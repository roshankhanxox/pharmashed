"""Reports: the rules, the pin placement, and the routes end to end (real Postgres, fixed-key tokens)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from pharmashed_api.community import auth, geo, reports
from pharmashed_api.community.auth import TokenVerifier
from pharmashed_api.main import app

from .test_community_auth import BASE, KEY, make_token

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
GOOD = {"water_colour": "clear", "animals": ["birds", "fish"]}


# -- pure rules ------------------------------------------------------------------------------------

def test_checklist_keeps_valid_answers_and_sorts_multi():
    assert reports.clean_checklist({"animals": ["fish", "birds", "fish"], "foam": "light"}) == {
        "animals": ["birds", "fish"], "foam": "light"}


@pytest.mark.parametrize("bad", [
    {}, {"foam": ""}, {"foam": "purple"}, {"mood": "happy"}, {"animals": "fish"}, {"animals": ["dragon"]}, {"foam": ["light"]},
])
def test_checklist_rejects(bad):
    with pytest.raises(reports.InvalidReport):
        reports.clean_checklist(bad)


def test_note_rules():
    assert reports.clean_note("  fine\x00 note ") == "fine note"
    assert reports.clean_note(None) == ""
    with pytest.raises(reports.InvalidReport):
        reports.clean_note("x" * 501)
    with pytest.raises(reports.InvalidReport):
        reports.clean_note("buy at www.example.com")


def test_visit_time_window():
    assert reports.clean_observed_at(NOW - timedelta(days=3), NOW) == NOW - timedelta(days=3)
    assert reports.clean_observed_at(datetime(2026, 5, 31, 12), NOW) == datetime(2026, 5, 31, 12, tzinfo=UTC)  # naive = UTC
    with pytest.raises(reports.InvalidReport):
        reports.clean_observed_at(NOW + timedelta(hours=1), NOW)
    with pytest.raises(reports.InvalidReport):
        reports.clean_observed_at(NOW - timedelta(days=31), NOW)


SITES = [{"id": "A-01", "city": "AAA", "lonlat": [1.0, 43.0]}, {"id": "A-02", "city": "AAA", "lonlat": [1.1, 43.0]}]
CITIES = [{"id": "AAA", "center": [1.05, 43.0]}, {"id": "BBB", "center": [10.0, 50.0]}]


def test_pin_links_to_nearest_site_within_a_kilometre():
    p = geo.place_pin(43.0, 1.0005, SITES, CITIES)           # about 40 m from A-01
    assert (p.site_id, p.city) == ("A-01", "AAA") and p.distance_m < 100


def test_pin_outside_site_range_gets_the_nearest_city_or_nothing():
    near_city = geo.place_pin(43.0, 1.05, SITES, CITIES)     # between the sites, over 1 km from both
    assert (near_city.site_id, near_city.city, near_city.distance_m) == (None, "AAA", None)
    far = geo.place_pin(0.0, 0.0, SITES, CITIES)
    assert (far.site_id, far.city) == (None, None)


def test_haversine_known_distance():
    assert geo.haversine_m(0, 0, 0, 1) == pytest.approx(111_195, rel=1e-3)   # one degree of longitude at the equator


# -- database and routes -----------------------------------------------------------------------------

@pytest.fixture
def client(community_db, monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key()))
    yield TestClient(app)
    auth.set_verifier(None)


def bearer(sub="user-1", **claims) -> dict:
    return {"Authorization": f"Bearer {make_token(sub=sub, **claims)}"}


def nickname(client, sub, name):
    assert client.put("/api/me/profile", json={"nickname": name}, headers=bearer(sub)).status_code == 200


def body(**over):
    site = reports.data.sites()["sites"][0]
    lon, lat = site["lonlat"]
    return {"lat": lat, "lon": lon, "observed_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            "checklist": GOOD, "note": "Calm.", **over}


def test_samples_are_seeded_once_and_labelled(client):
    listing = client.get("/api/reports?limit=500").json()
    assert len(listing) == 20 and all(r["is_sample"] and r["author"] == "Sample report" for r in listing)
    assert {r["city"] for r in listing} == {"TLS", "GNT", "BNV", "CBR", "OSL"}
    assert "user_id" not in listing[0]


def test_reading_is_public_filtering_works(client):
    sample = client.get("/api/reports").json()[0]
    assert len(client.get(f"/api/reports?site_id={sample['site_id']}").json()) >= 1
    assert all(r["city"] == "OSL" for r in client.get("/api/reports?city=OSL").json())


def test_filing_needs_sign_in_and_a_nickname(client):
    assert client.post("/api/reports", json=body()).status_code == 401
    r = client.post("/api/reports", json=body(), headers=bearer("u-nonick"))
    assert r.status_code == 409 and "nickname" in r.json()["detail"]


def test_file_a_report_and_find_it(client):
    nickname(client, "user-1", "Pat-Rivers")
    r = client.post("/api/reports", json=body(), headers=bearer("user-1"))
    assert r.status_code == 201
    made = r.json()
    assert made["author"] == "Pat-Rivers" and made["mine"] is True and made["is_sample"] is False
    assert made["site_id"] == reports.data.sites()["sites"][0]["id"] and made["checklist"]["animals"] == ["birds", "fish"]
    assert made["note"] == "Calm."
    anyone = {x["id"]: x for x in client.get(f"/api/reports?site_id={made['site_id']}").json()}
    assert anyone[made["id"]]["mine"] is False                         # not the viewer's, anonymous
    mine = {x["id"]: x for x in client.get(f"/api/reports?site_id={made['site_id']}", headers=bearer("user-1")).json()}
    assert mine[made["id"]]["mine"] is True
    assert [x["id"] for x in client.get("/api/me/reports", headers=bearer("user-1")).json()] == [made["id"]]
    assert client.get("/api/me/reports", headers=bearer("someone-else")).json() == []


def test_bad_reports_get_422(client):
    nickname(client, "user-2", "Lee-Banks")
    h = bearer("user-2")
    assert client.post("/api/reports", json=body(checklist={}), headers=h).status_code == 422
    assert client.post("/api/reports", json=body(note="see http://spam.test"), headers=h).status_code == 422
    assert client.post("/api/reports", json=body(observed_at=(datetime.now(UTC) + timedelta(days=1)).isoformat()), headers=h).status_code == 422
    assert client.post("/api/reports", json=body(lat=95), headers=h).status_code == 422


def test_daily_limit(client):
    nickname(client, "user-3", "Sam-Creek")
    h = bearer("user-3")
    codes = [client.post("/api/reports", json=body(), headers=h).status_code for _ in range(reports.MAX_REPORTS_PER_DAY + 1)]
    assert codes == [201] * reports.MAX_REPORTS_PER_DAY + [429]


def test_hidden_reports_leave_the_public_list_but_not_the_owners(client, community_db):
    nickname(client, "user-4", "Kit-Brook")
    made = client.post("/api/reports", json=body(), headers=bearer("user-4")).json()
    from pharmashed_api.community import db
    with db.connection() as conn:
        conn.execute("update reports set status = 'hidden' where id = %s", (made["id"],))
    assert made["id"] not in [r["id"] for r in client.get("/api/reports?limit=500").json()]
    mine = client.get("/api/me/reports", headers=bearer("user-4")).json()
    assert mine[0]["status"] == "hidden"


def test_bad_token_on_a_public_read_is_just_anonymous(client):
    assert client.get("/api/reports", headers={"Authorization": "Bearer nonsense"}).status_code == 200
