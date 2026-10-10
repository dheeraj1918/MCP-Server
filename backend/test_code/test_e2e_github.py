"""
End-to-end test: generate a REST API project and push it to GitHub.
Run with:  uv run python backend/test_code/test_e2e_github.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.agents.worker import (
    _get_file_plan,
    _generate_one_file,
    _run_code_generator,
    _run_github_publisher,
    _repo_name_from_task,
)


async def main():
    prompt = "create a small REST API with Flask that has CRUD endpoints for users"
    task = {
        "name": "worker_1",
        "role": "Code Generator",
        "type": "general",
        "task": "Write a Flask REST API with GET /users, POST /users, PUT /users/:id, DELETE /users/:id. Use in-memory storage.",
    }

    print("=" * 60)
    print("STEP 1: Get file plan")
    folder = _repo_name_from_task(task["task"], prompt) or "flask-rest-api"
    print(f"  Folder: {folder}")

    plan = await _get_file_plan(prompt, task["task"], folder)
    print(f"  Files planned: {[p['path'] for p in plan]}")
    assert len(plan) >= 2, "Expected at least 2 files"
    assert any("README" in p["path"] for p in plan), "Missing README"

    print("\nSTEP 2: Generate each file")
    for item in plan:
        content = await _generate_one_file(item["path"], item.get("description", ""), task["task"], folder)
        print(f"  {item['path']}: {len(content)} chars")
        assert len(content) > 10, f"File {item['path']} is too short: {content!r}"

    print("\nSTEP 3: Run full code generator")
    # tool_map with no workspace_write (files held in memory only)
    result = await _run_code_generator(
        prompt=prompt, task=task, tool_map={}, complexity="moderate"
    )
    print(f"  success={result['success']}, files={len(result.get('files', []))}")
    print(f"  result preview: {result['result'][:200]}")
    assert result["success"], f"Code generator failed: {result['result']}"
    assert len(result["files"]) >= 2, "Expected at least 2 files"

    print("\nSTEP 4: Run GitHub Publisher with generated files")
    pub_task = {
        "name": "worker_2",
        "role": "GitHub Publisher",
        "type": "general",
        "task": f"Create GitHub repo named {folder} and push all files",
    }

    from backend.services.mcp_client import get_mcp_tools
    tools = await get_mcp_tools()
    tool_map = {t.name: t for t in tools}

    pub_result = await _run_github_publisher(
        prompt=prompt,
        task=pub_task,
        tool_map=tool_map,
        prior_results=[result],
    )
    print(f"  success={pub_result['success']}")
    print(f"  tools used: {pub_result.get('tools_used', [])}")
    print(f"  result:\n{pub_result['result']}")

    if pub_result["success"]:
        print("\n✅ END-TO-END TEST PASSED")
    else:
        print("\n❌ Publisher failed (check GitHub token / network)")


if __name__ == "__main__":
    asyncio.run(main())
