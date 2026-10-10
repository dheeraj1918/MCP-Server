import sqlite3, os
from pathlib import Path

DB = Path(os.getenv("FACTORY_OS_MEMORY_DB", "./workspace/memory.db"))
DB.parent.mkdir(parents=True, exist_ok=True)

def _init():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, key TEXT NOT NULL,
            value TEXT NOT NULL, memory_type TEXT DEFAULT 'general',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, key))""")
_init()

def register(mcp):
    @mcp.tool()
    def memory_store(user_id: str, key: str, value: str, memory_type: str = "general") -> str:
        """Store or replace a memory for a user."""
        with sqlite3.connect(DB) as con:
            con.execute("""INSERT INTO memories(user_id,key,value,memory_type,updated_at)
                VALUES(?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id,key) DO UPDATE SET
                value=excluded.value,memory_type=excluded.memory_type,updated_at=CURRENT_TIMESTAMP""",
                (user_id,key,value,memory_type))
        return "Memory saved."

    @mcp.tool()
    def memory_search(user_id: str, query: str, limit: int = 10) -> str:
        """Search a user's memories by key or value text."""
        limit = max(1, min(limit, 50))
        with sqlite3.connect(DB) as con:
            rows = con.execute("""SELECT key,value,memory_type,updated_at FROM memories
                WHERE user_id=? AND (key LIKE ? OR value LIKE ?) ORDER BY updated_at DESC LIMIT ?""",
                (user_id, f"%{query}%", f"%{query}%", limit)).fetchall()
        return "\n".join(f"{k} [{t}] ({d}): {v}" for k,v,t,d in rows) or "No matching memories."
