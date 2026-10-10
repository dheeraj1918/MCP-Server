from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    prompt: str
    complexity: str
    tasks: list[dict[str, Any]]
    results: list[dict[str, Any]]
    final_answer: str
    error: str
    agent_count: int
    planning_error: str
