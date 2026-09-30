"""Environment configuration for the community features.

Everything here is optional: with nothing set the API behaves exactly as before and the community
endpoints answer 503, so the rest of the app never depends on a database being present.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse


def database_url() -> str | None:
    """Neon connection string. Use the *pooled* one (host contains -pooler) for app traffic."""
    return os.environ.get("DATABASE_URL") or None


def auth_base_url() -> str | None:
    """Neon Auth URL, e.g. https://ep-xxx.neonauth.eu-central-1.aws.neon.tech/neondb/auth."""
    url = os.environ.get("NEON_AUTH_BASE_URL")
    return url.rstrip("/") if url else None


def auth_origin(base_url: str) -> str:
    """scheme://host of the auth URL: Neon Auth sets the token's issuer and audience to it."""
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def admin_emails() -> frozenset[str]:
    """Comma-separated ADMIN_EMAILS, lower-cased. Only meaningful for a verified email address."""
    raw = os.environ.get("ADMIN_EMAILS", "")
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())
