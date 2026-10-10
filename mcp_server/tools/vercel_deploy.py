import os, base64, requests
from ._common import safe_path

API = "https://api.vercel.com"

def _headers():
    token = os.getenv("VERCEL_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set VERCEL_TOKEN in the environment.")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def _team_params():
    team = os.getenv("VERCEL_TEAM_ID", "").strip()
    return {"teamId": team} if team else {}

def register(mcp):
    @mcp.tool()
    def vercel_list_projects(limit: int = 20) -> str:
        """List Vercel projects accessible to the configured token."""
        r = requests.get(f"{API}/v9/projects", headers=_headers(),
                         params={**_team_params(), "limit": max(1, min(limit, 100))}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return "\n".join(f"{x.get('name')} (id={x.get('id')})" for x in data.get("projects", [])) or "No projects found."

    @mcp.tool()
    def vercel_deploy_project(project_name: str, workspace_path: str = ".", confirm: bool = False) -> str:
        """Deploy a workspace directory to Vercel. Requires confirm=true; only include trusted project files."""
        if not confirm:
            return "Deployment not started. Review the folder and call again with confirm=true."
        root = safe_path(workspace_path)
        if not root.is_dir():
            raise ValueError("workspace_path must be a workspace folder.")
        ignored = {".git", "node_modules", ".venv", "venv", "__pycache__", ".env"}
        files = []
        total_bytes = 0
        for p in root.rglob("*"):
            if not p.is_file() or any(part in ignored for part in p.relative_to(root).parts):
                continue
            rel = p.relative_to(root).as_posix()
            raw = p.read_bytes()
            total_bytes += len(raw)
            if len(files) >= 1000 or total_bytes > 25 * 1024 * 1024:
                raise ValueError("Deployment package exceeds the starter limit (1000 files / 25 MB).")
            files.append({"file": rel, "data": base64.b64encode(raw).decode("ascii"), "encoding": "base64"})
        if not files:
            raise ValueError("No deployable files found in the selected workspace folder.")
        payload = {"name": project_name, "files": files, "target": "production"}
        r = requests.post(f"{API}/v13/deployments", headers=_headers(),
                          params=_team_params(), json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return f"Deployment created: {data.get('url', '(URL pending)')} | state={data.get('readyState', data.get('status', 'unknown'))} | id={data.get('id', 'unknown')}"
