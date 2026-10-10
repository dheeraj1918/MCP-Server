import os
from pathlib import Path

# Root directory containing backend/ and mcp_server/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

MAX_AGENTS = max(1, int(os.getenv("MAX_AGENTS", "5")))
MAX_PARALLEL_AGENTS = max(1, int(os.getenv("MAX_PARALLEL_AGENTS", "3")))

MCP_COMMAND = os.getenv("MCP_COMMAND", "uv")
# Entry point for the MCP server subprocess.
# Defaults to mcp_server/main.py which calls run_server() inside the package.
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "mcp_server/main.py")
