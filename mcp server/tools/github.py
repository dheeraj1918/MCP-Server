"""GitHub REST API tools. Token is optional for public read operations."""
import os
import requests

API = "https://api.github.com"

def _headers(write=False):
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if write and not token:
        raise RuntimeError("GITHUB_TOKEN is required for this write operation.")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def register(mcp):
    @mcp.tool()
    def github_repo_info(owner: str, repo: str) -> str:
        """Get public or token-accessible GitHub repository metadata."""
        r = requests.get(f"{API}/repos/{owner}/{repo}", headers=_headers(), timeout=20)
        r.raise_for_status(); d = r.json()
        return f"{d.get('full_name')} | stars={d.get('stargazers_count')} | language={d.get('language')} | default_branch={d.get('default_branch')} | url={d.get('html_url')} | description={d.get('description')}"

    @mcp.tool()
    def github_list_issues(owner: str, repo: str, state: str = "open", limit: int = 20) -> str:
        """List repository issues; state must be open, closed, or all."""
        if state not in {"open", "closed", "all"}: raise ValueError("state must be open, closed, or all")
        r = requests.get(f"{API}/repos/{owner}/{repo}/issues", headers=_headers(), params={"state": state, "per_page": max(1,min(limit,100))}, timeout=20)
        r.raise_for_status(); items = r.json()
        return "\n".join(f"#{x['number']} [{x['state']}] {x['title']} — {x['html_url']}" for x in items if "pull_request" not in x) or "No issues found."

    @mcp.tool()
    def github_create_issue(owner: str, repo: str, title: str, body: str = "", confirm: bool = False) -> str:
        """Create a GitHub issue. Requires GITHUB_TOKEN and confirm=true."""
        if not confirm: return "Issue not created. Review details and call again with confirm=true."
        r = requests.post(f"{API}/repos/{owner}/{repo}/issues", headers=_headers(write=True), json={"title": title, "body": body}, timeout=20)
        r.raise_for_status(); d = r.json()
        return f"Created issue #{d['number']}: {d['html_url']}"
