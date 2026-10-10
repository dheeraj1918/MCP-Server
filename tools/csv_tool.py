"""CSV read/write tools restricted to the configured workspace."""
import csv, json
from .common import safe_path

def register(mcp):
    @mcp.tool()
    def csv_read(path: str, max_rows: int = 200) -> str:
        """Read a CSV file and return a JSON array of row objects or row arrays."""
        p=safe_path(path)
        if p.suffix.lower() != ".csv": raise ValueError("path must end in .csv")
        max_rows=max(1,min(max_rows,1000))
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            rows=list(csv.reader(f))[:max_rows]
        return json.dumps(rows, ensure_ascii=False)

    @mcp.tool()
    def csv_write(path: str, rows_json: str) -> str:
        """Write CSV from JSON array of arrays, e.g. [[\"name\",\"age\"],[\"Ana\",20]]."""
        rows=json.loads(rows_json)
        if not isinstance(rows,list) or any(not isinstance(row,list) for row in rows): raise ValueError("rows_json must be a JSON array of arrays")
        if len(rows)>10000: raise ValueError("Maximum 10000 rows")
        p=safe_path(path)
        if p.suffix.lower() != ".csv": raise ValueError("path must end in .csv")
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("w",encoding="utf-8",newline="") as f: csv.writer(f).writerows(rows)
        return f"Wrote {len(rows)} rows to {p.name}"
