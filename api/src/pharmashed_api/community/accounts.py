"""Deleting an account (S5 phase 5): everything we hold about a person, in one transaction."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

import psycopg

from pharmashed_api.community import storage

log = logging.getLogger(__name__)
_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")


def delete_account(conn: psycopg.Connection, user_id: str) -> dict[str, int]:
    """Delete the person's profile, reports (and their flags, points, badges, photos) and their sign-in user.

    Photo files are removed from the bucket first (a failure is logged and the database rows are still deleted,
    so a leftover file can never be linked to anyone). Flags the person raised on other people's reports are
    removed too. Returns counts for the confirmation message.
    """
    keys = [r["object_key"] for r in conn.execute("select object_key from report_photos where user_id = %s", (user_id,))]
    for key in keys:
        try:
            storage.delete(key)
        except Exception:  # noqa: BLE001
            log.exception("could not delete photo object %s", key)
    counts: dict[str, int] = {"photos": len(keys)}
    conn.execute("delete from report_flags where flagged_by = %s", (user_id,))
    conn.execute("delete from moderation_actions where admin_user_id = %s", (user_id,))
    conn.execute("delete from report_photos where user_id = %s", (user_id,))
    conn.execute("delete from points_events where user_id = %s", (user_id,))
    conn.execute("delete from badges_awarded where user_id = %s", (user_id,))
    counts["reports"] = conn.execute("delete from reports where user_id = %s", (user_id,)).rowcount
    conn.execute("delete from profiles where user_id = %s", (user_id,))
    counts["sign_in_user"] = _delete_sign_in_user(conn, user_id)
    return counts


def _delete_sign_in_user(conn: psycopg.Connection, user_id: str) -> int:
    """Remove the Neon Auth user, sessions, accounts and verification codes (they live in the same database)."""
    if not _UUID_RE.match(user_id) or conn.execute("select to_regclass('neon_auth.\"user\"') as t").fetchone()["t"] is None:
        return 0
    uid: Any = uuid.UUID(user_id)
    user = conn.execute('select email from neon_auth."user" where id = %s', (uid,)).fetchone()
    if user is None:
        return 0
    conn.execute('delete from neon_auth.session where "userId" = %s', (uid,))
    conn.execute('delete from neon_auth.account where "userId" = %s', (uid,))
    conn.execute("delete from neon_auth.verification where identifier = %s", (user["email"],))
    return conn.execute('delete from neon_auth."user" where id = %s', (uid,)).rowcount
