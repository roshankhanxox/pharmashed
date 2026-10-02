"""The community routes end to end: real Postgres, real token verification with a fixed key."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pharmashed_api.community import auth
from pharmashed_api.community.auth import TokenVerifier
from pharmashed_api.main import app

from .test_community_auth import BASE, KEY, make_token


@pytest.fixture
def client(community_db, monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key()))
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    yield TestClient(app)
    auth.set_verifier(None)


def bearer(**claims) -> dict:
    return {"Authorization": f"Bearer {make_token(**claims)}"}


def test_status_when_nothing_is_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("NEON_AUTH_BASE_URL", raising=False)
    auth.set_verifier(None)
    assert TestClient(app).get("/api/community/status").json() == {"enabled": False, "database": False, "auth": False, "photos": False}


def test_status_when_both_are_configured(client):
    assert client.get("/api/community/status").json() == {"enabled": True, "database": True, "auth": True, "photos": False}


def test_status_when_only_the_database_is_configured(community_db, monkeypatch):
    monkeypatch.delenv("NEON_AUTH_BASE_URL", raising=False)
    auth.set_verifier(None)
    assert TestClient(app).get("/api/community/status").json() == {"enabled": False, "database": True, "auth": False, "photos": False}


def test_me_needs_a_valid_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    expired = client.get("/api/me", headers=bearer(exp=1))
    assert expired.status_code == 401 and "sign in again" in expired.json()["detail"].lower()


def test_me_before_choosing_a_nickname(client):
    body = client.get("/api/me", headers=bearer()).json()
    assert body == {"user": {"name": "Pat Person"}, "profile": None, "is_admin": False}


def test_choosing_a_nickname_then_reading_it_back(client):
    put = client.put("/api/me/profile", headers=bearer(), json={"nickname": "RiverPat", "home_city": "GNT"})
    assert put.status_code == 200 and put.json()["nickname"] == "RiverPat"
    got = client.get("/api/me", headers=bearer()).json()["profile"]
    assert got["nickname"] == "RiverPat" and got["home_city"] == "GNT" and got["show_on_leaderboard"] is True
    again = client.put("/api/me/profile", headers=bearer(), json={"nickname": "RiverPat", "show_on_leaderboard": False})
    assert again.status_code == 200 and again.json()["show_on_leaderboard"] is False


def test_two_people_cannot_share_a_nickname_even_in_a_different_case(client):
    assert client.put("/api/me/profile", headers=bearer(sub="a", id="a"), json={"nickname": "StreamFan"}).status_code == 200
    clash = client.put("/api/me/profile", headers=bearer(sub="b", id="b"), json={"nickname": "streamfan"})
    assert clash.status_code == 409 and "taken" in clash.json()["detail"]
    assert client.get("/api/me", headers=bearer(sub="b", id="b")).json()["profile"] is None


@pytest.mark.parametrize("payload, fragment", [
    ({"nickname": "ab"}, "3 to 20"),
    ({"nickname": "admin"}, "reserved"),
    ({"nickname": "has space"}, "only letters"),
    ({"nickname": "GoodName", "home_city": "PAR"}, "Home city"),
])
def test_invalid_profiles_are_refused_with_a_readable_message(client, payload, fragment):
    r = client.put("/api/me/profile", headers=bearer(), json=payload)
    assert r.status_code == 422 and fragment in str(r.json()["detail"])


def test_writing_a_profile_needs_a_token(client):
    assert client.put("/api/me/profile", json={"nickname": "Nope"}).status_code == 401


def test_admin_is_reported_only_for_a_listed_verified_email(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
    assert client.get("/api/me", headers=bearer(email="boss@example.com")).json()["is_admin"] is True
    assert client.get("/api/me", headers=bearer(email="boss@example.com", emailVerified=False)).json()["is_admin"] is False
    assert client.get("/api/me", headers=bearer(email="someone@example.com")).json()["is_admin"] is False


def test_without_a_database_the_community_routes_say_so_and_the_rest_of_the_api_still_works(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda t: KEY.public_key()))
    c = TestClient(app)
    r = c.get("/api/me", headers=bearer())
    assert r.status_code == 503 and "no database" in r.json()["detail"]
    assert c.get("/api/health").status_code == 200
    auth.set_verifier(None)


def test_cors_allows_put_and_the_authorization_header(client):
    r = client.options("/api/me/profile", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert r.status_code == 200
    assert "PUT" in r.headers["access-control-allow-methods"]
    assert "authorization" in r.headers["access-control-allow-headers"].lower()
