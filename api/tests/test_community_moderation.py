"""Flags, the moderator queue, deleting an account, orphan photos and the FHIR export (real Postgres, fake bucket)."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from pharmashed_api.community import accounts, auth, db, moderation, photos, storage
from pharmashed_api.community.auth import TokenVerifier
from pharmashed_api.main import app

from .test_community_auth import BASE, KEY, make_token
from .test_community_photos import FakeBucket, image_bytes, model  # noqa: F401 - fixtures
from .test_community_reports import body

ADMIN = "boss@example.com"


@pytest.fixture
def client(community_db, monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    monkeypatch.setenv("ADMIN_EMAILS", ADMIN)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key()))
    yield TestClient(app)
    auth.set_verifier(None)


def bearer(sub, **claims):
    return {"Authorization": f"Bearer {make_token(sub=sub, **claims)}"}


def admin():
    return bearer("admin-1", email=ADMIN)


def person(client, sub, nick):
    client.put("/api/me/profile", json={"nickname": nick}, headers=bearer(sub))


def file_report(client, sub="author", **over):
    r = client.post("/api/reports", json=body(**over), headers=bearer(sub))
    assert r.status_code == 201, r.text
    return r.json()


def public_ids(client):
    return [r["id"] for r in client.get("/api/reports?limit=500").json()]


# -- flags ---------------------------------------------------------------------------------------------

def test_flag_rules(client):
    person(client, "author", "Author-A")
    rep = file_report(client)
    url = f"/api/reports/{rep['id']}/flag"
    assert client.post(url, json={"reason": "spam"}).status_code == 401
    assert client.post(url, json={"reason": "bogus"}, headers=bearer("f1")).status_code == 422
    assert client.post(url, json={"reason": "spam"}, headers=bearer("author")).status_code == 422      # own report
    assert client.post(f"/api/reports/{uuid.uuid4()}/flag", json={"reason": "spam"}, headers=bearer("f1")).status_code == 404
    sample = client.get("/api/reports?limit=500").json()[-1]
    assert sample["is_sample"] and client.post(f"/api/reports/{sample['id']}/flag", json={"reason": "spam"}, headers=bearer("f1")).status_code == 404
    first = client.post(url, json={"reason": "spam"}, headers=bearer("f1")).json()
    again = client.post(url, json={"reason": "inaccurate"}, headers=bearer("f1")).json()
    assert first == {"flagged": True, "held": False} and again == {"flagged": False, "held": False}
    assert client.get("/api/flag-reasons").json()["spam"]


def test_three_different_people_hold_a_report_for_review(client):
    person(client, "author", "Author-A")
    rep = file_report(client)
    url = f"/api/reports/{rep['id']}/flag"
    assert client.post(url, json={"reason": "spam"}, headers=bearer("f1")).json()["held"] is False
    assert client.post(url, json={"reason": "spam"}, headers=bearer("f2")).json()["held"] is False
    assert rep["id"] in public_ids(client)
    assert client.post(url, json={"reason": "spam"}, headers=bearer("f3")).json()["held"] is True
    assert rep["id"] not in public_ids(client)
    assert client.post(url, json={"reason": "spam"}, headers=bearer("f4")).status_code == 404       # no longer public


def test_daily_flag_limit(client, monkeypatch):
    monkeypatch.setattr(moderation, "MAX_FLAGS_PER_DAY", 2)
    person(client, "author", "Author-A")
    ids = [file_report(client)["id"] for _ in range(3)]
    codes = [client.post(f"/api/reports/{i}/flag", json={"reason": "spam"}, headers=bearer("f1")).status_code for i in ids]
    assert codes == [200, 200, 429]


# -- moderators kept in the database ---------------------------------------------------------------------

def test_a_row_in_the_moderators_table_makes_a_moderator_without_any_setting(client, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    h = bearer("db-mod", email="anyone@example.com", emailVerified=False)       # not listed anywhere, not verified
    assert client.get("/api/admin/reports", headers=h).status_code == 403
    assert client.get("/api/me", headers=h).json()["is_admin"] is False
    with db.connection() as c:
        c.execute("insert into moderators (user_id, note) values ('db-mod', 'test')")
    assert client.get("/api/admin/reports", headers=h).status_code == 200
    assert client.get("/api/me", headers=h).json()["is_admin"] is True
    assert client.get("/api/admin/reports", headers=bearer("someone-else")).status_code == 403   # only that person


def test_both_routes_work_and_removing_the_row_removes_the_power(client):
    assert client.get("/api/me", headers=admin()).json()["is_admin"] is True                    # the ADMIN_EMAILS route
    with db.connection() as c:
        c.execute("insert into moderators (user_id) values ('db-mod')")
    assert client.get("/api/admin/reports", headers=bearer("db-mod")).status_code == 200
    with db.connection() as c:
        c.execute("delete from moderators where user_id = 'db-mod'")
    assert client.get("/api/admin/reports", headers=bearer("db-mod")).status_code == 403


def test_deleting_an_account_removes_its_moderator_row(client):
    with db.connection() as c:
        c.execute("insert into moderators (user_id) values ('db-mod')")
        accounts.delete_account(c, "db-mod")
        assert c.execute("select count(*) as n from moderators").fetchone()["n"] == 0


# -- the queue and decisions ----------------------------------------------------------------------------

def test_queue_is_for_moderators_only(client):
    assert client.get("/api/admin/reports").status_code == 401
    assert client.get("/api/admin/reports", headers=bearer("x")).status_code == 403
    assert client.get("/api/admin/reports", headers=bearer("admin-1", email=ADMIN, emailVerified=False)).status_code == 403
    assert client.get("/api/admin/reports", headers=admin()).json() == []
    rid = str(uuid.uuid4())
    assert client.post(f"/api/admin/reports/{rid}/approve", json={}, headers=bearer("x")).status_code == 403


def test_held_report_in_queue_then_approved_and_scored(client):
    person(client, "author", "Author-A")
    held = file_report(client, note="ring me on 06 12 34 56 78")
    assert held["rewards"] is None and held["id"] not in public_ids(client)
    q = client.get("/api/admin/reports", headers=admin()).json()
    assert [i["id"] for i in q] == [held["id"]]
    assert q[0]["why"] == ["The note may contain personal details"] and q[0]["nickname"] == "Author-A"
    assert q[0]["note_raw"] == "ring me on 06 12 34 56 78"

    done = client.post(f"/api/admin/reports/{held['id']}/approve", json={"note": "fine"}, headers=admin()).json()
    assert done["status"] == "approved" and done["rewards"]["total"] >= 15
    assert held["id"] in public_ids(client) and client.get("/api/admin/reports", headers=admin()).json() == []
    again = client.post(f"/api/admin/reports/{held['id']}/approve", json={}, headers=admin()).json()
    assert again["rewards"]["total"] == 0                                        # never scored twice
    with db.connection() as c:
        assert c.execute("select count(*) as n from moderation_actions where action = 'approve'").fetchone()["n"] == 2


def test_flagged_public_report_is_queued_and_hide_reverses_points(client):
    person(client, "author", "Author-A")
    rep = file_report(client)
    pts = client.get("/api/me/progress", headers=bearer("author")).json()["points"]
    assert pts >= 15
    client.post(f"/api/reports/{rep['id']}/flag", json={"reason": "inaccurate"}, headers=bearer("f1"))
    q = client.get("/api/admin/reports", headers=admin()).json()
    assert q[0]["id"] == rep["id"] and q[0]["why"] == ["Flagged by 1 person"] and q[0]["flags"][0]["label"]
    hidden = client.post(f"/api/admin/reports/{rep['id']}/hide", json={"note": "not true"}, headers=admin()).json()
    assert hidden == {"status": "hidden", "points_removed": pts}
    assert rep["id"] not in public_ids(client)
    assert client.get("/api/me/progress", headers=bearer("author")).json()["points"] == 0
    assert client.get("/api/me/reports", headers=bearer("author")).json()[0]["status"] == "hidden"
    assert client.get("/api/admin/reports", headers=admin()).json() == []
    assert client.post(f"/api/admin/reports/{rep['id']}/approve", json={}, headers=admin()).status_code == 422
    assert client.post(f"/api/admin/reports/{rep['id']}/hide", json={"note": "x" * 301}, headers=admin()).status_code == 422
    with db.connection() as c:
        assert c.execute("select count(*) as n from report_flags where resolved_at is not null").fetchone()["n"] == 1


def test_hiding_deletes_the_photo_and_a_photo_flag_explains_the_hold(client, monkeypatch, model):
    bucket = FakeBucket().install(monkeypatch)
    deleted = []
    monkeypatch.setattr(storage, "delete", lambda key: deleted.append(key) or bucket.objects.pop(key, None))
    model(json.dumps({"is_stream": True, "people": True, "plate": False}))
    person(client, "author", "Author-A")
    up = client.post("/api/photos", files={"file": ("p.png", image_bytes(), "image/png")}, headers=bearer("author")).json()
    rep = file_report(client, photo_id=up["id"])
    q = client.get("/api/admin/reports", headers=admin()).json()[0]
    assert q["why"] == ["The photo check flagged it: people"] and q["photo_preview"].startswith("https://s3.test/")
    client.post(f"/api/admin/reports/{rep['id']}/hide", json={}, headers=admin())
    assert deleted == [f"photos/{up['id']}.jpg"] and bucket.objects == {}
    with db.connection() as c:
        assert c.execute("select count(*) as n from report_photos").fetchone()["n"] == 0


# -- orphan photos -----------------------------------------------------------------------------------------

def test_abandoned_uploads_are_swept_on_the_next_upload(client, monkeypatch, model):
    bucket = FakeBucket().install(monkeypatch)
    monkeypatch.setattr(storage, "delete", lambda key: bucket.objects.pop(key, None))
    model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    person(client, "author", "Author-A")
    old = client.post("/api/photos", files={"file": ("p.png", image_bytes(), "image/png")}, headers=bearer("author")).json()["id"]
    kept = client.post("/api/photos", files={"file": ("p.png", image_bytes(), "image/png")}, headers=bearer("author")).json()["id"]
    file_report(client, photo_id=kept)
    with db.connection() as c:
        c.execute("update report_photos set created_at = now() - interval '2 days' where id = %s", (old,))
    client.post("/api/photos", files={"file": ("p.png", image_bytes(), "image/png")}, headers=bearer("author"))
    assert f"photos/{old}.jpg" not in bucket.objects and f"photos/{kept}.jpg" in bucket.objects   # attached photo is safe


# -- delete my account -------------------------------------------------------------------------------------

@pytest.fixture
def neon_auth_stub(community_db):
    """The tables Neon Auth creates in the real database, reduced to what deletion touches."""
    db.reset_pool()
    with db.connection() as c:
        c.execute('create schema neon_auth; create table neon_auth."user" (id uuid primary key, email text);'
                  ' create table neon_auth.session ("userId" uuid); create table neon_auth.account ("userId" uuid);'
                  " create table neon_auth.verification (identifier text)")
    yield


def test_delete_my_account_removes_everything_and_only_theirs(client, neon_auth_stub, monkeypatch, model):
    bucket = FakeBucket().install(monkeypatch)
    monkeypatch.setattr(storage, "delete", lambda key: bucket.objects.pop(key, None))
    model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    me, other = str(uuid.uuid4()), str(uuid.uuid4())
    with db.connection() as c:
        for uid, mail in ((me, "me@example.com"), (other, "other@example.com")):
            c.execute('insert into neon_auth."user" values (%s, %s)', (uid, mail))
            c.execute('insert into neon_auth.session values (%s)', (uid,))
            c.execute('insert into neon_auth.account values (%s)', (uid,))
        c.execute("insert into neon_auth.verification values ('me@example.com')")
    person(client, me, "Leaving-Lee")
    person(client, other, "Staying-Sam")
    up = client.post("/api/photos", files={"file": ("p.png", image_bytes(), "image/png")}, headers=bearer(me)).json()
    mine = file_report(client, me, photo_id=up["id"])
    theirs = file_report(client, other)
    client.post(f"/api/reports/{theirs['id']}/flag", json={"reason": "spam"}, headers=bearer(me))      # a flag I raised
    assert bucket.objects

    assert client.delete("/api/me").status_code == 401
    out = client.delete("/api/me", headers=bearer(me)).json()
    assert out == {"photos": 1, "reports": 1, "sign_in_user": 1}
    assert bucket.objects == {}
    with db.connection() as c:
        left = lambda sql, *a: c.execute(sql, a).fetchone()["n"]  # noqa: E731
        assert left("select count(*) as n from reports where user_id = %s", me) == 0
        assert left("select count(*) as n from profiles where user_id = %s", me) == 0
        assert left("select count(*) as n from points_events where user_id = %s", me) == 0
        assert left("select count(*) as n from badges_awarded where user_id = %s", me) == 0
        assert left("select count(*) as n from report_flags") == 0
        assert left('select count(*) as n from neon_auth."user" where id = %s', uuid.UUID(me)) == 0
        assert left("select count(*) as n from neon_auth.verification") == 0
        assert left("select count(*) as n from profiles where user_id = %s", other) == 1             # others untouched
        assert left("select count(*) as n from neon_auth.session") == 1
    assert theirs["id"] in public_ids(client) and mine["id"] not in public_ids(client)


def test_delete_works_without_the_sign_in_tables(client):
    person(client, "plain-id", "Plain-Pat")
    assert client.delete("/api/me", headers=bearer("plain-id")).json() == {"photos": 0, "reports": 0, "sign_in_user": 0}


def test_delete_account_function_ignores_non_uuid_ids(community_db):
    with db.connection() as c:
        assert accounts.delete_account(c, "not-a-uuid") == {"photos": 0, "reports": 0, "sign_in_user": 0}


# -- FHIR export --------------------------------------------------------------------------------------------

def test_fhir_export_is_anonymous_unverified_and_only_for_public_reports(client):
    person(client, "author", "Secret-Nick")
    shown = file_report(client, note="secret note text")
    held = file_report(client, note="ring me 06 12 34 56 78")
    outside = client.post("/api/reports", json=body(lat=0.0, lon=0.0), headers=bearer("author")).json()
    r = client.get("/api/fhir/citizen-observations")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/fhir+json")
    bundle = r.json()
    assert bundle["resourceType"] == "Bundle" and bundle["entry"][0]["resource"]["resourceType"] == "Organization"
    ids = {e["resource"]["id"] for e in bundle["entry"][1:]}
    assert f"cit-{shown['id']}" in ids and f"cit-{held['id']}" not in ids and f"cit-{outside['id']}" not in ids
    text = json.dumps(bundle)
    assert "Secret-Nick" not in text and "secret note text" not in text and "author" not in text
    obs = next(e["resource"] for e in bundle["entry"] if e["resource"]["id"] == f"cit-{shown['id']}")
    assert obs["status"] == "preliminary" and obs["subject"]["reference"].startswith("Location/site-")
    samples = [e for e in bundle["entry"][1:] if any(t["code"] == "sample" for t in e["resource"]["meta"]["tag"])]
    assert len(samples) == 20
