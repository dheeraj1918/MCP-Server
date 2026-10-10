import os, requests

def register(mcp):
    @mcp.tool()
    def web_search_tool(query: str) -> str:
        """Search the web using an optional configured search endpoint; otherwise return setup guidance."""
        endpoint = os.getenv("WEB_SEARCH_ENDPOINT", "").strip()
        api_key = os.getenv("WEB_SEARCH_API_KEY", "").strip()
        if not endpoint:
            return "Web search is not configured. Set WEB_SEARCH_ENDPOINT and, if required, WEB_SEARCH_API_KEY."
        response = requests.get(endpoint, params={"q": query}, headers={"Authorization": f"Bearer {api_key}"} if api_key else {}, timeout=20)
        response.raise_for_status()
        return response.text[:20000]
