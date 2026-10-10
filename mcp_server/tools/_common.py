import os
from pathlib import Path

def workspace_root() -> Path:
    root = Path(os.getenv("FACTORY_OS_WORKSPACE", "./workspace")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def safe_path(path: str) -> Path:
    """Resolve a user path inside the configured workspace; block path traversal."""
    root = workspace_root()
    candidate = (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path must stay inside the configured workspace.")
    return candidate

def s3_bucket_allowed(bucket: str) -> bool:
    raw = os.getenv("AWS_S3_ALLOWED_BUCKETS", "").strip()
    if not raw:
        return True
    allowed = {item.strip() for item in raw.split(",") if item.strip()}
    return bucket in allowed
