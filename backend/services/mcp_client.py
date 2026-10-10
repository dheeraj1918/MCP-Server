from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from backend.config import MCP_COMMAND, MCP_SERVER_PATH, PROJECT_ROOT

server_path = Path(MCP_SERVER_PATH)
if not server_path.is_absolute():
    server_path = PROJECT_ROOT / server_path

if not server_path.exists():
    raise FileNotFoundError(
        f"MCP server entry point not found: {server_path}. "
        "Set MCP_SERVER_PATH to the actual server entry point (e.g. mcp_server/main.py)."
    )

_mcp_server_dir = server_path.parent

mcp_client = MultiServerMCPClient({
    "factory_tools": {
        "transport": "stdio",
        "command": MCP_COMMAND,
        "args": [
            "run",
            "--directory", str(_mcp_server_dir),
            "python", str(server_path),
        ],
    }
})


async def get_mcp_tools():
    """Discover the tools exposed by the MCP server subprocess."""
    return await mcp_client.get_tools()


async def send_to_mcp(prompt: str) -> dict:
    """Call ask_llm on the MCP server. Returns {"success": True, "response": <str>}."""
    tools = await get_mcp_tools()
    gateway = next((t for t in tools if t.name == "ask_llm"), None)
    if gateway is None:
        available = ", ".join(t.name for t in tools) or "none"
        raise RuntimeError(
            f"MCP server does not expose 'ask_llm'. Available tools: {available}"
        )
    raw = await gateway.ainvoke({"prompt": prompt})
    text = _unwrap(raw)
    return {"success": True, "response": text}


def get_tool_schema(tool) -> dict:
    """Return the input schema dict for a LangChain MCP tool object.

    Tries multiple attribute names used across langchain / langchain-mcp-adapters versions.
    Always returns a dict (empty if nothing found).
    """
    # langchain-mcp-adapters exposes .args as a property → {param: type_str}
    for attr in ("args", "args_schema", "input_schema", "schema"):
        val = getattr(tool, attr, None)
        if val is None:
            continue
        # Pydantic model class → call .schema()
        if isinstance(val, type):
            try:
                return val.schema()
            except Exception:
                pass
        if isinstance(val, dict):
            return val
    return {}


def _unwrap(raw) -> str:
    """Normalise whatever FastMCP returns into a plain string."""
    if isinstance(raw, str):
        return raw

    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or str(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    if isinstance(raw, dict):
        if "response" in raw:
            resp = raw["response"]
            return resp if isinstance(resp, str) else str(resp)
        if "text" in raw:
            return raw["text"]
        return str(raw)

    return str(raw)
