import ipaddress, socket
from urllib.parse import urlparse
import requests

def _validate_public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS URLs are allowed.")
    host = parsed.hostname.lower()
    if host in ("localhost",) or host.endswith(".local"):
        raise ValueError("Local hosts are not allowed.")
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if not ip.is_global: raise ValueError("Non-public IP destinations are not allowed.")
    except socket.gaierror as exc:
        raise ValueError("Unable to resolve host.") from exc

def register(mcp):
    @mcp.tool()
    def http_get_text(url: str) -> str:
        """Fetch text from a public HTTPS URL (private/local destinations are blocked)."""
        _validate_public_url(url)
        r = requests.get(url, timeout=15, allow_redirects=False, headers={"User-Agent": "FactoryOS-MCP/1.0"})
        r.raise_for_status()
        return r.text[:20000]

    @mcp.tool()
    def http_post_json(url: str, json_body: str) -> str:
        """POST JSON to a public HTTPS endpoint. Use only with endpoints you are authorized to call."""
        import json
        _validate_public_url(url)
        body = json.loads(json_body)
        r = requests.post(url, json=body, timeout=15, allow_redirects=False,
                          headers={"User-Agent": "FactoryOS-MCP/1.0"})
        r.raise_for_status()
        return r.text[:20000]
