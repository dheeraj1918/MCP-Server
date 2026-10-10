import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from llm.providers import available_models
from llm.complexity import classify_prompt
from llm.model_router import route_prompt


def test_provider_configuration():
    models = available_models()

    print("\n=== CONFIGURED MODELS ===")

    if not models:
        print("FAIL: No provider API keys configured.")
        return False

    for item in models:
        print(
            f"Provider: {item['provider']} | "
            f"Model: {item['model']} | "
            f"Tier: {item['tier']}"
        )

    return True


def test_complexity():
    prompts = [
        "What is Python?",
        "Write a program to create a REST API.",
        (
            "Design a production-ready multi-agent architecture "
            "with distributed task execution, database isolation, "
            "security controls, observability, and automatic "
            "LLM fallback across multiple providers."
        ),
    ]

    print("\n=== PROMPT CLASSIFICATION ===")

    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        print(f"Complexity: {classify_prompt(prompt)}")


def test_routing():
    prompts = [
        "What is 2 + 2?",
        "Explain how Python decorators work.",
        (
            "Design a fault-tolerant distributed system with "
            "multiple agents, retries, security, and observability."
        ),
    ]

    print("\n=== LLM ROUTING TEST ===")

    for prompt in prompts:
        print(f"\nPrompt: {prompt}")

        result = route_prompt(prompt)

        print(f"Success: {result['success']}")
        print(f"Complexity: {result['complexity']}")
        print(f"Provider: {result.get('provider', 'None')}")
        print(f"Model: {result.get('model', 'None')}")
        print(f"Fallback used: {result['fallback_used']}")

        if result["success"]:
            print(f"Response: {result['response'][:300]}")
        else:
            print(f"Errors: {result['errors']}")


if __name__ == "__main__":
    test_provider_configuration()
    test_complexity()
    test_routing()