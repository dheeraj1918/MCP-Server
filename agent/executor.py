from llm.model_router import route_prompt

def execute_prompt(prompt: str) -> dict:
    """Execute a prompt using the automatic LLM router."""
    if not prompt or not prompt.strip():
        return {
            "success": False,
            "error": "Prompt cannot be empty."
        }

    result = route_prompt(prompt)

    if not result["success"]:
        return {
            "success": False,
            "error": "All configured models failed.",
            "details": result["errors"],
        }

    return result