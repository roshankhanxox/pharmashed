"""Flags from readers and the moderator's queue (S5 phase 5).

A report is held (status `pending`) when it is filed with something suspicious, or pulled back to pending when
enough different people flag it. A moderator then approves it (it goes public and is scored) or hides it
(it leaves the map, its points are reversed, and its photo is deleted). Every decision is logged.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg

from pharmashed_api.community import points, proofread, reports, storage

log = logging.getLogger(__name__)

FLAG_REASONS = {
    "inaccurate": "Looks wrong or made up",
    "personal_info": "Shows personal details",
    "inappropriate": "Inappropriate or offensive",
    "not_a_stream": "Not about a stream",
    "spam": "Spam or advertising",
}
FLAGS_TO_HOLD = 3            # this many different people flagging a public report sends it back for review
MAX_FLAGS_PER_DAY = 20
NOTE_MAX = 300


class ModerationError(ValueError):
    """The action is not allowed; str() is a message safe to show."""


class NotFound(ModerationError):
    """No such report."""


class TooManyFlags(Exception):
    """The person flagged too many reports today."""


def is_moderator(conn: psycopg.Connection, user: Any) -> bool:
    """True if the person is a moderator: a row in `moderators` (by user id), or the ADMIN_EMAILS route
    (listed email that the auth service verified)."""
    if user.is_admin:
        return True
    return conn.execute("select 1 from moderators where user_id = %s", (user.id,)).fetchone() is not None


def flag_report(conn: psycopg.Connection, report_id: str, user_id: str, reason: str) -> dict[str, Any]:
    """Record a flag. Returns {flagged: bool (False if already flagged by this person), held: bool}."""
    if reason not in FLAG_REASONS:
        raise ModerationError("Choose one of the listed reasons.")
    row = conn.execute("select user_id, status, is_sample from reports where id = %s", (report_id,)).fetchone()
    if row is None or row["status"] != "approved" or row["is_sample"]:
        raise NotFound("That report cannot be flagged.")
    if row["user_id"] == user_id:
        raise ModerationError("You cannot flag your own report.")
    today = conn.execute(
        "select count(*) as n from report_flags where flagged_by = %s and created_at > now() - interval '1 day'", (user_id,)
    ).fetchone()["n"]
    if today >= MAX_FLAGS_PER_DAY:
        raise TooManyFlags
    inserted = conn.execute(
        "insert into report_flags (report_id, flagged_by, reason) values (%s, %s, %s)"
        " on conflict (report_id, flagged_by) do nothing returning id",
        (report_id, user_id, reason),
    ).fetchone()
    open_flags = conn.execute(
        "select count(*) as n from report_flags where report_id = %s and resolved_at is null", (report_id,)
    ).fetchone()["n"]
    held = False
    if open_flags >= FLAGS_TO_HOLD:
        held = conn.execute(
            "update reports set status = 'pending' where id = %s and status = 'approved' returning id", (report_id,)
        ).fetchone() is not None
    return {"flagged": inserted is not None, "held": held}


def _why(row: dict[str, Any], flags: list[dict[str, Any]]) -> list[str]:
    """Plain-language reasons an item is in the queue."""
    why = []
    if row["status"] == "pending":
        text = row["note_clean"] or row["note_raw"] or ""
        if proofread.deterministic_flags(row["note_raw"] or "") or proofread.deterministic_flags(text):
            why.append("The note may contain personal details")
        if row["photo_id"] and row["ai_ok"] is False:
            why.append("The photo check flagged it: " + ", ".join(sorted(row["ai_flags"])))
        if row["photo_id"] and row["ai_ok"] is None:
            why.append("The photo could not be checked automatically")
    if flags:
        why.append(f"Flagged by {len(flags)} {'person' if len(flags) == 1 else 'people'}")
    return why or ["Waiting for review"]


def queue(conn: psycopg.Connection, limit: int = 100) -> list[dict[str, Any]]:
    """Reports needing a decision: held ones, and public ones with open flags. Oldest first."""
    rows = conn.execute(
        """
        select r.*, p.nickname, ph.id as photo_id, ph.object_key, ph.ai_ok, ph.ai_flags
        from reports r
        left join profiles p on p.user_id = r.user_id
        left join report_photos ph on ph.report_id = r.id
        where not r.is_sample and (
            r.status = 'pending'
            or (r.status = 'approved' and exists (select 1 from report_flags f where f.report_id = r.id and f.resolved_at is null)))
        order by r.created_at limit %s
        """,
        (max(1, min(limit, 200)),),
    ).fetchall()
    ids = [r["id"] for r in rows]
    flag_rows = conn.execute(
        "select report_id, reason, created_at from report_flags where report_id = any(%s) and resolved_at is null order by created_at",
        (ids,),
    ).fetchall() if ids else []
    out = []
    for r in rows:
        flags = [f for f in flag_rows if f["report_id"] == r["id"]]
        photo = None
        if r["photo_id"] and storage.is_configured():
            try:
                photo = storage.presigned_get(r["object_key"])
            except Exception:  # noqa: BLE001 - a missing preview must not break the queue
                log.exception("could not sign photo link")
        out.append({
            **reports._public(r, None),  # noqa: SLF001
            "status": r["status"],
            "nickname": r["nickname"],
            "note_raw": r["note_raw"],
            "why": _why(r, flags),
            "flags": [{"reason": f["reason"], "label": FLAG_REASONS[f["reason"]]} for f in flags],
            "photo_preview": photo,
        })
    return out


def _decide(conn: psycopg.Connection, report_id: str, admin_id: str, action: str, note: str) -> None:
    note = (note or "").strip()
    if len(note) > NOTE_MAX:
        raise ModerationError(f"Keep the note under {NOTE_MAX} characters.")
    conn.execute(
        "insert into moderation_actions (report_id, admin_user_id, action, note) values (%s, %s, %s, %s)",
        (report_id, admin_id, action, note),
    )
    conn.execute("update report_flags set resolved_at = now() where report_id = %s and resolved_at is null", (report_id,))


def approve(conn: psycopg.Connection, report_id: str, admin_id: str, note: str = "") -> dict[str, Any]:
    """Approve a held or flagged report: it is public, and scored if it never was. Hidden reports stay hidden."""
    row = conn.execute("select status, is_sample from reports where id = %s for update", (report_id,)).fetchone()
    if row is None or row["is_sample"]:
        raise NotFound("No such report.")
    if row["status"] == "hidden":
        raise ModerationError("A hidden report cannot be approved again. Ask the person to file a new one.")
    conn.execute("update reports set status = 'approved' where id = %s", (report_id,))
    _decide(conn, report_id, admin_id, "approve", note)
    return {"status": "approved", "rewards": points.award_for_report(conn, report_id)}


def hide(conn: psycopg.Connection, report_id: str, admin_id: str, note: str = "") -> dict[str, Any]:
    """Hide a report: off the map, points reversed, photo deleted."""
    row = conn.execute("select status, is_sample from reports where id = %s for update", (report_id,)).fetchone()
    if row is None or row["is_sample"]:
        raise NotFound("No such report.")
    conn.execute("update reports set status = 'hidden' where id = %s", (report_id,))
    removed = points.reverse_for_report(conn, report_id)
    for photo in conn.execute("select id, object_key from report_photos where report_id = %s", (report_id,)).fetchall():
        try:
            storage.delete(photo["object_key"])
        except Exception:  # noqa: BLE001 - the row is removed regardless so the photo can never be served
            log.exception("could not delete photo object %s", photo["object_key"])
        conn.execute("delete from report_photos where id = %s", (photo["id"],))
    _decide(conn, report_id, admin_id, "hide", note)
    return {"status": "hidden", "points_removed": removed}
