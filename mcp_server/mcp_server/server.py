"""
Factory OS MCP Server.

IMPORTANT: stdout is the MCP JSON-RPC channel — nothing may be printed there.
All logging and LiteLLM output is redirected to stderr before anything else runs.
"""

import importlib
import inspect
import logging
import os
import sys
from pathlib import Path

# ── Silence stdout pollution BEFORE importing litellm or any tool ─────────────
# LiteLLM writes progress/debug lines to stdout, corrupting the MCP stdio channel.
os.environ.setdefault("LITELLM_LOG", "ERROR")
os.environ.setdefault("LITELLM_TELEMETRY", "False")

# Load .env BEFORE any tool or LLM module reads os.getenv().
# This must happen here (in server.py) because tools import os directly,
# not via config.py, so load_dotenv() in config.py is not guaranteed to
# have fired first.
from dotenv import load_dotenv as _load_dotenv  # noqa: E402
_load_dotenv()  # loads mcp_server/.env (cwd when launched via uv --directory mcp_server)

import builtins as _builtins
_real_print = _builtins.print

def _stderr_print(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    _real_print(*args, **kwargs)

_builtins.print = _stderr_print

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# ─────────────────────────────────────────────────────────────────────────────

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("Factory OS Tools")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"

logger = logging.getLogger(__name__)

# Opt-in gate for unsafe execution tools (terminal_run, python_run)
_UNSAFE_ENABLED = os.getenv("FACTORY_OS_ENABLE_UNSAFE_TOOLS", "false").lower() == "true"


def _register_module_tools(module_name: str) -> int:
    """Import a tools module and call its register(mcp) if present.

    Falls back to scanning top-level annotated functions.
    Returns the number of tool registrations (0 on failure or skip).
    """
    try:
        module = importlib.import_module(module_name)
    except Exception:
        logger.exception("Could not import %s", module_name)
        return 0

    register_fn = getattr(module, "register", None)
    if callable(register_fn):
        try:
            register_fn(mcp)
            logger.info("Registered tools from %s via register()", module_name)
            return 1
        except Exception:
            logger.exception("register() failed for %s", module_name)
            return 0

    # Fallback: scan top-level fully-annotated, documented functions.
    EXCLUDED = {"main", "run", "cli"}
    count = 0
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_") or name in EXCLUDED:
            continue
        if fn.__module__ != module.__name__:
            continue
        if not fn.__doc__:
            continue
        sig = inspect.signature(fn)
        if any(p.annotation is inspect.Parameter.empty for p in sig.parameters.values()):
            continue
        if sig.return_annotation is inspect.Signature.empty:
            continue
        stem = module_name.split(".")[-1]
        try:
            mcp.tool(name=f"{stem}_{name}")(fn)
            logger.info("Registered MCP tool: %s_%s", stem, name)
            count += 1
        except Exception:
            logger.exception("Could not register %s.%s", module_name, name)
    return count


def register_tools():
    if not TOOLS_DIR.is_dir():
        raise RuntimeError(f"Tools directory not found: {TOOLS_DIR}")

    for file in sorted(TOOLS_DIR.glob("*.py")):
        if file.name.startswith("_"):
            continue
        # Gate unsafe execution tools behind an explicit env var opt-in
        if file.stem == "optional_execution" and not _UNSAFE_ENABLED:
            logger.info(
                "Skipping optional_execution tools "
                "(set FACTORY_OS_ENABLE_UNSAFE_TOOLS=true to enable)"
            )
            continue
        _register_module_tools(f"tools.{file.stem}")


@mcp.tool()
def list_available_llms() -> dict:
    """List the configured LLM models available to the router."""
    from llm.providers import available_models
    return {"models": available_models()}


@mcp.tool()
def ask_llm(prompt: str) -> str:
    """Ask an LLM using automatic complexity-based model routing. Returns plain text."""
    try:
        from llm.model_router import route_prompt
        result = route_prompt(prompt)
        if result.get("success"):
            return result.get("response") or ""
        errors = "; ".join(
            e.get("error", str(e)) for e in result.get("errors", [])
        )
        return f"[LLM routing failed] {errors}"
    except Exception as exc:
        return f"[ask_llm error] {type(exc).__name__}: {exc}"


register_tools()


def run_server():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
