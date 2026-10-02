"""Points: every rule, the caps, reversals, badges, the challenge and the leaderboard. Real Postgres, fixed clock."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from pharmashed_api.community import db, points

# Monday 2026-06-01 12:00 UTC is in ISO week 23.
MON = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
FULL = {"water_colour": "clear", "smell": "none", "foam": "none", "litter": "none", "flow": "normal"}


@pytest.fixture
def conn(pg_url):
    with psycopg.connect(pg_url, row_factory=dict_row, autocommit=True) as c:
        db.apply_migrations(c)
        for t in ("points_events", "badges_awarded", "report_photos", "reports", "profiles"):
            c.execute(f"delete from {t}")
        yield c


def profile(conn, uid, nick, show=True):
    conn.execute("insert into profiles (user_id, nickname, show_on_leaderboard) values (%s, %s, %s)", (uid, nick, show))


def report(conn, uid="u1", site="TLS-01", at=MON, status="approved", sample=False, checklist=None, photo_ok=None, city="TLS"):
    row = conn.execute(
        "insert into reports (user_id, is_sample, lat, lon, site_id, city, observed_at, checklist, status, created_at)"
        " values (%s, %s, 43, 1, %s, %s, %s, %s, %s, %s) returning id",
        (uid, sample, site, city if site else None, at, Jsonb(checklist or {"foam": "none"}), status, at),
    ).fetchone()
    if photo_ok is not None:
        conn.execute(
            "insert into report_photos (user_id, report_id, object_key, width, height, bytes, ai_ok) values (%s, %s, 'k', 1, 1, 1, %s)",
            (uid, row["id"], photo_ok),
        )
    return row["id"]


def award(conn, rid):
    return points.award_for_report(conn, rid)


def reasons(res):
    return {line["reason"]: line["points"] for line in res["lines"]}


def total(conn, uid="u1"):
    return conn.execute("select coalesce(sum(points),0) as n from points_events where user_id = %s", (uid,)).fetchone()["n"]


# -- the basic rules -----------------------------------------------------------------------------------

def test_first_report_at_a_neglected_site(conn):
    res = award(conn, report(conn))
    assert reasons(res) == {"report": 10, "first_at_site": 5, "neglected_site": 10} and res["total"] == 25
    assert res["new_badges"] == [{"key": "first_report", "title": "First report"}]


def test_a_checked_photo_adds_five(conn):
    assert reasons(award(conn, report(conn, photo_ok=True)))["photo"] == 5
    assert "photo" not in reasons(award(conn, report(conn, site="TLS-02", photo_ok=False)))
    assert "photo" not in reasons(award(conn, report(conn, site="TLS-03", photo_ok=None)))


def test_scoring_is_idempotent(conn):
    rid = report(conn)
    assert award(conn, rid)["total"] == 25
    assert award(conn, rid)["total"] == 0 and total(conn) == 25


def test_samples_pending_and_hidden_reports_earn_nothing(conn):
    for kw in ({"sample": True}, {"status": "pending"}, {"status": "hidden"}):
        assert award(conn, report(conn, **kw)) == {"lines": [], "total": 0, "new_badges": []}
    assert total(conn) == 0


def test_a_report_outside_coverage_earns_nothing_and_says_why(conn):
    res = award(conn, report(conn, site=None))
    assert reasons(res) == {"no_points:outside_coverage": 0}
    assert "Not near one of our sites" in res["lines"][0]["label"]


def test_neglected_bonus_only_when_nobody_reported_in_30_days(conn):
    award(conn, report(conn, "other", "TLS-01", MON - timedelta(days=10)))      # someone else, 10 days earlier
    res = award(conn, report(conn, "u1", "TLS-01", MON))
    assert "neglected_site" not in reasons(res) and "first_at_site" in reasons(res)
    old = award(conn, report(conn, "u3", "TLS-05", MON - timedelta(days=40)))
    later = award(conn, report(conn, "u1", "TLS-05", MON))
    assert "neglected_site" in reasons(later) and "neglected_site" in reasons(old)


def test_samples_do_not_count_as_recent_reports(conn):
    report(conn, "sample", "TLS-01", MON - timedelta(days=2), sample=True)
    assert "neglected_site" in reasons(award(conn, report(conn)))


# -- caps ----------------------------------------------------------------------------------------------

def test_site_cooldown_is_seven_days_per_person(conn):
    award(conn, report(conn, at=MON))
    blocked = award(conn, report(conn, at=MON + timedelta(days=3)))
    assert reasons(blocked) == {"no_points:site_cooldown": 0}
    assert "report" in reasons(award(conn, report(conn, at=MON + timedelta(days=9))))
    assert "report" in reasons(award(conn, report(conn, "u2", at=MON + timedelta(days=3))))     # someone else is fine


def test_three_rewarded_reports_a_day(conn):
    got = [reasons(award(conn, report(conn, site=f"TLS-0{i}", at=MON + timedelta(minutes=i)))) for i in range(1, 5)]
    assert ["report" in g for g in got] == [True, True, True, False]
    assert got[3] == {"no_points:daily_cap": 0}
    assert "report" in reasons(award(conn, report(conn, site="TLS-09", at=MON + timedelta(days=1))))   # next day is fresh


# -- streaks and the weekly challenge ------------------------------------------------------------------

def test_weekly_streak_bonus_grows_and_caps(conn):
    bonuses = []
    for w in range(7):
        res = award(conn, report(conn, site=f"TLS-{w + 1:02d}", at=MON + timedelta(weeks=w)))
        bonuses.append(reasons(res).get("streak", 0))
    assert bonuses == [0, 5, 10, 15, 20, 20, 20]


def test_a_missed_week_resets_the_streak(conn):
    award(conn, report(conn, site="TLS-01", at=MON))
    award(conn, report(conn, site="TLS-02", at=MON + timedelta(weeks=1)))
    res = award(conn, report(conn, site="TLS-03", at=MON + timedelta(weeks=3)))
    assert "streak" not in reasons(res)


def test_streak_bonus_once_per_week(conn):
    award(conn, report(conn, site="TLS-01", at=MON))
    first = award(conn, report(conn, site="TLS-02", at=MON + timedelta(weeks=1)))
    second = award(conn, report(conn, site="TLS-03", at=MON + timedelta(weeks=1, hours=1)))
    assert reasons(first)["streak"] == 5 and "streak" not in reasons(second)


def test_challenge_is_deterministic_by_iso_week(conn):
    assert points.challenge_for(MON)["key"] == points.CHALLENGES[23 % 4][0]
    assert points.challenge_for(MON)["week"] == "2026-W23"
    assert points.challenge_for(MON + timedelta(days=6))["key"] == points.challenge_for(MON)["key"]
    assert points.challenge_for(MON + timedelta(days=7))["key"] != points.challenge_for(MON)["key"]


def test_challenge_awards_twenty_once_a_week(conn):
    wk = next(MON + timedelta(weeks=i) for i in range(4) if points.challenge_for(MON + timedelta(weeks=i))["key"] == "detailed")
    first = award(conn, report(conn, site="TLS-01", at=wk, checklist=FULL))
    assert reasons(first)["challenge"] == 20
    second = award(conn, report(conn, site="TLS-02", at=wk + timedelta(hours=1), checklist=FULL))
    assert "challenge" not in reasons(second)
    assert {r["badge"] for r in conn.execute("select badge from badges_awarded")} >= {"first_report", "challenger"}


# -- reversal and badges -------------------------------------------------------------------------------

def test_reversal_cancels_points_and_takes_the_badge_back(conn):
    rid = report(conn)
    award(conn, rid)
    assert total(conn) == 25
    assert points.reverse_for_report(conn, rid) == 25
    assert total(conn) == 0
    assert points.reverse_for_report(conn, rid) == 0                       # second call does nothing
    assert conn.execute("select count(*) as n from badges_awarded").fetchone()["n"] == 0
    assert conn.execute("select count(*) as n from points_events where points < 0").fetchone()["n"] == 3


def test_reversed_report_no_longer_counts_toward_caps(conn):
    ids = [report(conn, site=f"TLS-0{i}", at=MON + timedelta(minutes=i)) for i in range(1, 4)]
    for i in ids:
        award(conn, i)
    points.reverse_for_report(conn, ids[0])
    assert "report" in reasons(award(conn, report(conn, site="TLS-09", at=MON + timedelta(minutes=9))))


def test_badges_from_counts(conn):
    for i in range(5):
        award(conn, report(conn, site=f"TLS-0{i + 1}", at=MON + timedelta(weeks=i), photo_ok=True))
    have = {r["badge"] for r in conn.execute("select badge from badges_awarded where user_id = 'u1'")}
    assert have == {"first_report", "regular", "explorer", "photographer", "streak_3", "neglected_hero"} | (have & {"challenger"})


# -- progress and leaderboard --------------------------------------------------------------------------

def test_progress_summary(conn):
    profile(conn, "u1", "Pat")
    award(conn, report(conn, photo_ok=True))
    p = points.progress(conn, "u1", now=MON + timedelta(days=1))
    assert p["points"] == 30 and p["points_this_week"] == 30 and p["rank"] == 1 and p["streak_weeks"] == 1
    assert [b["key"] for b in p["badges"] if b["earned"]] == ["first_report"]
    assert len(p["badges"]) == len(points.BADGES) and p["challenge"]["week"] == "2026-W23"
    assert p["recent"][0]["label"] and {e["reason"] for e in p["recent"]} >= {"report", "photo"}


def test_leaderboard_ranks_hides_and_filters(conn):
    for uid, nick, show in (("a", "Alpha", True), ("b", "Bravo", True), ("c", "Hidden-C", False), ("d", "Delta", True)):
        profile(conn, uid, nick, show)
    award(conn, report(conn, "a", "TLS-01", MON, city="TLS"))                                 # 25
    award(conn, report(conn, "a", "TLS-02", MON + timedelta(hours=1), city="TLS"))            # +25 = 50
    award(conn, report(conn, "b", "OSL-01", MON, city="OSL"))                                 # 25
    award(conn, report(conn, "c", "OSL-02", MON, city="OSL"))                                 # 25, hidden
    award(conn, report(conn, "d", "OSL-03", MON - timedelta(days=60), city="OSL"))            # old: 25, +20 challenge (that week's)
    board = points.leaderboard(conn, "b", now=MON + timedelta(days=1))
    assert [(e["nickname"], e["points"], e["rank"]) for e in board["entries"]] == [
        ("Alpha", 50, 1), ("Delta", 45, 2), ("Bravo", 25, 3)]                                 # hidden person omitted
    assert [e["is_me"] for e in board["entries"]] == [False, False, True]
    assert board["me"] == {"rank": 3, "points": 25, "listed": True}
    week = points.leaderboard(conn, None, scope="week", now=MON + timedelta(days=1))
    assert [e["nickname"] for e in week["entries"]] == ["Alpha", "Bravo"] and week["me"] is None
    osl = points.leaderboard(conn, "c", city="OSL", now=MON + timedelta(days=1))
    assert [e["nickname"] for e in osl["entries"]] == ["Delta", "Bravo"]
    assert osl["me"] == {"rank": 2, "points": 25, "listed": False}   # tied with Bravo; hidden people still see their own rank


def test_leaderboard_never_shows_user_ids_or_zero_point_people(conn):
    profile(conn, "z", "Zero")
    award(conn, report(conn, "z", site=None))
    board = points.leaderboard(conn, None)
    assert board["entries"] == [] and "user_id" not in str(board)


# -- through the API -----------------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402

from pharmashed_api.community import auth  # noqa: E402
from pharmashed_api.community.auth import TokenVerifier  # noqa: E402
from pharmashed_api.main import app  # noqa: E402

from .test_community_auth import BASE, KEY, make_token  # noqa: E402
from .test_community_reports import body  # noqa: E402


@pytest.fixture
def client(community_db, monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key()))
    yield TestClient(app)
    auth.set_verifier(None)


def bearer(sub):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_filing_a_report_returns_its_rewards_and_feeds_progress_and_board(client):
    client.put("/api/me/profile", json={"nickname": "Point-Pat"}, headers=bearer("api-1"))
    made = client.post("/api/reports", json=body(), headers=bearer("api-1")).json()
    rewards = made["rewards"]
    assert {line["reason"] for line in rewards["lines"]} >= {"report", "first_at_site"}
    assert rewards["total"] >= 15 and "first_report" in {b["key"] for b in rewards["new_badges"]}

    prog = client.get("/api/me/progress", headers=bearer("api-1")).json()
    assert prog["points"] == rewards["total"] and prog["rank"] == 1
    assert client.get("/api/me/progress").status_code == 401

    board = client.get("/api/leaderboard", headers=bearer("api-1")).json()
    assert board["entries"][0]["nickname"] == "Point-Pat" and board["entries"][0]["is_me"] is True
    assert "user_id" not in str(board)
    anon = client.get("/api/leaderboard?scope=week").json()
    assert anon["entries"][0]["is_me"] is False and anon["me"] is None


def test_a_held_report_earns_nothing_until_approved(client, community_db):
    client.put("/api/me/profile", json={"nickname": "Held-Hal"}, headers=bearer("api-2"))
    held = client.post("/api/reports", json=body(note="call me 06 12 34 56 78"), headers=bearer("api-2")).json()
    assert held["rewards"] is None
    assert client.get("/api/me/progress", headers=bearer("api-2")).json()["points"] == 0
    with db.connection() as c:
        c.execute("update reports set status = 'approved' where id = %s", (held["id"],))
        assert points.award_for_report(c, held["id"])["total"] >= 15          # what phase 5's approve button will call
    assert client.get("/api/me/progress", headers=bearer("api-2")).json()["points"] >= 15


def test_challenge_and_input_checks(client):
    assert client.get("/api/challenge").json()["key"] in {c[0] for c in points.CHALLENGES}
    assert client.get("/api/leaderboard?scope=forever").status_code == 422
    assert client.get("/api/leaderboard?city=XXX").status_code == 422
    assert client.get("/api/leaderboard?city=OSL&scope=month&limit=5").status_code == 200
