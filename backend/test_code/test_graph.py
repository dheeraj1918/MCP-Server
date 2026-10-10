"""Quick end-to-end test for the LangGraph workflow."""
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.orchestration.graph import run_workflow


async def main() -> None:
    prompts = {
        "1": "What is 2 + 2?",
        "2": "Research the purpose of an MCP server and explain three practical use cases.",
        "3": (
            "Design a Python project with a modular architecture, database integration, "
            "unit tests, error handling, logging, and deployment documentation. "
            "Break it into independent implementation tasks."
        ),
    }
    print("Choose a test:")
    print("  1. Simple prompt")
    print("  2. Retrieval / research")
    print("  3. Complex multi-agent prompt")
    print("  4. Custom prompt")
    choice = input("Choice (1-4): ").strip()

    if choice in prompts:
        prompt = prompts[choice]
    elif choice == "4":
        prompt = input("Enter prompt: ").strip()
        if not prompt:
            print("Prompt cannot be empty.")
            return
    else:
        print("Invalid choice.")
        return

    print(f"\nRunning: {prompt}\n")
    result = await run_workflow(prompt)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    output_path = Path(__file__).resolve().parent / "graph_result.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
