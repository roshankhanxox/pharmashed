"""Profiles: nickname rules and the queries behind /api/me."""

from __future__ import annotations

import re
from typing import Any

import psycopg
from psycopg import errors

CITIES = ("TLS", "GNT", "BNV", "CBR", "OSL")
NICKNAME_MIN, NICKNAME_MAX = 3, 20
_NICKNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
# Names that could pass for staff or the system. Compared case-insensitively.
RESERVED_NICKNAMES = frozenset({
    "admin", "administrator", "moderator", "mod", "support", "staff", "official", "system", "root",
    "pharmashed", "oneaquahealth", "null", "undefined", "anonymous", "guest", "me", "you",
})


class InvalidProfile(ValueError):
    """A profile field breaks a rule; str() is a message safe to show the person."""


class InvalidNickname(InvalidProfile):
    """The nickname breaks a rule."""


class NicknameTaken(Exception):
    """Another profile already uses this nickname (compared case-insensitively)."""


def validate_nickname(raw: str) -> str:
    """Return the cleaned nickname or raise InvalidNickname."""
    nickname = (raw or "").strip()
    if not NICKNAME_MIN <= len(nickname) <= NICKNAME_MAX:
        raise InvalidNickname(f"Use {NICKNAME_MIN} to {NICKNAME_MAX} characters.")
    if not _NICKNAME_RE.match(nickname):
        raise InvalidNickname("Use only letters, numbers, dashes and underscores, and start with a letter or number.")
    if not any(c.isalpha() for c in nickname):
        raise InvalidNickname("Include at least one letter.")
    if nickname.lower() in RESERVED_NICKNAMES:
        raise InvalidNickname("That name is reserved. Please pick another.")
    return nickname


def validate_city(city: str | None) -> str | None:
    if city is None or city == "":
        return None
    if city not in CITIES:
        raise InvalidProfile(f"Home city must be one of {', '.join(CITIES)}.")
    return city


def _public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """The fields the API exposes for a profile (never the user id)."""
    if row is None:
        return None
    return {
        "nickname": row["nickname"],
        "show_on_leaderboard": row["show_on_leaderboard"],
        "home_city": row["home_city"],
        "created_at": row["created_at"].isoformat(),
    }


def get_profile(conn: psycopg.Connection, user_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "select nickname, show_on_leaderboard, home_city, created_at from profiles where user_id = %s",
        (user_id,),
    ).fetchone()
    return _public(row)


def save_profile(
    conn: psycopg.Connection,
    user_id: str,
    nickname: str,
    show_on_leaderboard: bool = True,
    home_city: str | None = None,
) -> dict[str, Any]:
    """Create or update the user's profile. Raises NicknameTaken if another user has the nickname."""
    try:
        with conn.transaction():
            row = conn.execute(
                """
                insert into profiles (user_id, nickname, show_on_leaderboard, home_city)
                values (%s, %s, %s, %s)
                on conflict (user_id) do update
                   set nickname = excluded.nickname,
                       show_on_leaderboard = excluded.show_on_leaderboard,
                       home_city = excluded.home_city,
                       updated_at = now()
                returning nickname, show_on_leaderboard, home_city, created_at
                """,
                (user_id, nickname, show_on_leaderboard, home_city),
            ).fetchone()
    except errors.UniqueViolation as exc:
        raise NicknameTaken(nickname) from exc
    return _public(row)  # type: ignore[return-value]
