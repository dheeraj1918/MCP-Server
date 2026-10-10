"""Test LLM responses for file generation prompts."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from llm.model_router import route_prompt


def test_file_plan():
    """Test that the LLM returns a parseable file plan."""
    prompt = (
        "List the files needed for a Flask REST API project as a JSON array.\n"
        "Folder: flask-rest-api/\n"
        "Return ONLY a JSON array like this:\n"
        '[{"path": "flask-rest-api/app.py", "description": "Main app"},'
        '{"path": "flask-rest-api/requirements.txt", "description": "Deps"},'
        '{"path": "flask-rest-api/README.md", "description": "Docs"}]'
    )
    result = route_prompt(prompt)
    print(f"success: {result['success']}, provider: {result.get('provider')}")
    resp = result.get("response", "")
    print(f"response ({len(resp)} chars): {resp[:300]}")

    start, end = resp.find("["), resp.rfind("]")
    if start >= 0 and end > start:
        try:
            plan = json.loads(resp[start:end + 1])
            print(f"Parsed {len(plan)} files: {[p.get('path') for p in plan]}")
            return True
        except Exception as e:
            print(f"JSON parse failed: {e}")
    else:
        print("No JSON array found in response")
    return False


def test_single_file():
    """Test generating a single file."""
    prompt = (
        "Write the complete content for flask-rest-api/app.py\n"
        "A Flask REST API with GET /users and POST /users using in-memory storage.\n"
        "Return ONLY the raw Python code, no markdown fences, no explanation."
    )
    result = route_prompt(prompt)
    resp = result.get("response", "")
    print(f"app.py ({len(resp)} chars)")
    print(f"First 200 chars: {resp[:200]}")
    has_flask = "flask" in resp.lower() or "Flask" in resp
    has_route = "@app.route" in resp or "app.route" in resp
    print(f"Has flask: {has_flask}, has route: {has_route}")
    return bool(resp) and len(resp) > 50


def test_requirements():
    """Test generating requirements.txt."""
    prompt = (
        "Write the requirements.txt for a Flask REST API project.\n"
        "Return ONLY the file content (one package per line with versions). No explanation."
    )
    result = route_prompt(prompt)
    resp = result.get("response", "")
    print(f"requirements.txt ({len(resp)} chars): {resp[:200]}")
    return "flask" in resp.lower()


if __name__ == "__main__":
    print("=" * 50)
    print("TEST 1: File plan")
    ok1 = test_file_plan()

    print("\nTEST 2: Single file generation")
    ok2 = test_single_file()

    print("\nTEST 3: Requirements.txt")
    ok3 = test_requirements()

    print("\n" + "=" * 50)
    print(f"Results: plan={ok1}, file={ok2}, reqs={ok3}")
    if ok1 and ok2 and ok3:
        print("ALL PASS")
    else:
        print("SOME FAILED")
        sys.exit(1)
