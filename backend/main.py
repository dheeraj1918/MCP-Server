import asyncio
import logging

from backend.orchestration.graph import run_workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("factory_os")


async def main() -> None:
    print("=" * 60)
    print("  FACTORY OS — MULTI-AGENT SYSTEM")
    print("=" * 60)
    print("Enter a task. Type 'exit' to quit.\n")

    while True:
        try:
            prompt = (await asyncio.to_thread(input, "Factory OS > ")).strip()
            if prompt.lower() in {"exit", "quit"}:
                print("Factory OS stopped.")
                return
            if not prompt:
                continue

            print("\nRunning workflow…\n")
            result = await run_workflow(prompt)
            print("-" * 60)
            print("SUCCESS   :", result.get("success", False))
            print("COMPLEXITY:", result.get("complexity", "unknown"))
            print("AGENTS    :", ", ".join(result.get("agents", [])))
            print("\nFINAL ANSWER:\n")
            print(result.get("answer", "No answer returned."))
            if result.get("errors"):
                print("\nWORKFLOW ERRORS:")
                for err in result["errors"]:
                    print(" -", err)
            print("-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\nFactory OS stopped.")
            return
        except Exception as exc:
            logger.exception("Workflow execution failed")
            print(f"\nWorkflow failed: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
