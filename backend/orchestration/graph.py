"""
LangGraph workflow: planner → workers → reviewer.

Execution strategy
──────────────────
Wave 1 (parallel):   all tasks that do NOT depend on prior output
                     (e.g. Code Generator, researchers)
Wave 2 (sequential): tasks that consume Wave-1 output
                     (e.g. GitHub Publisher, deployer)
                     Each Wave-2 task receives the full cumulative result list.

A task is "dependent" (Wave 2) when its role OR task text contains any of the
keywords in _DEPENDENT_ROLE_WORDS / _DEPENDENT_TASK_WORDS.
"""

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from backend.agents.planner import plan_tasks
from backend.agents.retriever import run_retrieval_worker
from backend.agents.reviewer import review_results
from backend.agents.worker import run_worker
from backend.config import MAX_PARALLEL_AGENTS
from backend.orchestration.state import WorkflowState
from backend.services.mcp_client import get_mcp_tools

logger = logging.getLogger(__name__)

# Role substrings that mark a task as Wave-2 (dependent)
_DEPENDENT_ROLE_WORDS = {
    "publisher", "deployer", "uploader",
    "git publisher", "github publisher", "deploy agent", "deployment",
}

# Task-text substrings that mark a task as Wave-2 (dependent)
_DEPENDENT_TASK_WORDS = {
    "push to github", "github_push", "create repo and push",
    "push all", "upload to github", "deploy to github",
    "github_create_repo", "github_push_files",
}


def _is_dependent(task: dict) -> bool:
    """Return True if this task must run in Wave 2 (after independent workers)."""
    role = task.get("role", "").lower().strip()
    text = task.get("task", "").lower().strip()

    if any(kw in role for kw in _DEPENDENT_ROLE_WORDS):
        return True
    if any(kw in text for kw in _DEPENDENT_TASK_WORDS):
        return True
    return False


async def planning_node(state: WorkflowState) -> dict:
    plan = await plan_tasks(state["prompt"])
    update: dict = {
        "complexity": plan["complexity"],
        "tasks": plan["tasks"],
        "agent_count": len(plan["tasks"]),
    }
    if plan.get("planning_error"):
        update["planning_error"] = plan["planning_error"]

    # Log the wave assignment for debugging
    for t in plan["tasks"]:
        wave = "Wave-2 (dependent)" if _is_dependent(t) else "Wave-1 (independent)"
        logger.info("[planner] %s → role=%r  wave=%s", t.get("name"), t.get("role"), wave)

    return update


async def execution_node(state: WorkflowState) -> dict:
    tools = await get_mcp_tools()
    semaphore = asyncio.Semaphore(MAX_PARALLEL_AGENTS)
    all_tasks = state.get("tasks", [])
    complexity = state.get("complexity", "simple")

    independent = [t for t in all_tasks if not _is_dependent(t)]
    dependent   = [t for t in all_tasks if _is_dependent(t)]

    logger.info("[execution] Wave-1 tasks: %s", [t.get("name") for t in independent])
    logger.info("[execution] Wave-2 tasks: %s", [t.get("name") for t in dependent])

    async def _run(task: dict, prior: list[dict]) -> dict:
        """Run one task inside the semaphore."""
        async with semaphore:
            if task.get("type") == "retrieval":
                return await run_retrieval_worker(state["prompt"], task)
            return await run_worker(
                prompt=state["prompt"],
                task=task,
                tools=tools,
                complexity=complexity,
                prior_results=prior,
            )

    # ── Wave 1: independent tasks, all in parallel ────────────────────────
    wave1_raw = await asyncio.gather(
        *(_run(t, []) for t in independent),
        return_exceptions=True,
    )

    wave1: list[dict] = []
    for i, item in enumerate(wave1_raw):
        if isinstance(item, BaseException):
            t = independent[i]
            logger.error("[execution] Wave-1 task %s raised: %s", t.get("name"), item)
            wave1.append({
                "agent":   t.get("name", f"worker_{i+1}"),
                "role":    t.get("role", "Worker"),
                "type":    t.get("type", "general"),
                "success": False,
                "files":   [],
                "result":  f"{type(item).__name__}: {item}",
            })
        else:
            logger.info(
                "[execution] Wave-1 task %s finished: success=%s files=%d",
                item.get("agent"), item.get("success"), len(item.get("files", [])),
            )
            wave1.append(item)

    # ── Wave 2: dependent tasks, sequential, each sees all prior output ───
    wave2: list[dict] = []
    cumulative = list(wave1)  # grows as each Wave-2 task completes

    for task in dependent:
        logger.info(
            "[execution] Starting Wave-2 task %s with %d prior results (%d files total)",
            task.get("name"),
            len(cumulative),
            sum(len(r.get("files", [])) for r in cumulative),
        )
        try:
            result = await _run(task, cumulative)
        except Exception as exc:
            logger.exception("[execution] Wave-2 task %s raised", task.get("name"))
            result = {
                "agent":   task.get("name", "dep_worker"),
                "role":    task.get("role", "Worker"),
                "type":    task.get("type", "general"),
                "success": False,
                "files":   [],
                "result":  f"{type(exc).__name__}: {exc}",
            }

        logger.info(
            "[execution] Wave-2 task %s finished: success=%s",
            result.get("agent"), result.get("success"),
        )
        wave2.append(result)
        cumulative.append(result)

    return {"results": wave1 + wave2}


async def review_node(state: WorkflowState) -> dict:
    answer = await review_results(
        prompt=state["prompt"],
        results=state.get("results", []),
        complexity=state.get("complexity", "simple"),
    )
    return {"final_answer": answer}


def build_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("planner", planning_node)
    graph.add_node("workers", execution_node)
    graph.add_node("reviewer", review_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "workers")
    graph.add_edge("workers", "reviewer")
    graph.add_edge("reviewer", END)
    return graph.compile()


workflow = build_graph()


async def run_workflow(prompt: str) -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt cannot be empty.")

    result = await workflow.ainvoke({"prompt": prompt, "results": []})

    errors = []
    if result.get("planning_error"):
        errors.append(result["planning_error"])
    errors.extend(
        f"{item.get('agent', 'worker')}: {item.get('result', 'failed')}"
        for item in result.get("results", [])
        if not item.get("success", False)
    )

    return {
        "success":     bool(result.get("final_answer")) and not errors,
        "complexity":  result.get("complexity", "unknown"),
        "agent_count": result.get("agent_count", 0),
        "agents":      [t.get("name", "worker") for t in result.get("tasks", [])],
        "results":     result.get("results", []),
        "answer":      result.get("final_answer", ""),
        "errors":      errors,
    }
