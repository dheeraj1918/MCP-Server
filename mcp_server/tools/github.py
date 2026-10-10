"""GitHub REST API tools.

Covers: repo info, issues, creating repos, pushing files, and reading file contents.
GITHUB_TOKEN is required for all write operations and private repo access.
"""
import base64
import os
import requests

API = "https://api.github.com"


def _headers(write: bool = False) -> dict:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if write and not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Add it to mcp_server/.env.\n"
            "Create one at https://github.com/settings/tokens — needs 'repo' scope."
        )
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _whoami() -> str:
    """Return the authenticated user's login."""
    r = requests.get(f"{API}/user", headers=_headers(write=True), timeout=15)
    r.raise_for_status()
    return r.json()["login"]


def register(mcp):

    # ── read tools ───────────────────────────────────────────────────────────

    @mcp.tool()
    def github_whoami() -> str:
        """Return the GitHub username of the authenticated token owner."""
        return _whoami()

    @mcp.tool()
    def github_repo_info(owner: str, repo: str) -> str:
        """Get public or token-accessible GitHub repository metadata."""
        r = requests.get(
            f"{API}/repos/{owner}/{repo}", headers=_headers(), timeout=20
        )
        r.raise_for_status()
        d = r.json()
        return (
            f"{d.get('full_name')} | stars={d.get('stargazers_count')} "
            f"| language={d.get('language')} "
            f"| default_branch={d.get('default_branch')} "
            f"| url={d.get('html_url')} "
            f"| description={d.get('description')}"
        )

    @mcp.tool()
    def github_list_repos(limit: int = 30) -> str:
        """List repositories belonging to the authenticated user."""
        limit = max(1, min(limit, 100))
        r = requests.get(
            f"{API}/user/repos",
            headers=_headers(write=True),
            params={"per_page": limit, "sort": "updated"},
            timeout=20,
        )
        r.raise_for_status()
        items = r.json()
        return "\n".join(
            f"{x['full_name']} ({x['visibility']}) — {x.get('description') or 'no description'}"
            for x in items
        ) or "No repositories found."

    @mcp.tool()
    def github_list_issues(owner: str, repo: str, state: str = "open", limit: int = 20) -> str:
        """List repository issues. state must be open, closed, or all."""
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be open, closed, or all")
        r = requests.get(
            f"{API}/repos/{owner}/{repo}/issues",
            headers=_headers(),
            params={"state": state, "per_page": max(1, min(limit, 100))},
            timeout=20,
        )
        r.raise_for_status()
        items = r.json()
        return "\n".join(
            f"#{x['number']} [{x['state']}] {x['title']} — {x['html_url']}"
            for x in items
            if "pull_request" not in x
        ) or "No issues found."

    @mcp.tool()
    def github_get_file(owner: str, repo: str, path: str, ref: str = "") -> str:
        """Read the contents of a file from a GitHub repository."""
        params = {"ref": ref} if ref else {}
        r = requests.get(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(),
            params=params,
            timeout=20,
        )
        r.raise_for_status()
        d = r.json()
        if d.get("encoding") == "base64":
            return base64.b64decode(d["content"]).decode("utf-8", errors="replace")
        return d.get("content", "")

    @mcp.tool()
    def github_list_files(owner: str, repo: str, path: str = "", ref: str = "") -> str:
        """List files and directories at a path in a GitHub repository."""
        params = {"ref": ref} if ref else {}
        r = requests.get(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(),
            params=params,
            timeout=20,
        )
        r.raise_for_status()
        items = r.json()
        if isinstance(items, dict):
            return f"{items['type']}: {items['name']}"
        return "\n".join(f"[{x['type']}] {x['path']}" for x in items)

    # ── write tools ──────────────────────────────────────────────────────────

    @mcp.tool()
    def github_create_repo(
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
        confirm: bool = False,
    ) -> str:
        """Create a new GitHub repository for the authenticated user.

        Requires GITHUB_TOKEN with 'repo' scope and confirm=true.
        auto_init=true creates an initial README so the repo has a default branch.
        """
        if not confirm:
            return (
                f"Repository '{name}' not created. "
                "Review the details and call again with confirm=true."
            )
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        r = requests.post(
            f"{API}/user/repos",
            headers=_headers(write=True),
            json=payload,
            timeout=20,
        )
        if r.status_code == 422:
            data = r.json()
            errors = "; ".join(e.get("message", "") for e in data.get("errors", []))
            return f"Repository creation failed: {data.get('message', '')} — {errors}"
        r.raise_for_status()
        d = r.json()
        return (
            f"Created repository: {d['full_name']}\n"
            f"URL: {d['html_url']}\n"
            f"Default branch: {d.get('default_branch', 'main')}\n"
            f"Clone: {d['clone_url']}"
        )

    @mcp.tool()
    def github_push_file(
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str = "Add file via Factory OS",
        branch: str = "",
        confirm: bool = False,
    ) -> str:
        """Create or update a single file in a GitHub repository.

        Requires GITHUB_TOKEN with 'repo' scope and confirm=true.
        content is the raw UTF-8 text of the file.
        branch defaults to the repository's default branch.
        """
        if not confirm:
            return (
                f"File '{path}' not pushed. "
                "Review the file path and content, then call again with confirm=true."
            )

        # Resolve the branch
        if not branch:
            repo_r = requests.get(
                f"{API}/repos/{owner}/{repo}", headers=_headers(write=True), timeout=15
            )
            repo_r.raise_for_status()
            branch = repo_r.json().get("default_branch", "main")

        # Check if the file already exists (needed for the SHA to update it)
        sha = None
        check = requests.get(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(write=True),
            params={"ref": branch},
            timeout=15,
        )
        if check.status_code == 200:
            sha = check.json().get("sha")

        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        payload: dict = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(write=True),
            json=payload,
            timeout=20,
        )
        r.raise_for_status()
        d = r.json()
        action = "Updated" if sha else "Created"
        return (
            f"{action} {path} in {owner}/{repo} on branch '{branch}'.\n"
            f"Commit: {d['commit']['sha'][:7]} — {d['commit']['html_url']}"
        )

    @mcp.tool()
    def github_push_files(
        owner: str,
        repo: str,
        files_json: str,
        message: str = "Add files via Factory OS",
        branch: str = "",
        confirm: bool = False,
    ) -> str:
        """Push multiple files to a GitHub repository in one commit using the Git Trees API.

        files_json is a JSON array of objects: [{"path": "src/main.py", "content": "..."}]
        Requires GITHUB_TOKEN with 'repo' scope and confirm=true.
        """
        import json

        if not confirm:
            return (
                "Files not pushed. Review the file list, "
                "then call again with confirm=true."
            )

        files = json.loads(files_json)
        if not isinstance(files, list) or not files:
            raise ValueError("files_json must be a non-empty JSON array of {path, content} objects.")

        hdrs = _headers(write=True)

        # Resolve default branch
        if not branch:
            repo_r = requests.get(f"{API}/repos/{owner}/{repo}", headers=hdrs, timeout=15)
            repo_r.raise_for_status()
            branch = repo_r.json().get("default_branch", "main")

        # Get the HEAD commit SHA and tree SHA
        ref_r = requests.get(
            f"{API}/repos/{owner}/{repo}/git/ref/heads/{branch}",
            headers=hdrs, timeout=15,
        )
        ref_r.raise_for_status()
        head_sha = ref_r.json()["object"]["sha"]

        commit_r = requests.get(
            f"{API}/repos/{owner}/{repo}/git/commits/{head_sha}",
            headers=hdrs, timeout=15,
        )
        commit_r.raise_for_status()
        base_tree_sha = commit_r.json()["tree"]["sha"]

        # Build the tree
        tree = []
        for f in files:
            fpath = f.get("path", "").strip()
            fcontent = f.get("content", "")
            if not fpath:
                continue
            # Create a blob
            blob_r = requests.post(
                f"{API}/repos/{owner}/{repo}/git/blobs",
                headers=hdrs,
                json={"content": fcontent, "encoding": "utf-8"},
                timeout=20,
            )
            blob_r.raise_for_status()
            tree.append({
                "path": fpath,
                "mode": "100644",
                "type": "blob",
                "sha": blob_r.json()["sha"],
            })

        # Create the tree
        new_tree_r = requests.post(
            f"{API}/repos/{owner}/{repo}/git/trees",
            headers=hdrs,
            json={"base_tree": base_tree_sha, "tree": tree},
            timeout=20,
        )
        new_tree_r.raise_for_status()
        new_tree_sha = new_tree_r.json()["sha"]

        # Create the commit
        new_commit_r = requests.post(
            f"{API}/repos/{owner}/{repo}/git/commits",
            headers=hdrs,
            json={"message": message, "tree": new_tree_sha, "parents": [head_sha]},
            timeout=20,
        )
        new_commit_r.raise_for_status()
        new_commit_sha = new_commit_r.json()["sha"]

        # Update the ref
        requests.patch(
            f"{API}/repos/{owner}/{repo}/git/refs/heads/{branch}",
            headers=hdrs,
            json={"sha": new_commit_sha},
            timeout=15,
        ).raise_for_status()

        repo_url = f"https://github.com/{owner}/{repo}"
        return (
            f"Pushed {len(tree)} file(s) to {owner}/{repo} on branch '{branch}'.\n"
            f"Commit: {new_commit_sha[:7]}\n"
            f"Repository: {repo_url}"
        )

    @mcp.tool()
    def github_create_issue(
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        confirm: bool = False,
    ) -> str:
        """Create a GitHub issue. Requires GITHUB_TOKEN and confirm=true."""
        if not confirm:
            return "Issue not created. Review details and call again with confirm=true."
        r = requests.post(
            f"{API}/repos/{owner}/{repo}/issues",
            headers=_headers(write=True),
            json={"title": title, "body": body},
            timeout=20,
        )
        r.raise_for_status()
        d = r.json()
        return f"Created issue #{d['number']}: {d['html_url']}"
