"""Postgres access: a connection pool and a tiny migration runner.

The pool is created on first use, and migrations from api/migrations/*.sql are applied then, so a
fresh Neon database sets itself up. Two details matter for Neon's pooled endpoint (PgBouncer in
transaction mode): prepared statements are switched off, and the migration lock is a
*transaction-level* advisory lock (a session-level one would not survive the connection being
swapped between statements).
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from pharmashed_api.community import config, reports

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
_MIGRATION_LOCK_ID = 7_301_505  # arbitrary constant shared by every instance of this app


class NotConfigured(Exception):
    """DATABASE_URL is not set."""


_pool: ConnectionPool | None = None
_lock = threading.Lock()


def is_configured() -> bool:
    return config.database_url() is not None


def apply_migrations(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every not-yet-applied *.sql file in name order. Returns the names applied.

    Runs in one transaction under an advisory lock, so two app instances starting together cannot
    both apply the same file, and a failing migration leaves nothing half-done.
    """
    applied_now: list[str] = []
    with conn.transaction():
        conn.execute("select pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
        conn.execute(
            "create table if not exists schema_migrations ("
            "name text primary key, applied_at timestamptz not null default now())"
        )
        done = {row["name"] for row in conn.execute("select name from schema_migrations")}
        for path in sorted(directory.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text())
            conn.execute("insert into schema_migrations (name) values (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


def get_pool() -> ConnectionPool:
    """The shared pool, created (and the schema migrated) on first use."""
    global _pool
    with _lock:
        if _pool is None:
            url = config.database_url()
            if not url:
                raise NotConfigured("DATABASE_URL is not set")
            pool = ConnectionPool(
                url,
                min_size=1,
                max_size=5,
                open=False,
                check=ConnectionPool.check_connection,  # drop connections Neon closed while idle
                kwargs={"row_factory": dict_row, "prepare_threshold": None},
            )
            pool.open(wait=True, timeout=30)
            try:
                with pool.connection() as conn:
                    for name in apply_migrations(conn):
                        log.info("applied migration %s", name)
                    with conn.transaction():
                        if reports.ensure_samples(conn):
                            log.info("added the labelled sample reports")
            except Exception:
                pool.close()
                raise
            _pool = pool
        return _pool


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """A pooled connection; commits when the block ends normally, rolls back on error."""
    with get_pool().connection() as conn:
        yield conn


def reset_pool() -> None:
    """Close and forget the pool (tests, or after DATABASE_URL changes)."""
    global _pool
    with _lock:
        if _pool is not None:
            _pool.close()
            _pool = None
