import json
from ._common import safe_path

def register(mcp):
    @mcp.tool()
    def json_read(path: str) -> str:
        """Read a JSON file from the workspace."""
        p = safe_path(path)
        return p.read_text(encoding="utf-8")

    @mcp.tool()
    def json_write(path: str, json_text: str) -> str:
        """Validate and write JSON text to a workspace file."""
        obj = json.loads(json_text)
        p = safe_path(path); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Saved valid JSON to {p.name}"
