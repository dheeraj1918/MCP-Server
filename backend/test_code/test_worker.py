"""Unit tests for worker helper functions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.agents.worker import (
    _extract_tool_call,
    _extract_files_json,
    _repo_name_from_task,
)
from backend.orchestration.graph import _is_dependent


def test_file_extraction_json():
    text = '{"files": [{"path": "rest-api/app.py", "content": "from flask import Flask"}, {"path": "rest-api/README.md", "content": "# REST API"}]}'
    files = _extract_files_from_text(text)
    assert len(files) == 2, f"Expected 2, got {len(files)}"
    assert files[0]["path"] == "rest-api/app.py"
    print(f"PASS file_extraction_json: {[f['path'] for f in files]}")


def test_file_extraction_history():
    history = [
        {"tool": "workspace_write", "args": {"path": "myapp/app.py", "content": "print(1)"}, "result": "Saved"},
        {"tool": "workspace_write", "args": {"path": "myapp/README.md", "content": "# App"}, "result": "Saved"},
    ]
    files = _collect_files_from_history(history)
    assert len(files) == 2, f"Expected 2, got {len(files)}"
    print(f"PASS file_extraction_history: {[f['path'] for f in files]}")


def test_repo_name():
    name = _repo_name_from_task("Create a GitHub repo named rest-api and push files", "")
    assert name == "rest-api", f"Got: {name}"
    print(f"PASS repo_name: {name}")


def test_dependent():
    assert _is_dependent({"role": "GitHub Publisher", "task": "push"})
    assert not _is_dependent({"role": "Code Generator", "task": "write app"})
    print("PASS dependent detection")


def test_tool_call_plain():
    import json
    obj = {"tool": "github_whoami", "arguments": {}}
    text = json.dumps(obj)
    result = _extract_tool_call(text)
    assert result is not None
    assert result["tool"] == "github_whoami"
    print(f"PASS tool_call_plain: {result}")


def test_tool_call_embedded():
    import json
    obj = {"tool": "github_create_repo", "arguments": {"name": "test", "confirm": True}}
    text = f"Here is my response:\n{json.dumps(obj)}"
    result = _extract_tool_call(text)
    assert result is not None
    assert result["tool"] == "github_create_repo"
    print(f"PASS tool_call_embedded: {result['tool']}")


def test_no_tool_call():
    result = _extract_tool_call("This is just plain text with no tool call.")
    assert result is None
    print("PASS no_tool_call: None as expected")


if __name__ == "__main__":
    test_file_extraction_json()
    test_file_extraction_history()
    test_repo_name()
    test_dependent()
    test_tool_call_plain()
    test_tool_call_embedded()
    test_no_tool_call()
    print("\nAll tests passed.")
