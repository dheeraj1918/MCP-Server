from llm.providers import available_models, chat
from llm.complexity import classify_prompt


def route_prompt(prompt: str) -> dict:
    complexity = classify_prompt(prompt)
    models = available_models()

    if not models:
        return {
            "success": False,
            "complexity": complexity,
            "response": None,
            "fallback_used": False,
            "errors": [{"provider": "all", "model": "all",
                        "error": "No LLM providers configured. Add an API key to mcp_server/.env."}],
        }

    # complexity is now "simple" | "moderate" | "complex" — matching planner schema
    if complexity == "simple":
        preferred = ["groq", "openrouter", "gemini"]
        tier_order = ["fast", "general", "complex"]
    elif complexity == "moderate":
        preferred = ["gemini", "groq", "openrouter"]
        tier_order = ["general", "fast", "complex"]
    else:  # complex
        preferred = ["openrouter", "gemini", "groq"]
        tier_order = ["complex", "general", "fast"]

    def rank(item):
        p = preferred.index(item["provider"]) if item["provider"] in preferred else len(preferred)
        t = tier_order.index(item["tier"]) if item["tier"] in tier_order else len(tier_order)
        return (p, t)

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
                            "You are a helpful, accurate technical assistant. "
                            "Be concise and direct."
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
