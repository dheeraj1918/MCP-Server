from ._common import safe_path, workspace_root

def register(mcp):
    @mcp.tool()
    def workspace_list(path: str = ".") -> str:
        """List files and folders in the workspace or a workspace subfolder."""
        p = safe_path(path)
        if not p.exists(): return "Path does not exist."
        if not p.is_dir(): return f"{p.name} is a file."
        return "\n".join(("[DIR] " if x.is_dir() else "[FILE] ") + x.name for x in sorted(p.iterdir()))

    @mcp.tool()
    def workspace_read(path: str, max_chars: int = 20000) -> str:
        """Read a UTF-8 text file from the workspace."""
        if max_chars < 1 or max_chars > 100000: raise ValueError("max_chars must be 1..100000")
        p = safe_path(path)
        if not p.is_file(): raise FileNotFoundError(path)
        return p.read_text(encoding="utf-8")[:max_chars]

    @mcp.tool()
    def workspace_write(path: str, content: str) -> str:
        """Write UTF-8 text inside the workspace."""
        p = safe_path(path); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Saved {p.name} ({len(content)} characters)."


def _register_search(mcp):
    @mcp.tool()
    def workspace_search(query: str, path: str = ".", max_files: int = 200) -> str:
        """Search text files in the workspace for a case-insensitive phrase."""
        root = safe_path(path)
        if not root.exists(): raise FileNotFoundError(path)
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        results = []
        for p in files[:max(1, min(max_files, 1000))]:
            if p.suffix.lower() not in {".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".csv", ".html", ".css", ".yml", ".yaml", ".toml", ".ini", ".sql"}:
                continue
            try: lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError: continue
            for number, line in enumerate(lines, 1):
                if query.casefold() in line.casefold():
                    results.append(f"{p.relative_to(workspace_root())}:{number}: {line[:300]}")
                    if len(results) >= 100: return "\n".join(results)
        return "\n".join(results) or "No matches found."

_original_register = register
def register(mcp):
    _original_register(mcp)
    _register_search(mcp)
