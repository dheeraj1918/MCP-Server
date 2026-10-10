import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from .common import safe_path, s3_bucket_allowed

def _client():
    return boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION") or None)

def _check(bucket):
    if not s3_bucket_allowed(bucket):
        raise PermissionError("Bucket is not in AWS_S3_ALLOWED_BUCKETS.")

def register(mcp):
    @mcp.tool()
    def s3_list_objects(bucket: str, prefix: str = "", max_keys: int = 100) -> str:
        """List S3 object keys in an allowed bucket."""
        _check(bucket); max_keys = max(1, min(max_keys, 1000))
        result = _client().list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
        return "\n".join(f"{o['Key']} ({o['Size']} bytes)" for o in result.get("Contents", [])) or "No objects found."

    @mcp.tool()
    def s3_upload_file(bucket: str, local_path: str, object_key: str) -> str:
        """Upload a workspace file to S3."""
        _check(bucket); p = safe_path(local_path)
        if not p.is_file(): raise FileNotFoundError(local_path)
        _client().upload_file(str(p), bucket, object_key)
        return f"Uploaded {p.name} to s3://{bucket}/{object_key}"

    @mcp.tool()
    def s3_download_file(bucket: str, object_key: str, local_path: str) -> str:
        """Download an S3 object into the workspace."""
        _check(bucket); p = safe_path(local_path); p.parent.mkdir(parents=True, exist_ok=True)
        _client().download_file(bucket, object_key, str(p))
        return f"Downloaded s3://{bucket}/{object_key} to {p.name}"

    @mcp.tool()
    def s3_delete_object(bucket: str, object_key: str, confirm: bool = False) -> str:
        """Delete an S3 object. Requires confirm=true because this action is destructive."""
        _check(bucket)
        if not confirm: return "Not deleted. Call again with confirm=true after verifying the bucket and key."
        _client().delete_object(Bucket=bucket, Key=object_key)
        return f"Delete request sent for s3://{bucket}/{object_key}"
