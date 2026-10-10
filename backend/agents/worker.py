"""
Worker agent — agentic loop with dedicated Code Generator and GitHub Publisher paths.

Key design decision:
  The Code Generator does NOT ask the LLM to call tools.
  Instead it asks the LLM to return a plain JSON object with all file contents,
  then Python extracts that JSON and calls workspace_write itself.
  This is 100% reliable — LLMs always return JSON when asked directly.

  The GitHub Publisher receives the file list from prior_results["files"]
  and calls github tools directly (no LLM involved in pushing).
"""

import json
import logging
import re
from typing import Any

from backend.services.mcp_client import get_tool_schema, send_to_mcp

logger = logging.getLogger(__name__)

MAX_STEPS = 8


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_tool_call(text: str) -> dict | None:
    """Extract the last JSON tool-call block {"tool": ..., "arguments": ...}."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    end = text.rfind("}")
    if end < 0:
        return None
    depth, start = 0, -1
    for i in range(end, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            depth -= 1
            if depth == 0:
                start = i
                break
    if start < 0:
        return None
    try:
        obj = json.loads(text[start:end + 1])
        if isinstance(obj, dict) and "tool" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    return None


def _extract_files_json(text: str) -> list[dict]:
    """
    Extract file list from LLM output.

    Accepts three formats (in priority order):

    1. Top-level JSON object:
       {"files": [{"path": "...", "content": "..."}]}

    2. JSON array directly:
       [{"path": "...", "content": "..."}]

    3. Code blocks with preceding filename:
       ### rest-api/app.py
       ```python
       <code>
       ```
    """
    # ── Format 1 & 2: JSON ────────────────────────────────────────────────────
    # Strip markdown fences first
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()

    # Try every {...} block in the text (outermost first)
    for match in re.finditer(r'[{\[]', clean):
        start = match.start()
        open_ch = clean[start]
        close_ch = "}" if open_ch == "{" else "]"
        depth, end = 0, -1
        for i in range(start, len(clean)):
            if clean[i] == open_ch:
                depth += 1
            elif clean[i] == close_ch:
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end < 0:
            continue
        try:
            obj = json.loads(clean[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            continue

        # {"files": [...]}
        if isinstance(obj, dict) and "files" in obj:
            files = obj["files"]
            if isinstance(files, list):
                valid = [
                    f for f in files
                    if isinstance(f, dict)
                    and str(f.get("path", "")).strip()
                    and "content" in f
                ]
                if valid:
                    return valid

        # [{"path": ..., "content": ...}]
        if isinstance(obj, list):
            valid = [
                f for f in obj
                if isinstance(f, dict)
                and str(f.get("path", "")).strip()
                and "content" in f
            ]
            if valid:
                return valid

    # ── Format 3: fenced code blocks with filename heading ───────────────────
    files: dict[str, str] = {}
    # Patterns that introduce a filename before a code block:
    #   ### rest-api/app.py       (markdown heading)
    #   **rest-api/app.py**       (bold)
    #   `rest-api/app.py`         (inline code)
    #   // rest-api/app.py        (comment)
    #   # rest-api/app.py         (hash comment)
    fname_pattern = re.compile(
        r'(?:^|\n)'                           # start of line
        r'(?:#{1,4}\s+|[*]{2}|`|//\s*|#\s*)?' # optional prefix
        r'([\w][\w./\-]{1,60}\.\w{1,10})'    # filename
        r'(?:`|[*]{2})?'                      # optional suffix
        r'\s*\n'                              # newline after filename
        r'```(?:\w*)\n'                       # opening fence
        r'(.*?)'                              # code
        r'```',                               # closing fence
        re.DOTALL,
    )
    for m in fname_pattern.finditer(text):
        fname = m.group(1).strip().lstrip("/")
        code = m.group(2)
        if fname and code.strip():
            files[fname] = code

    if files:
        return [{"path": p, "content": c} for p, c in files.items()]

    return []


def _repo_name_from_task(task_text: str, prompt: str) -> str:
    """Extract a repo name from task or prompt text."""
    STOPWORDS = {"named", "called", "a", "an", "the", "my", "your", "new", "into", "it"}
    for text in (task_text, prompt):
        # "repo named <name>" or "repository called <name>"
        m = re.search(
            r"(?:repo(?:sitory)?)\s+(?:named?|called?)\s+['\"]?([^\s'\",.]+)['\"]?",
            text, re.IGNORECASE,
        )
        if m:
            candidate = m.group(1).lower().replace("_", "-").strip("\"'.,")
            if candidate and candidate not in STOPWORDS:
                return candidate
        # Quoted name anywhere
        m = re.search(r"['\"]([a-z0-9][a-z0-9_\-]{1,38})['\"]", text, re.IGNORECASE)
        if m:
            candidate = m.group(1).lower().replace("_", "-")
            if candidate not in STOPWORDS:
                return candidate
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# File plan — what files to generate for a project
# ─────────────────────────────────────────────────────────────────────────────

async def _get_file_plan(prompt: str, task_text: str, folder: str) -> list[dict]:
    """Ask the LLM for a simple list of filenames + one-line descriptions.

    Returns [{"path": "folder/file.ext", "description": "..."}]
    This is a small, constrained response the LLM handles reliably.
    """
    plan_prompt = f"""List the files needed for this project as a JSON array.

