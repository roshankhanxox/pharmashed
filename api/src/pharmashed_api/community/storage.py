"""Object storage for report photos: the private Neon storage bucket, through its S3-compatible API."""

from __future__ import annotations

import os
import threading
from typing import Any

import boto3
from botocore.config import Config

PRESIGN_SECONDS = 300
_lock = threading.Lock()
_client: Any = None


def is_configured() -> bool:
    """True when the endpoint, keys and bucket are all set."""
    return all(os.environ.get(k) for k in ("AWS_ENDPOINT_URL_S3", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET"))


def bucket() -> str:
    return os.environ["S3_BUCKET"]


def client() -> Any:
    """The shared S3 client (created on first use)."""
    global _client
    with _lock:
        if _client is None:
            _client = boto3.client(
                "s3",
                endpoint_url=os.environ["AWS_ENDPOINT_URL_S3"],
                region_name=os.environ.get("AWS_REGION", "us-east-2"),
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                              retries={"max_attempts": 2}, connect_timeout=10, read_timeout=30),
            )
        return _client


def reset_client() -> None:
    """Forget the shared client (tests and key rotation)."""
    global _client
    _client = None


def put(key: str, data: bytes, content_type: str) -> None:
    client().put_object(Bucket=bucket(), Key=key, Body=data, ContentType=content_type)


def presigned_get(key: str, seconds: int = PRESIGN_SECONDS) -> str:
    """A short-lived link to a private object."""
    return client().generate_presigned_url("get_object", Params={"Bucket": bucket(), "Key": key}, ExpiresIn=seconds)


def delete(key: str) -> None:
    client().delete_object(Bucket=bucket(), Key=key)
