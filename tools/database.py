import sqlite3
from .common import safe_path

def register(mcp):
    @mcp.tool()
    def sqlite_read_query(db_path: str, query: str, limit: int = 100) -> str:
        """Run a read-only SELECT query against a SQLite database in the workspace."""
        if not query.lstrip().lower().startswith("select"):
            raise ValueError("Only SELECT queries are permitted.")
        limit = max(1, min(limit, 500))
        p = safe_path(db_path)
        uri = f"file:{p.as_posix()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(query)
            rows = cur.fetchmany(limit)
            return str({"columns": [d[0] for d in cur.description or []], "rows": rows})
        finally:
            con.close()