Project: {task_text or prompt}
Folder: {folder}/

Return ONLY a JSON array like this (no other text):
[
  {{"path": "{folder}/app.py", "description": "Main application file"}},
  {{"path": "{folder}/requirements.txt", "description": "Python dependencies"}},
  {{"path": "{folder}/README.md", "description": "Setup and usage instructions"}}
]

Rules:
- 3 to 6 files maximum
- Always include README.md
- paths must start with "{folder}/"
"""
    try:
        resp = await send_to_mcp(plan_prompt)
        text = resp.get("response", "").strip()
        # Find the JSON array
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            plan = json.loads(text[start:end + 1])
            valid = [
                p for p in plan
                if isinstance(p, dict) and p.get("path", "").startswith(folder)
            ]
            if valid:
                return valid
    except Exception as e:
        logger.warning("File plan failed: %s", e)

    # Hardcoded fallback plan
    return [
        {"path": f"{folder}/app.py", "description": "Main application"},
        {"path": f"{folder}/requirements.txt", "description": "Dependencies"},
        {"path": f"{folder}/README.md", "description": "Documentation"},
    ]


async def _generate_one_file(path: str, description: str, prompt: str, folder: str) -> str:
    """Generate the content of a single file. Returns the raw file content string."""
    ext = path.rsplit(".", 1)[-1].lower()

    if ext == "md":
        file_prompt = (
            f"Write a README.md for this project: {prompt}\n"
            f"Include: project description, requirements, installation steps, "
            f"how to run it, and example API calls if applicable.\n"
            f"Return ONLY the raw markdown content, no extra explanation."
        )
    elif ext in ("txt",) and "requirements" in path.lower():
        file_prompt = (
            f"List the pip package requirements for this project: {prompt}\n"
            f"Return ONLY the requirements.txt content (one package per line, "
            f"with version pins like flask==3.0.0). No explanation."
        )
    else:
        file_prompt = (
            f"Write the complete, working code for this file: {path}\n"
            f"File purpose: {description}\n"
            f"Project: {prompt}\n"
            f"Return ONLY the raw code, no markdown fences, no explanation.\n"
            f"The code must be complete and runnable."
        )

    try:
        resp = await send_to_mcp(file_prompt)
        content = resp.get("response", "").strip()
        # Strip accidental markdown fences
        if content.startswith("```"):
            lines = content.splitlines()[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content
    except Exception as e:
        return f"# Error generating {path}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Code Generator — generates files one at a time, assembles in Python
# ─────────────────────────────────────────────────────────────────────────────

async def _run_code_generator(
    prompt: str,
    task: dict,
    tool_map: dict,
    complexity: str,
) -> dict:
    """Generate project files one at a time and save them to workspace."""
    agent_name = task.get("name", "worker")
    agent_role = task.get("role", "Code Generator")
    task_text = task.get("task", prompt)

    folder = _repo_name_from_task(task_text, prompt) or "project"
    logger.info("[%s] Generating project in folder '%s'", agent_name, folder)

    # Step 1: Get the list of files to generate
    file_plan = await _get_file_plan(prompt, task_text, folder)
    logger.info("[%s] File plan: %s", agent_name, [f["path"] for f in file_plan])

    # Step 2: Generate each file content individually
    files: list[dict] = []
    write_tool = tool_map.get("workspace_write")
    tools_used: list[str] = []
    write_log: list[str] = []

    for item in file_plan:
        path = item["path"]
        description = item.get("description", "")
        logger.info("[%s] Generating %s", agent_name, path)

        content = await _generate_one_file(path, description, task_text or prompt, folder)

        if not content:
            logger.warning("[%s] Empty content for %s — skipping", agent_name, path)
            continue

        files.append({"path": path, "content": content})

        # Save to workspace
        if write_tool:
            try:
                await write_tool.ainvoke({"path": path, "content": content})
                tools_used.append("workspace_write")
                write_log.append(f"  ✓ saved {path} ({len(content)} chars)")
                logger.info("[%s] Saved %s (%d chars)", agent_name, path, len(content))
            except Exception as e:
                write_log.append(f"  ✗ failed {path}: {e}")
                logger.warning("[%s] workspace_write failed for %s: %s", agent_name, path, e)

    if not files:
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": [], "files": [],
            "result": "Failed to generate any files.",
        }

    logger.info("[%s] Generated %d files successfully", agent_name, len(files))

    summary = (
        f"Generated {len(files)} file(s) in folder '{folder}/':\n"
        + "\n".join(f"  📄 {f['path']} ({len(f['content'])} chars)" for f in files)
        + ("\n\n" + "\n".join(write_log) if write_log else "")
    )

    return {
        "agent": agent_name,
        "role": agent_role,
        "type": "general",
        "success": True,
        "tools_used": list(set(tools_used)),
        "files": files,   # consumed by GitHub Publisher
        "result": summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Publisher — deterministic, no LLM
# ─────────────────────────────────────────────────────────────────────────────

async def _run_github_publisher(
    prompt: str,
    task: dict,
    tool_map: dict,
    prior_results: list[dict],
) -> dict:
    agent_name = task.get("name", "github_publisher")
    agent_role = task.get("role", "GitHub Publisher")
    tools_used: list[str] = []

    # ── Collect files from all prior agents ───────────────────────────────
    all_files: dict[str, str] = {}
    for r in prior_results:
        # Structured list (from _run_code_generator)
        for f in r.get("files", []):
            if f.get("path") and "content" in f:
                all_files[f["path"]] = f["content"]
        # Fallback: try to parse files from result text
        for f in _extract_files_json(r.get("result", "")):
            if f["path"] not in all_files:
                all_files[f["path"]] = f["content"]

    logger.info("[%s] Collected %d files from prior results", agent_name, len(all_files))
    logger.info("[%s] Prior result keys: %s", agent_name,
                [(r.get("agent"), list(r.keys())) for r in prior_results])

    if not all_files:
        # Show what we actually received for debugging
        prior_summary = "\n".join(
            f"  - {r.get('agent','?')} (role={r.get('role','?')}): "
            f"success={r.get('success')}, files={len(r.get('files',[]))}, "
            f"result_preview={str(r.get('result',''))[:100]}"
            for r in prior_results
        )
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": [],
            "result": (
                f"No files found from prior agents.\n\n"
                f"Prior agent results:\n{prior_summary}"
            ),
        }

    # ── Determine repo name ───────────────────────────────────────────────
    task_text = task.get("task", "")
    repo_name = _repo_name_from_task(task_text, prompt)
    if not repo_name:
        # Derive from the folder prefix of the first file
        first_path = list(all_files.keys())[0].replace("\\", "/")
        parts = first_path.split("/")
        repo_name = parts[0] if len(parts) > 1 else "factory-os-project"
    repo_name = repo_name.lower().replace(" ", "-").replace("_", "-")
    logger.info("[%s] Repo name: %s", agent_name, repo_name)

    steps_log: list[str] = []

    # ── github_whoami ─────────────────────────────────────────────────────
    whoami_tool = tool_map.get("github_whoami")
    if not whoami_tool:
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": [],
            "result": "github_whoami tool not available. Is GITHUB_TOKEN set in mcp_server/.env?",
        }
    try:
        owner = str(await whoami_tool.ainvoke({})).strip()
        tools_used.append("github_whoami")
        steps_log.append(f"✓ Authenticated as: {owner}")
        logger.info("[%s] Owner: %s", agent_name, owner)
    except Exception as e:
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": ["github_whoami"],
            "result": f"github_whoami failed: {e}",
        }

    # ── github_create_repo ────────────────────────────────────────────────
    create_tool = tool_map.get("github_create_repo")
    if not create_tool:
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": tools_used,
            "result": "github_create_repo tool not available.",
        }
    try:
        res = str(await create_tool.ainvoke({
            "name": repo_name,
            "description": f"Generated by Factory OS — {prompt[:100]}",
            "private": False,
            "auto_init": True,
            "confirm": True,
        }))
        tools_used.append("github_create_repo")
        steps_log.append(f"✓ Created repo: {res}")
    except Exception as e:
        err = str(e)
        if "already exists" in err.lower() or "422" in err:
            steps_log.append(f"ℹ Repo '{repo_name}' already exists — will push to it.")
        else:
            return {
                "agent": agent_name, "role": agent_role, "type": "general",
                "success": False, "tools_used": tools_used,
                "result": f"github_create_repo failed: {e}\n" + "\n".join(steps_log),
            }

    # ── github_push_files ─────────────────────────────────────────────────
    push_tool = tool_map.get("github_push_files")
    if not push_tool:
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": tools_used,
            "result": "github_push_files tool not available.",
        }

    files_payload = [{"path": p, "content": c} for p, c in all_files.items()]

    try:
        push_res = str(await push_tool.ainvoke({
            "owner": owner,
            "repo": repo_name,
            "files_json": json.dumps(files_payload),
            "message": "Add project files via Factory OS",
            "confirm": True,
        }))
        tools_used.append("github_push_files")
        steps_log.append(f"✓ Pushed {len(files_payload)} files: {push_res}")
    except Exception as e:
        return {
            "agent": agent_name, "role": agent_role, "type": "general",
            "success": False, "tools_used": tools_used,
            "result": f"github_push_files failed: {e}\n" + "\n".join(steps_log),
        }

    repo_url = f"https://github.com/{owner}/{repo_name}"
    file_list = "\n".join(f"  📄 {f['path']}" for f in files_payload)

    return {
        "agent": agent_name,
        "role": agent_role,
        "type": "general",
        "success": True,
        "tools_used": tools_used,
        "result": (
            f"✅ Successfully published to GitHub!\n\n"
            f"🔗 Repository: {repo_url}\n\n"
            f"📁 Files pushed ({len(files_payload)}):\n{file_list}\n\n"
            + "\n".join(steps_log)
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# General worker — agentic loop for everything else
# ─────────────────────────────────────────────────────────────────────────────

async def run_worker(
    prompt: str,
    task: dict,
    tools: list | None = None,
    complexity: str = "simple",
    prior_results: list[dict] | None = None,
) -> dict:
    """Route to the right worker based on role."""
    tool_map = {t.name: t for t in (tools or [])}
    role_lower = task.get("role", "").lower()

    # ── GitHub Publisher ───────────────────────────────────────────────────
    if any(w in role_lower for w in (
        "publisher", "deployer", "uploader", "git publisher", "github publisher"
    )):
        return await _run_github_publisher(
            prompt=prompt, task=task,
            tool_map=tool_map, prior_results=prior_results or [],
        )

    # ── Code Generator ────────────────────────────────────────────────────
    if any(w in role_lower for w in (
        "code generator", "code writer", "developer", "programmer",
        "backend developer", "api developer", "software engineer",
        "full stack", "fullstack",
    )):
        return await _run_code_generator(
            prompt=prompt, task=task,
            tool_map=tool_map, complexity=complexity,
        )

    # ── General agentic loop ──────────────────────────────────────────────
    tool_descriptions = [
        {"name": t.name, "description": t.description or "", "schema": get_tool_schema(t)}
        for t in (tools or []) if t.name not in ("ask_llm", "list_available_llms")
    ]

    system_prompt = f"""You are a specialist worker agent in Factory OS.
