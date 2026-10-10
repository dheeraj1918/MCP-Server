from llm.complexity import classify_prompt
from llm.providers import available_models, chat

def route_prompt(prompt: str) -> dict:
    complexity = classify_prompt(prompt)
    models = available_models()

    if not models:
        raise RuntimeError(
            "No LLM providers configured. Add an API key to .env."
        )

    if complexity == "simple":
        preferred = ["groq", "openrouter", "gemini"]
        tier_order = ["fast", "general", "complex"]
    elif complexity == "medium":
        preferred = ["gemini", "groq", "openrouter"]
        tier_order = ["general", "fast", "complex"]
    else:
        preferred = ["openrouter", "gemini", "groq"]
        tier_order = ["complex", "general", "fast"]

    def rank(item):
        return (
            preferred.index(item["provider"]),
            tier_order.index(item["tier"]),
        )

    candidates = sorted(models, key=rank)
    errors = []

    for candidate in candidates:
        try:
            result = chat(
                model=candidate["model"],
                provider=candidate["provider"],
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful technical assistant. "
                            "Be accurate and concise."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            return {
                "success": True,
                "complexity": complexity,
                "provider": candidate["provider"],
                "model": candidate["model"],
                "response": result,
                "fallback_used": len(errors) > 0,
                "errors": errors,
            }

        except Exception as exc:
            # Avoid returning API keys or raw request headers.
            errors.append({
                "provider": candidate["provider"],
                "model": candidate["model"],
                "error": str(exc)[:300],
            })

    return {
        "success": False,
        "complexity": complexity,
        "response": None,
        "fallback_used": len(errors) > 1,
        "errors": errors,
    }