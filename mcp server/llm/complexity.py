import re

COMPLEX_KEYWORDS = {
    "architect", "architecture", "design a system",
    "debug this project", "analyze", "compare",
    "optimize", "multi-agent", "distributed",
    "concurrency", "security audit", "root cause",
    "prove", "derive", "complex reasoning",
    "refactor the entire", "production ready"
}

MEDIUM_KEYWORDS = {
    "explain", "implement", "write a program",
    "create an api", "build an application",
    "database schema", "integration", "workflow"
}

def classify_prompt(prompt: str) -> str:
    text = prompt.lower().strip()

    if not text:
        return "simple"

    if len(text) > 1800:
        return "complex"

    if any(word in text for word in COMPLEX_KEYWORDS):
        return "complex"

    if len(text) > 700:
        return "medium"

    if any(word in text for word in MEDIUM_KEYWORDS):
        return "medium"

    if re.search(r"\b(step-by-step|multiple files|end-to-end)\b", text):
        return "complex"

    return "simple"