import importlib
import inspect
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Factory OS Tools")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"

EXCLUDED_FUNCTIONS = {
    "main",
    "run",
    "cli",
}

def register_tools():
    if not TOOLS_DIR.is_dir():
        raise RuntimeError(
            f"Tools directory not found: {TOOLS_DIR}"
        )

    for file in sorted(TOOLS_DIR.glob("*.py")):
        if file.name.startswith("_"):
            continue

        module_name = f"tools.{file.stem}"

        try:
            module = importlib.import_module(module_name)
        except Exception:
            logging.exception(
                "Could not import %s", module_name
            )
            continue

        for name, function in inspect.getmembers(
            module, inspect.isfunction
        ):
            if name.startswith("_"):
                continue

            if name in EXCLUDED_FUNCTIONS:
                continue

            # Only expose functions defined in this module,
            # not every imported dependency.
            if function.__module__ != module.__name__:
                continue

            # MCP needs an inspectable schema. Skip functions
            # with unsupported or missing type annotations.
            signature = inspect.signature(function)

            if not function.__doc__:
                logging.debug(
                    "Skipping undocumented function: %s.%s",
                    module_name, name
                )
                continue

            if any(
                param.annotation is inspect.Parameter.empty
                for param in signature.parameters.values()
            ):
                logging.debug(
                    "Skipping function with missing annotations: %s.%s",
                    module_name, name
                )
                continue

            if signature.return_annotation is inspect.Signature.empty:
                logging.debug(
                    "Skipping function without return annotation: %s.%s",
                    module_name, name
                )
                continue

            try:
                mcp.tool(name=f"{file.stem}_{name}")(function)
                logging.info(
                    "Registered MCP tool: %s_%s",
                    file.stem, name
                )
            except Exception:
                logging.exception(
                    "Could not register %s.%s",
                    module_name, name
                )

@mcp.tool()
def list_available_llms() -> dict:
    """List the configured LLM models available to the router."""
    from llm.providers import available_models

    return {"models": available_models()}

@mcp.tool()
def ask_llm(prompt: str) -> dict:
    """Ask an LLM using automatic complexity-based model routing."""
    from llm.model_router import route_prompt

    return route_prompt(prompt)

register_tools()

def run_server():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()