import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "groq/openai/gpt-oss-20b"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini/gemini-3.1-flash-lite"
)

OPENROUTER_FAST_MODEL = os.getenv(
    "OPENROUTER_FAST_MODEL",
    "deepseek/deepseek-v4-flash"
)

OPENROUTER_GENERAL_MODEL = os.getenv(
    "OPENROUTER_GENERAL_MODEL",
    "xiaomi/mimo-v2.6-flash"
)

OPENROUTER_COMPLEX_MODEL = os.getenv(
    "OPENROUTER_COMPLEX_MODEL",
    "xiaomi/mimo-v2.6-pro"
)

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")