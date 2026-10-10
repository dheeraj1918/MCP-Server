"""Small deterministic utilities useful to agents."""
import base64, hashlib, json, uuid
from datetime import datetime, timezone

def register(mcp):
    @mcp.tool()
    def current_datetime() -> str:
        """Return the current UTC date and time in ISO-8601 format."""
        return datetime.now(timezone.utc).isoformat()

    @mcp.tool()
    def generate_uuid() -> str:
        """Generate a random UUID4."""
        return str(uuid.uuid4())

    @mcp.tool()
    def text_hash(text: str, algorithm: str = "sha256") -> str:
        """Hash text with sha256, sha1, or md5 (for checksums, not security decisions)."""
        if algorithm not in {"sha256", "sha1", "md5"}: raise ValueError("algorithm must be sha256, sha1, or md5")
        return hashlib.new(algorithm, text.encode("utf-8")).hexdigest()

    @mcp.tool()
    def base64_encode_text(text: str) -> str:
        """Base64-encode UTF-8 text."""
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    @mcp.tool()
    def base64_decode_text(encoded: str) -> str:
        """Decode base64 text as UTF-8, validating input."""
        return base64.b64decode(encoded, validate=True).decode("utf-8")

    @mcp.tool()
    def json_query(json_text: str, dotted_path: str) -> str:
        """Read a simple dotted path from JSON, e.g. customer.address.city or items.0.name."""
        value=json.loads(json_text)
        for part in filter(None, dotted_path.split('.')):
            if isinstance(value,dict): value=value[part]
            elif isinstance(value,list): value=value[int(part)]
            else: raise ValueError(f"Cannot traverse {part!r} through a scalar value")
        return json.dumps(value,ensure_ascii=False,indent=2,default=str)
