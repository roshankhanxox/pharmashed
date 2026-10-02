"""Verifying Neon Auth tokens.

Neon Auth (managed Better Auth) signs JWTs with EdDSA (Ed25519) and publishes its public keys at
{auth URL}/.well-known/jwks.json. The token's issuer and audience are the auth URL's origin, it
expires after 15 minutes, and `sub` is the user id. We accept only EdDSA (never `none`, and never an
HMAC algorithm that could be confused with the public key), and require the claims we rely on.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

import jwt
from fastapi import Depends, HTTPException, Request
from jwt import PyJWKClient

from pharmashed_api.community import config

ALGORITHMS = ["EdDSA"]
REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub"]
LEEWAY_SECONDS = 10  # tolerate small clock differences between Neon and this server


class AuthError(Exception):
    """The token is missing, malformed, expired, or not signed by the auth service."""


class AuthUnavailable(Exception):
    """We could not reach the auth service's key list, so we cannot say either way."""


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None
    email_verified: bool
    name: str | None

    @property
    def is_admin(self) -> bool:
        """Admin only if the email is listed in ADMIN_EMAILS *and* the auth service verified it."""
        return bool(self.email and self.email_verified and self.email.lower() in config.admin_emails())


class TokenVerifier:
    """Checks a bearer token against the auth service's public keys."""

    def __init__(self, base_url: str, key_resolver: Callable[[str], Any] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.origin = config.auth_origin(self.base_url)
        if key_resolver is None:
            client = PyJWKClient(f"{self.base_url}/.well-known/jwks.json", cache_keys=True, lifespan=3600, timeout=10)
            key_resolver = lambda token: client.get_signing_key_from_jwt(token).key  # noqa: E731
        self._resolve_key = key_resolver

    def verify(self, token: str) -> AuthUser:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthError("malformed token") from exc
        # Refuse anything but EdDSA before touching the network or the keys: this shuts out
        # alg=none and HMAC-with-the-public-key downgrade attempts.
        if header.get("alg") not in ALGORITHMS:
            raise AuthError("unsupported token algorithm")

        try:
            key = self._resolve_key(token)
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthUnavailable("could not fetch the auth service's keys") from exc
        except jwt.PyJWTError as exc:
            raise AuthError("no matching signing key") from exc

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self.origin,
                issuer=self.origin,
                leeway=LEEWAY_SECONDS,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as exc:
            raise AuthError(str(exc)) from exc

        return AuthUser(
            id=str(claims["sub"]),
            email=claims.get("email"),
            email_verified=bool(claims.get("emailVerified", False)),
            name=claims.get("name"),
        )


_verifier: TokenVerifier | None = None
_verifier_lock = threading.Lock()


def get_verifier() -> TokenVerifier | None:
    """The shared verifier, or None when NEON_AUTH_BASE_URL is not set."""
    global _verifier
    base = config.auth_base_url()
    if base is None:
        return None
    with _verifier_lock:
        if _verifier is None or _verifier.base_url != base:
            _verifier = TokenVerifier(base)
        return _verifier


def set_verifier(verifier: TokenVerifier | None) -> None:
    """Install a verifier (tests use a fixed-key one)."""
    global _verifier
    _verifier = verifier


def auth_configured() -> bool:
    return _verifier is not None or config.auth_base_url() is not None


def current_user(request: Request) -> AuthUser:
    """FastAPI dependency: the signed-in user, or 401. 503 if sign-in is not set up at all."""
    verifier = get_verifier()
    if verifier is None:
        raise HTTPException(503, "Sign-in is not configured on this server.")
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Sign in to do that.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return verifier.verify(token.strip())
    except AuthError as exc:
        raise HTTPException(401, f"Your sign-in is not valid ({exc}). Please sign in again.",
                            headers={"WWW-Authenticate": "Bearer"}) from exc
    except AuthUnavailable as exc:
        raise HTTPException(503, "Sign-in service is temporarily unreachable. Try again shortly.") from exc


def optional_user(request: Request) -> AuthUser | None:
    """For public reads that personalise when someone is signed in: the user, or None.

    A missing, invalid or unverifiable token means "anonymous", never an error.
    """
    if not request.headers.get("authorization"):
        return None
    try:
        return current_user(request)
    except HTTPException:
        return None


CurrentUser = Depends(current_user)
OptionalUser = Depends(optional_user)
