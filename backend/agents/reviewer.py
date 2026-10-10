import logging

from backend.services.mcp_client import send_to_mcp

logger = logging.getLogger(__name__)


async def review_results(
    prompt: str,
    results: list[dict],
    complexity: str = "simple",
) -> str:
    """Synthesize all successful agent results into one final answer."""
    successful = [
        {
            "agent": item.get("agent", "unknown"),
            "role": item.get("role", "Worker"),
            "tool_used": item.get("tool_used"),
            "result": item.get("result", ""),
        }
        for item in results
        if item.get("success", False)
    ]

    if not successful:
        failure_lines = [
            f"  - {item.get('agent', 'worker')}: {str(item.get('result', 'Unknown error'))[:300]}"
            for item in results
        ]
        return (
            "No agent completed successfully. Failure details:\n"
            + "\n".join(failure_lines)
        )

    request = f"""You are the final reviewer for Factory OS.
Original user request: {prompt}
Task complexity: {complexity}

Agent results:
{successful}

Your job:
1. Combine all useful findings into one clear, well-structured answer.
2. Remove duplication.
3. If an agent used a tool (see tool_used field), mention what was accomplished.
4. Flag anything that is uncertain or incomplete.
5. Answer the original request directly.

Return plain text only — no JSON, no markdown headers.
"""
    try:
        response = await send_to_mcp(request)
        answer = response.get("response", "")
        return answer if isinstance(answer, str) else str(answer)
    except Exception as exc:
        logger.exception("Review step failed")
        fallback = "\n\n".join(
            f"{item['agent']}: {item['result']}" for item in successful
        )
        return (
            f"Review step failed ({type(exc).__name__}: {exc}).\n\n"
            f"Raw agent results:\n\n{fallback}"
        )
