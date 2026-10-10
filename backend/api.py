"""
Factory OS — FastAPI streaming backend.

Endpoints:
  POST /run      Streams planning + per-agent + review events as SSE
  GET  /health   Liveness check
"""

import asyncio
import json
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents.planner import plan_tasks
from backend.agents.retriever import run_retrieval_worker
from backend.agents.reviewer import review_results
from backend.agents.worker import run_worker
from backend.config import MAX_PARALLEL_AGENTS
from backend.services.mcp_client import get_mcp_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("factory_os.api")

app = FastAPI(title="Factory OS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    prompt: str


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_workflow(prompt: str):
    prompt = prompt.strip()
    if not prompt:
        yield _sse("error", {"message": "Prompt cannot be empty."})
        return

    # ── 1. Planning ──────────────────────────────────────────────────────────
    yield _sse("planning", {"message": "Planning tasks…"})

    try:
        plan = await plan_tasks(prompt)
    except Exception as exc:
        yield _sse("error", {"message": f"Planning failed: {exc}"})
        return

    tasks = plan.get("tasks", [])
    complexity = plan.get("complexity", "simple")

    yield _sse("plan_ready", {
        "complexity": complexity,
        "agent_count": len(tasks),
        "tasks": [
            {"name": t.get("name"), "role": t.get("role"), "type": t.get("type")}
            for t in tasks
        ],
    })

    if plan.get("planning_error"):
        yield _sse("warning", {"message": plan["planning_error"]})

    # ── 2. Execution (parallel via queue) ────────────────────────────────────
    semaphore = asyncio.Semaphore(MAX_PARALLEL_AGENTS)
    results: list[dict] = [{}] * len(tasks)
    queue: asyncio.Queue = asyncio.Queue()

    async def run_one(index: int, task: dict):
        name = task.get("name", f"worker_{index + 1}")
        async with semaphore:
            await queue.put(_sse("agent_start", {
                "name": name,
                "role": task.get("role"),
                "type": task.get("type"),
            }))
            try:
                tools = await get_mcp_tools()
                if task.get("type") == "retrieval":
                    result = await run_retrieval_worker(prompt, task)
                else:
                    result = await run_worker(
                        prompt=prompt, task=task,
                        tools=tools, complexity=complexity,
                    )
            except Exception as exc:
                result = {
                    "agent": name,
                    "role": task.get("role", "Worker"),
                    "type": task.get("type", "general"),
                    "success": False,
                    "result": f"{type(exc).__name__}: {exc}",
                }
            results[index] = result
            await queue.put(_sse("agent_done", {
                "name": name,
                "role": task.get("role"),
                "success": result.get("success", False),
                "tools_used": result.get("tools_used", []),
                "result": str(result.get("result", ""))[:2000],
            }))

    async def producer():
        await asyncio.gather(*(run_one(i, t) for i, t in enumerate(tasks)))
        await queue.put(None)  # sentinel

    runner = asyncio.create_task(producer())

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item

    await runner

    # ── 3. Review ────────────────────────────────────────────────────────────
    yield _sse("reviewing", {"message": "Synthesizing results…"})

    try:
        answer = await review_results(
            prompt=prompt, results=results, complexity=complexity
        )
    except Exception as exc:
        answer = f"Review failed: {exc}"

    errors = [
        f"{r.get('agent', 'worker')}: {r.get('result', 'failed')}"
        for r in results
        if not r.get("success", False)
    ]

    yield _sse("done", {
        "success": bool(answer) and not errors,
        "complexity": complexity,
        "agent_count": len(tasks),
        "agents": [t.get("name", "worker") for t in tasks],
        "answer": answer,
        "errors": errors,
    })


@app.post("/run")
async def run_endpoint(body: RunRequest):
    return StreamingResponse(
        _stream_workflow(body.prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "factory-os-api"}


def start(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run("backend.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start()
