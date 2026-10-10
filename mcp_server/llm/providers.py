import os
from typing import Any

from litellm import completion

from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    GROQ_MODEL,
    GEMINI_MODEL,
    OPENROUTER_FAST_MODEL,
    OPENROUTER_GENERAL_MODEL,
    OPENROUTER_COMPLEX_MODEL,
)

OPENROUTER_MODELS = {
    "fast": OPENROUTER_FAST_MODEL,
    "general": OPENROUTER_GENERAL_MODEL,
    "complex": OPENROUTER_COMPLEX_MODEL,
}

def available_models() -> list[dict[str, str]]:
    models = []

    if GROQ_API_KEY:
        models.append({
            "provider": "groq",
            "model": GROQ_MODEL,
            "tier": "fast",
        })

    if GEMINI_API_KEY:
        models.append({
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "tier": "general",
        })

    if OPENROUTER_API_KEY:
        for tier, model in OPENROUTER_MODELS.items():
            models.append({
                "provider": "openrouter",
                "model": model,
                "tier": tier,
            })

    return models

def chat(
    model: str,
    provider: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    keys = {
        "groq": GROQ_API_KEY,
        "gemini": GEMINI_API_KEY,
        "openrouter": OPENROUTER_API_KEY,
    }

    api_key = keys.get(provider)

    if not api_key:
        raise RuntimeError(
            f"API key for provider '{provider}' is missing."
        )

    response = completion(
        model=model,
        messages=messages,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=90,
    )

    return response.choices[0].message.content or ""