Objective: {prompt}
Role: {task.get('role', 'General assistant')}
Task: {task.get('task', prompt)}
Complexity: {complexity}

Available tools:
{json.dumps(tool_descriptions, indent=2)}

RESPONSE FORMAT:
- Call a tool: respond with ONLY JSON: {{"tool": "<name>", "arguments": {{...}}}}
- Done: respond with plain text summary.
"""
    agent_name = task.get("name", "worker")
    agent_role = task.get("role", "General assistant")
    history: list[dict[str, Any]] = []
    tools_used: list[str] = []

    for step in range(1, MAX_STEPS + 1):
        user_content = (
            f"Begin: {task.get('task', prompt)}" if not history
            else (
                "Progress:\n" +
                "\n".join(
                    f"Step {i+1}: {h.get('tool','text')} → "
                    f"{str(h.get('result', h.get('text', '')))[:300]}"
                    for i, h in enumerate(history)
                ) + "\n\nNext step? If done, give a summary."
            )
        )

        try:
            response = await send_to_mcp(f"{system_prompt}\n\n{user_content}")
        except Exception as exc:
            return {
                "agent": agent_name, "role": agent_role, "type": task.get("type", "general"),
                "success": False, "tools_used": tools_used,
                "result": f"LLM failed at step {step}: {exc}",
            }

        llm_text = response.get("response", "").strip()
        if not llm_text:
            break

        tool_call = _extract_tool_call(llm_text)
        if not tool_call:
            history.append({"text": llm_text})
            break

        tool_name = tool_call.get("tool", "")
        arguments = tool_call.get("arguments", {}) or {}
        selected = tool_map.get(tool_name)
        if selected is None:
            history.append({"tool": tool_name, "args": arguments,
                            "result": f"ERROR: tool '{tool_name}' not found."})
            continue

        tools_used.append(tool_name)
        try:
            result_str = str(await selected.ainvoke(arguments))
        except Exception as e:
            result_str = f"ERROR: {e}"
        history.append({"tool": tool_name, "args": arguments, "result": result_str})

    final = "\n\n".join(
        f"✓ {h['tool']}: {h['result']}" if "tool" in h else h["text"]
        for h in history
    )
    return {
        "agent": agent_name, "role": agent_role, "type": task.get("type", "general"),
        "success": bool(final), "tools_used": tools_used, "result": final,
    }
