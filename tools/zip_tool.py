import zipfile
from .common import safe_path

def register(mcp):
    @mcp.tool()
    def zip_create(paths_csv: str, output_path: str) -> str:
        """Create a ZIP archive from workspace files. paths_csv is comma-separated."""
        paths = [safe_path(x.strip()) for x in paths_csv.split(",") if x.strip()]
        out = safe_path(output_path)
        if out.suffix.lower() != ".zip": raise ValueError("Output path must end in .zip")
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                if not p.is_file(): raise FileNotFoundError(str(p))
                if p.resolve() == out.resolve(): raise ValueError("Output cannot be included in itself.")
                zf.write(p, arcname=p.name)
        return f"Created {out.name} with {len(paths)} files"

    @mcp.tool()
    def zip_list(path: str) -> str:
        """List filenames in a ZIP archive in the workspace."""
        p = safe_path(path)
        with zipfile.ZipFile(p) as zf:
            return "\n".join(zf.namelist())
