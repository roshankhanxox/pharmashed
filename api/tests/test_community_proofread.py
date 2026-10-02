"""Note proofreading: output validation, deterministic flags, rate limit, and the route (fake model, no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pharmashed_api.assistant import loop
from pharmashed_api.assistant.limits import limiter
from pharmashed_api.community import auth, proofread
from pharmashed_api.community.auth import TokenVerifier
from pharmashed_api.main import app

from .test_community_auth import BASE, KEY, make_token
from .test_community_reports import body


class FakeClient:
    """Stands in for the OpenAI client; `reply` is the raw text the model returns."""

    def __init__(self, reply: str):
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.reply = reply

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))])


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.delenv("ASSISTANT_PROVIDER", raising=False)
    holder = {}

    def install(reply):
        holder["c"] = FakeClient(reply)
        monkeypatch.setattr(loop, "_client", lambda prov: holder["c"])
        return holder["c"]

    limiter.reset()
    return install


def test_flags_found_by_plain_rules():
    assert proofread.deterministic_flags("call me on 06 12 34 56 78") == ["personal_info"]
    assert proofread.deterministic_flags("mail pat@example.org") == ["personal_info"]
    assert proofread.deterministic_flags("follow @riverpat") == ["personal_info"]
    assert proofread.deterministic_flags("The water was 3 degrees warmer, about 20 cm deep") == []


def test_a_good_reply_is_used(fake):
    c = fake(json.dumps({"clean": "The water was calm.", "flags": ["off_topic"]}))
    out = proofread.proofread("the watr was calm")
    assert out == {"original": "the watr was calm", "clean": "The water was calm.", "changed": True, "flags": ["off_topic"]}
    assert "<note>the watr was calm</note>" in c.calls[0]["messages"][1]["content"]


@pytest.mark.parametrize("reply", ["not json", "{}", '{"clean": 5, "flags": 1}', json.dumps({"clean": "see http://x.test"}),
                                   json.dumps({"clean": "x" * 600})])
def test_an_unusable_reply_falls_back_to_the_original(fake, reply):
    fake(reply)
    out = proofread.proofread("calm water")
    assert out["clean"] == "calm water" and out["changed"] is False


def test_unknown_flags_are_dropped_and_rule_flags_are_added(fake):
    fake(json.dumps({"clean": "Call 06 12 34 56 78.", "flags": ["made_up"]}))
    assert proofread.proofread("call 06 12 34 56 78")["flags"] == ["personal_info"]


def test_empty_note_needs_no_model(fake):
    c = fake("unused")
    assert proofread.proofread("  ")["clean"] == "" and c.calls == []


def test_no_provider_raises(monkeypatch):
    for k in ("OPENAI_API_KEY", "GROQ_API_KEY", "ASSISTANT_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError):
        proofread.proofread("calm water")


@pytest.fixture
def client(community_db, monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key()))
    yield TestClient(app)
    auth.set_verifier(None)


def bearer(sub="p-user"):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_route_needs_sign_in_and_works(client, fake):
    fake(json.dumps({"clean": "Calm water.", "flags": []}))
    assert client.post("/api/ai/proofread", json={"note": "calm watr"}).status_code == 401
    r = client.post("/api/ai/proofread", json={"note": "calm watr"}, headers=bearer())
    assert r.status_code == 200 and r.json()["clean"] == "Calm water."


def test_route_is_rate_limited_per_person(client, fake, monkeypatch):
    monkeypatch.setenv("ASSISTANT_IP_LIMIT", "2")
    fake(json.dumps({"clean": "ok", "flags": []}))
    codes = [client.post("/api/ai/proofread", json={"note": "ok"}, headers=bearer("a")).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert client.post("/api/ai/proofread", json={"note": "ok"}, headers=bearer("b")).status_code == 200


def test_route_when_the_model_fails_or_is_missing(client, fake, monkeypatch):
    c = fake("x")
    c._create = lambda **k: (_ for _ in ()).throw(RuntimeError("boom"))
    c.chat.completions.create = c._create
    assert client.post("/api/ai/proofread", json={"note": "a note"}, headers=bearer()).status_code == 502
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert client.post("/api/ai/proofread", json={"note": "a note"}, headers=bearer()).status_code == 503


def test_report_keeps_both_notes_and_holds_personal_details_for_review(client):
    client.put("/api/me/profile", json={"nickname": "Note-Taker"}, headers=bearer("n1"))
    ok = client.post("/api/reports", json=body(note="calm watr", note_clean="Calm water."), headers=bearer("n1")).json()
    assert ok["note"] == "Calm water."                       # the confirmed tidy version is what is shown
    held = client.post("/api/reports", json=body(note="ring me 06 12 34 56 78"), headers=bearer("n1"))
    assert held.status_code == 201
    mine = {r["id"]: r for r in client.get("/api/me/reports", headers=bearer("n1")).json()}
    assert mine[held.json()["id"]]["status"] == "pending"
    public = [r["id"] for r in client.get("/api/reports?limit=500").json()]
    assert held.json()["id"] not in public and ok["id"] in public
