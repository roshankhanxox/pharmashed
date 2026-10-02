"""Migrations and profile queries against a real (temporary) Postgres."""

from __future__ import annotations

import threading

import psycopg
import pytest
from psycopg.rows import dict_row

from pharmashed_api.community import db, profiles


@pytest.fixture
def conn(pg_url):
    with psycopg.connect(pg_url, row_factory=dict_row, autocommit=True) as c:
        yield c


def test_migrations_apply_once_and_are_recorded(conn):
    assert db.apply_migrations(conn) == ["0001_profiles.sql", "0002_reports.sql", "0003_photos.sql"]
    assert db.apply_migrations(conn) == []          # already applied: nothing to do
    names = [r["name"] for r in conn.execute("select name from schema_migrations order by name")]
    assert names == ["0001_profiles.sql", "0002_reports.sql", "0003_photos.sql"]
    assert conn.execute("select to_regclass('public.profiles') as t").fetchone()["t"] == "profiles"


def test_instances_starting_together_apply_each_migration_exactly_once(pg_url):
    results, errors = [], []

    def run():
        try:
            with psycopg.connect(pg_url, row_factory=dict_row, autocommit=True) as c:
                results.append(db.apply_migrations(c))
        except Exception as exc:  # pragma: no cover - the assertion below reports it
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    files = len(list(db.MIGRATIONS_DIR.glob('*.sql')))
    assert sorted(len(r) for r in results) == [0, 0, 0, 0, 0, files]   # only one instance did the work


def test_a_failing_migration_leaves_nothing_half_applied(conn, tmp_path):
    (tmp_path / "0001_ok.sql").write_text("create table one (id int);")
    (tmp_path / "0002_bad.sql").write_text("create table two (id int); select 1/0;")
    with pytest.raises(psycopg.Error):
        db.apply_migrations(conn, tmp_path)
    assert conn.execute("select to_regclass('public.one') as t").fetchone()["t"] is None   # rolled back
    assert conn.execute("select to_regclass('public.schema_migrations') as t").fetchone()["t"] is None


def test_new_profile_then_update_by_the_same_user(conn):
    db.apply_migrations(conn)
    first = profiles.save_profile(conn, "u1", "RiverPat", True, "TLS")
    assert first["nickname"] == "RiverPat" and first["home_city"] == "TLS" and first["created_at"]
    second = profiles.save_profile(conn, "u1", "RiverPat2", False, None)
    assert second["nickname"] == "RiverPat2" and second["show_on_leaderboard"] is False and second["home_city"] is None
    assert second["created_at"] == first["created_at"]
    assert conn.execute("select count(*) as n from profiles").fetchone()["n"] == 1


def test_a_nickname_is_unique_across_users_ignoring_case(conn):
    db.apply_migrations(conn)
    profiles.save_profile(conn, "u1", "StreamFan")
    with pytest.raises(profiles.NicknameTaken):
        profiles.save_profile(conn, "u2", "streamfan")
    with pytest.raises(profiles.NicknameTaken):
        profiles.save_profile(conn, "u2", "STREAMFAN")
    assert profiles.get_profile(conn, "u2") is None          # the failed attempt left no profile
    profiles.save_profile(conn, "u1", "streamfan")           # the owner may change their own casing


def test_the_profile_the_api_returns_never_contains_the_user_id(conn):
    db.apply_migrations(conn)
    profile = profiles.save_profile(conn, "secret-user-id", "Someone")
    assert "user_id" not in profile and "secret-user-id" not in str(profile)


def test_the_database_itself_rejects_an_unknown_home_city(conn):
    db.apply_migrations(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("insert into profiles (user_id, nickname, home_city) values ('u9', 'Nine', 'XXX')")


def test_the_pool_creates_the_schema_on_first_use(community_db):
    with db.connection() as c:
        assert c.execute("select count(*) as n from profiles").fetchone()["n"] == 0
    db.reset_pool()
    with db.connection() as c:                                # second start: no error, nothing reapplied
        assert c.execute("select count(*) as n from schema_migrations").fetchone()["n"] == len(list(db.MIGRATIONS_DIR.glob("*.sql")))


def test_an_unconfigured_database_is_reported_not_crashed(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db.reset_pool()
    assert db.is_configured() is False
    with pytest.raises(db.NotConfigured):
        db.get_pool()
