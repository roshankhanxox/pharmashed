"""Neon Auth token verification. No network: a fixed Ed25519 key stands in for the JWKS."""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pharmashed_api.community import auth
from pharmashed_api.community.auth import AuthError, AuthUnavailable, AuthUser, TokenVerifier

BASE = "https://ep-test.neonauth.example.test/neondb/auth"
ORIGIN = "https://ep-test.neonauth.example.test"

KEY = Ed25519PrivateKey.generate()
OTHER_KEY = Ed25519PrivateKey.generate()


def make_token(key=KEY, alg="EdDSA", **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": "user-123", "id": "user-123", "iss": ORIGIN, "aud": ORIGIN, "iat": now, "exp": now + 900,
        "email": "Person@Example.com", "emailVerified": True, "name": "Pat Person",
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": "k1"})


@pytest.fixture
def verifier():
    return TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key())


def test_a_valid_token_gives_the_user(verifier):
    user = verifier.verify(make_token())
    assert user == AuthUser(id="user-123", email="Person@Example.com", email_verified=True, name="Pat Person")


def test_issuer_and_audience_come_from_the_auth_url_origin():
    assert TokenVerifier(BASE + "/", key_resolver=lambda t: None).origin == ORIGIN


@pytest.mark.parametrize("overrides, why", [
    ({"exp": int(time.time()) - 3600}, "expired"),
    ({"iss": "https://evil.example.test"}, "wrong issuer"),
    ({"aud": "https://evil.example.test"}, "wrong audience"),
    ({"sub": None}, "missing subject"),
    ({"exp": None}, "missing expiry"),
])
def test_bad_claims_are_rejected(verifier, overrides, why):
    with pytest.raises(AuthError):
        verifier.verify(make_token(**overrides))


def test_a_token_signed_by_another_key_is_rejected(verifier):
    with pytest.raises(AuthError):
        verifier.verify(make_token(key=OTHER_KEY))


def test_a_few_seconds_of_clock_skew_is_tolerated(verifier):
    assert verifier.verify(make_token(exp=int(time.time()) - 3)).id == "user-123"


def test_alg_none_is_rejected_before_any_key_lookup():
    calls = []
    v = TokenVerifier(BASE, key_resolver=lambda t: calls.append(t))
    unsigned = jwt.encode({"sub": "x", "iss": ORIGIN, "aud": ORIGIN, "exp": int(time.time()) + 900}, None, algorithm="none")
    with pytest.raises(AuthError, match="unsupported"):
        v.verify(unsigned)
    assert calls == []


def test_an_hmac_token_is_rejected_the_downgrade_attack():
    calls = []
    v = TokenVerifier(BASE, key_resolver=lambda t: calls.append(t))
    hs = jwt.encode({"sub": "x", "iss": ORIGIN, "aud": ORIGIN, "exp": int(time.time()) + 900}, "a-shared-secret-of-32-or-more-bytes!!", algorithm="HS256")
    with pytest.raises(AuthError, match="unsupported"):
        v.verify(hs)
    assert calls == []


@pytest.mark.parametrize("junk", ["", "abc", "a.b.c", "Bearer x"])
def test_malformed_tokens_are_rejected(verifier, junk):
    with pytest.raises(AuthError):
        verifier.verify(junk)


def test_an_unreachable_key_service_is_reported_as_unavailable_not_as_a_bad_login():
    def resolver(token):
        raise jwt.PyJWKClientConnectionError("network down")

    with pytest.raises(AuthUnavailable):
        TokenVerifier(BASE, key_resolver=resolver).verify(make_token())


def test_an_unknown_key_id_is_a_bad_login():
    def resolver(token):
        raise jwt.PyJWKClientError("Unable to find a signing key that matches")

    with pytest.raises(AuthError):
        TokenVerifier(BASE, key_resolver=resolver).verify(make_token())


# --- admin -----------------------------------------------------------------------------------


def _user(**kw):
    return AuthUser(**{"id": "u", "email": "boss@example.com", "email_verified": True, "name": None, **kw})


def test_admin_needs_a_listed_and_verified_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "Boss@Example.com, other@example.com")
    assert _user().is_admin is True                                # case-insensitive match
    assert _user(email_verified=False).is_admin is False           # an unverified email proves nothing
    assert _user(email="stranger@example.com").is_admin is False
    assert _user(email=None).is_admin is False


def test_nobody_is_admin_when_no_admins_are_configured(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    assert _user().is_admin is False


def test_the_shared_verifier_follows_the_environment(monkeypatch):
    auth.set_verifier(None)
    monkeypatch.delenv("NEON_AUTH_BASE_URL", raising=False)
    assert auth.get_verifier() is None and auth.auth_configured() is False
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE + "/")
    v = auth.get_verifier()
    assert v is not None and v.base_url == BASE and auth.auth_configured() is True
    auth.set_verifier(None)
