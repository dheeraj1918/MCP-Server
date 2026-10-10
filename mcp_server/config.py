"""
MCP server configuration — reads all env vars from mcp_server/.env via dotenv.

Tools that import os.getenv() directly are covered because server.py calls
load_dotenv() before any tool is imported. This module provides typed constants
for code that prefers explicit imports over bare os.getenv() calls.
"""
import os
from dotenv import load_dotenv

# Load .env from the directory this file lives in (mcp_server/).
# safe to call multiple times — dotenv is idempotent.
load_dotenv()

# ── LLM providers ─────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/llama3-8b-8192")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-flash")
OPENROUTER_FAST_MODEL = os.getenv(
    "OPENROUTER_FAST_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct:free"
)
OPENROUTER_GENERAL_MODEL = os.getenv(
    "OPENROUTER_GENERAL_MODEL", "openrouter/meta-llama/llama-3.1-70b-instruct"
)
OPENROUTER_COMPLEX_MODEL = os.getenv(
    "OPENROUTER_COMPLEX_MODEL", "openrouter/anthropic/claude-3.5-sonnet"
)

# ── GitHub tool ────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ── AWS S3 tool ────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_S3_ALLOWED_BUCKETS = os.getenv("AWS_S3_ALLOWED_BUCKETS", "")

# ── Vercel deploy tool ─────────────────────────────────────────────────────────
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "")
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID", "")

# ── Web search tool ────────────────────────────────────────────────────────────
WEB_SEARCH_ENDPOINT = os.getenv("WEB_SEARCH_ENDPOINT", "")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")

# ── Workspace & memory ────────────────────────────────────────────────────────
FACTORY_OS_WORKSPACE = os.getenv("FACTORY_OS_WORKSPACE", "./workspace")
FACTORY_OS_MEMORY_DB = os.getenv("FACTORY_OS_MEMORY_DB", "./workspace/memory.db")

# ── Unsafe execution tools ────────────────────────────────────────────────────
FACTORY_OS_ENABLE_UNSAFE_TOOLS = (
    os.getenv("FACTORY_OS_ENABLE_UNSAFE_TOOLS", "false").lower() == "true"
)

# ── MCP transport ─────────────────────────────────────────────────────────────
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
