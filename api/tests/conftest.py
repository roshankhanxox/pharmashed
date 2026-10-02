"""Shared fixtures. The community tests run against a real, throwaway Postgres cluster started from
the locally installed Postgres binaries (no Docker, no cloud account); they skip cleanly if Postgres
is not installed."""

from __future__ import annotations

import glob
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import psycopg
import pytest


def _pg_bin(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for pattern in ("/opt/homebrew/opt/postgresql@*/bin", "/usr/local/opt/postgresql@*/bin", "/usr/lib/postgresql/*/bin"):
        for directory in sorted(glob.glob(pattern), reverse=True):
            candidate = Path(directory) / name
            if candidate.exists():
                return str(candidate)
    return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def pg_server(tmp_path_factory):
    """A temporary Postgres cluster for the whole test session; yields (host, port)."""
    initdb, pg_ctl = _pg_bin("initdb"), _pg_bin("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("Postgres binaries (initdb, pg_ctl) not found; install Postgres to run the community tests")
    root = tmp_path_factory.mktemp("pg")
    data = root / "data"
    subprocess.run([initdb, "-D", str(data), "-A", "trust", "-U", "postgres", "--no-sync", "-E", "UTF8"],
                   check=True, capture_output=True)
    port = _free_port()
    # TCP only: no Unix socket, whose path would exceed macOS's ~104-character limit under pytest's temp dir.
    options = f"-p {port} -c listen_addresses=127.0.0.1 -c unix_socket_directories= -c fsync=off"
    subprocess.run([pg_ctl, "-D", str(data), "-o", options, "-l", str(root / "pg.log"), "-w", "start"],
                   check=True, capture_output=True)
    try:
        yield "127.0.0.1", port
    finally:
        subprocess.run([pg_ctl, "-D", str(data), "-m", "immediate", "stop"], capture_output=True)


@pytest.fixture
def pg_url(pg_server):
    """A fresh, empty database in the temporary cluster; returns its connection URL."""
    host, port = pg_server
    name = f"t_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(f"postgresql://postgres@{host}:{port}/postgres", autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
    try:
        yield f"postgresql://postgres@{host}:{port}/{name}"
    finally:
        with psycopg.connect(f"postgresql://postgres@{host}:{port}/postgres", autocommit=True) as admin:
            admin.execute(f'drop database if exists "{name}" with (force)')


@pytest.fixture
def community_db(pg_url, monkeypatch):
    """DATABASE_URL pointing at a fresh database, with the API's connection pool reset around the test."""
    from pharmashed_api.community import db

    monkeypatch.setenv("DATABASE_URL", pg_url)
    db.reset_pool()
    yield pg_url
    db.reset_pool()


@pytest.fixture(autouse=True)
def _no_real_services(monkeypatch):
    """main.py loads the developer's .env; tests must never reach the real bucket or a real model key."""
    for name in ("AWS_ENDPOINT_URL_S3", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET",
                 "OPENAI_API_KEY", "GROQ_API_KEY", "ASSISTANT_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    from pharmashed_api.community import storage

    storage.reset_client()
