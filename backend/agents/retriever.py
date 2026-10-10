import json
import logging

from backend.services.mcp_client import get_mcp_tools, get_tool_schema, send_to_mcp

logger = logging.getLogger(__name__)

RETRIEVAL_KEYWORDS = (
    "search", "web", "fetch", "read", "retrieve", "github",
    "database", "query", "list", "lookup", "browse", "get", "find",
)


def _parse_tool_plan(raw: object) -> dict:
    """Extract a JSON tool-plan from LLM output. Raises json.JSONDecodeError on failure."""
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


async def run_retrieval_worker(prompt: str, task: dict) -> dict:
    """Select and execute one matching MCP retrieval tool."""
    name = task.get("name", "retriever")
    role = task.get("role", "Retrieval")

    try:
        # Single connection — reuse the same tools list for both selection and invocation
        tools = await get_mcp_tools()

        relevant = [
            tool for tool in tools
            if tool.name not in {"ask_llm", "list_available_llms"} and any(
                key in tool.name.lower()
                or key in (tool.description or "").lower()
                for key in RETRIEVAL_KEYWORDS
            )
        ]

        if not relevant:
            # No retrieval tools available — fall back to a plain LLM answer
            response = await send_to_mcp(
                f"Objective: {prompt}\nTask: {task.get('task', prompt)}\n"
                "Answer as thoroughly as you can from your knowledge."
            )
            return {
                "agent": name, "role": role, "success": True,
                "result": response.get("response",
                                       "No retrieval tools available; could not complete task."),
            }

        # Build tool descriptions with accurate schemas
        descriptions = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "schema": get_tool_schema(tool),
            }
            for tool in relevant
        ]

        selection_prompt = f"""You are a retrieval specialist in Factory OS.
Choose the best tool from the list below to complete the assigned task.
Objective: {prompt}
Assigned task: {task.get('task', prompt)}

Available tools:
{json.dumps(descriptions, indent=2)}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"tool": "<exact_tool_name>", "arguments": {{<param>: <value>}}}}

Rules:
- Use only a tool that is listed above.
- Include all required arguments from the tool's schema.
- For write/destructive tools, include "confirm": true in arguments.
- If no listed tool is suitable, respond with: {{"tool": null, "arguments": {{}}}}
"""
        response = await send_to_mcp(selection_prompt)
        raw_response = response.get("response", "")

        try:
            plan = _parse_tool_plan(raw_response)
        except (json.JSONDecodeError, ValueError) as parse_err:
            logger.warning(
                "Retriever could not parse tool selection JSON: %s\nLLM output: %s",
                parse_err, raw_response[:500],
            )
            return {
                "agent": name, "role": role, "success": False,
                "result": (
                    f"LLM returned non-JSON tool selection: {raw_response[:300]}\n"
                    f"Parse error: {parse_err}"
                ),
            }

        selected_name = plan.get("tool")
        arguments = plan.get("arguments", {})

        # LLM explicitly said no suitable tool
        if not selected_name:
            response2 = await send_to_mcp(
                f"Objective: {prompt}\nTask: {task.get('task', prompt)}\n"
                "No suitable retrieval tool is available. Answer from your knowledge."
            )
            return {
                "agent": name, "role": role, "success": True,
                "result": response2.get("response", "No suitable tool found."),
            }

        selected = next((t for t in relevant if t.name == selected_name), None)
        if selected is None:
            return {
                "agent": name, "role": role, "success": False,
                "result": (
                    f"LLM selected tool '{selected_name}' which does not exist. "
                    f"Available: {[t.name for t in relevant]}"
                ),
            }

        if not isinstance(arguments, dict):
            return {
                "agent": name, "role": role, "success": False,
                "result": f"Tool arguments must be a JSON object, got: {type(arguments).__name__}",
            }

        logger.info("Retriever invoking tool: %s with args %s", selected_name, arguments)
        tool_result = await selected.ainvoke(arguments)

        return {
            "agent": name,
            "role": role,
            "success": True,
            "tool": selected.name,
            "arguments": arguments,
            "result": str(tool_result),
        }

    except Exception as exc:
        logger.exception("Retrieval worker failed")
        return {
            "agent": name, "role": role, "success": False,
            "result": f"Retrieval failed: {type(exc).__name__}: {exc}",
        }
