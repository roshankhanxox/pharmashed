"""Citizen reports (S5 phase 2): the checklist rules, saving a report, and listing reports.

Reports are an unverified layer beside the model. They never change a score.
"""

from __future__ import annotations

import random
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

import psycopg
from psycopg.types.json import Jsonb

from pharmashed_api import data
from pharmashed_api.community import geo, photos

SAMPLE_USER = "sample"
NOTE_MAX = 500
MAX_REPORTS_PER_DAY = 10          # saved reports per person per rolling 24 h (spam guard, not the points cap)
MAX_AGE_DAYS = 30                 # how far back a visit may be dated
CLOCK_SKEW = timedelta(minutes=5)

# Each checklist question and its allowed answers. "animals" takes several; every other question takes one.
CHECKLIST: dict[str, tuple[str, ...]] = {
    "water_colour": ("clear", "cloudy", "brown", "green", "grey"),
    "smell": ("none", "earthy", "musty", "sewage", "chemical"),
    "foam": ("none", "light", "heavy"),
    "litter": ("none", "some", "a_lot"),
    "animals": ("fish", "birds", "insects", "frogs", "none_seen"),
    "flow": ("dry", "trickle", "normal", "high"),
    "rain_24h": ("none", "light", "heavy"),
}
MULTI = frozenset({"animals"})
_URL_RE = re.compile(r"https?://|www\.", re.I)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class InvalidReport(ValueError):
    """A report field breaks a rule; str() is a message safe to show the person."""


class TooManyReports(Exception):
    """The person reached the daily limit of saved reports."""


def clean_checklist(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return only the known, valid answers, or raise InvalidReport. At least one answer is required."""
    out: dict[str, Any] = {}
    for key, value in (raw or {}).items():
        if key not in CHECKLIST:
            raise InvalidReport(f"Unknown question: {key}.")
        allowed = CHECKLIST[key]
        if value in (None, "", []):
            continue
        if key in MULTI:
            if not isinstance(value, list) or not all(isinstance(v, str) and v in allowed for v in value):
                raise InvalidReport(f"Invalid answer for {key}.")
            out[key] = sorted(set(value))
        else:
            if not isinstance(value, str) or value not in allowed:
                raise InvalidReport(f"Invalid answer for {key}.")
            out[key] = value
    if not out:
        raise InvalidReport("Answer at least one question.")
    return out


def clean_note(raw: str | None) -> str:
    """Trim, drop control characters, and refuse links (the main spam vector). Empty is fine."""
    note = _CONTROL_RE.sub("", (raw or "")).strip()
    if len(note) > NOTE_MAX:
        raise InvalidReport(f"Keep the note under {NOTE_MAX} characters.")
    if _URL_RE.search(note):
        raise InvalidReport("Please leave links out of the note.")
    return note


def clean_observed_at(value: datetime, now: datetime | None = None) -> datetime:
    """Visits must be in the past (small clock skew allowed) and at most 30 days old. Returns UTC."""
    now = now or datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    value = value.astimezone(UTC)
    if value > now + CLOCK_SKEW:
        raise InvalidReport("The visit time is in the future.")
    if value < now - timedelta(days=MAX_AGE_DAYS):
        raise InvalidReport(f"Reports must be about a visit in the last {MAX_AGE_DAYS} days.")
    return value


def _personal(note: str) -> bool:
    from pharmashed_api.community import proofread  # proofread imports this module

    return bool(proofread.deterministic_flags(note))


def locate(lat: float, lon: float) -> geo.Placement:
    """Place a pin among the model sites and cities."""
    catalogue = data.sites()
    return geo.place_pin(lat, lon, catalogue["sites"], catalogue["cities"])


def _public(row: Mapping[str, Any], viewer_id: str | None) -> dict[str, Any]:
    """The fields the API exposes (never the user id)."""
    sample = bool(row["is_sample"])
    return {
        "id": str(row["id"]),
        "lat": row["lat"],
        "lon": row["lon"],
        "site_id": row["site_id"],
        "city": row["city"],
        "observed_at": row["observed_at"].isoformat(),
        "checklist": row["checklist"],
        "note": row["note_clean"] or row["note_raw"],
        "is_sample": sample,
        "author": "Sample report" if sample else (row.get("nickname") or "A citizen"),
        "mine": bool(viewer_id) and row["user_id"] == viewer_id,
        "photo_url": f"/photos/{row['photo_id']}" if row.get("photo_id") and row["status"] == "approved" else None,
    }


_SELECT = """
    select r.*, p.nickname, ph.id as photo_id
    from reports r
    left join profiles p on p.user_id = r.user_id
    left join report_photos ph on ph.report_id = r.id
"""


def create_report(
    conn: psycopg.Connection,
    user_id: str,
    *,
    lat: float,
    lon: float,
    observed_at: datetime,
    checklist: Mapping[str, Any],
    note: str | None,
    note_clean: str | None = None,
    photo_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate and save one report; return its public form. Raises InvalidReport or TooManyReports.

    `note_clean` is the AI-tidied version the person chose to use; both versions are kept. A note that looks
    like it contains personal details, or a photo the AI flagged or could not check, waits for a moderator
    (status `pending`) instead of going public. Raises photos.InvalidPhoto for a photo that is not the person's.
    """
    now = now or datetime.now(UTC)
    answers = clean_checklist(checklist)
    text = clean_note(note)
    tidy = clean_note(note_clean) if note_clean else None
    status = "pending" if _personal(text) or _personal(tidy or "") else "approved"
    when = clean_observed_at(observed_at, now)
    placement = locate(lat, lon)
    recent = conn.execute(
        "select count(*) as n from reports where user_id = %s and created_at > %s",
        (user_id, now - timedelta(days=1)),
    ).fetchone()["n"]
    if recent >= MAX_REPORTS_PER_DAY:
        raise TooManyReports
    row = conn.execute(
        """
        insert into reports (user_id, lat, lon, site_id, city, distance_m, observed_at, checklist, note_raw,
                             note_clean, status)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id
        """,
        (user_id, lat, lon, placement.site_id, placement.city, placement.distance_m, when,
         Jsonb(answers), text, tidy, status),
    ).fetchone()
    if photo_id:
        if photos.attach(conn, photo_id, user_id, row["id"]) is not True:
            conn.execute("update reports set status = 'pending' where id = %s", (row["id"],))
    return get_report(conn, row["id"], user_id)


def get_report(conn: psycopg.Connection, report_id: Any, viewer_id: str | None) -> dict[str, Any]:
    """One report in public form."""
    row = conn.execute(_SELECT + " where r.id = %s", (report_id,)).fetchone()
    return _public(row, viewer_id)


def list_reports(
    conn: psycopg.Connection,
    viewer_id: str | None,
    *,
    site_id: str | None = None,
    city: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Approved reports, newest visit first, optionally for one site or city."""
    where, params = ["r.status = 'approved'"], []
    if site_id:
        where.append("r.site_id = %s")
        params.append(site_id)
    if city:
        where.append("r.city = %s")
        params.append(city)
    rows = conn.execute(
        f"{_SELECT} where {' and '.join(where)} order by r.observed_at desc limit %s",
        (*params, max(1, min(limit, 500))),
    ).fetchall()
    return [_public(r, viewer_id) for r in rows]


def my_reports(conn: psycopg.Connection, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Everything the person has filed, whatever its status (they see their own hidden ones too)."""
    rows = conn.execute(
        f"{_SELECT} where r.user_id = %s order by r.created_at desc limit %s", (user_id, limit)
    ).fetchall()
    return [{**_public(r, user_id), "status": r["status"]} for r in rows]


# -- sample reports -----------------------------------------------------------------------------------

_SAMPLE_NOTES = (
    "", "Calm water, a few leaves on the surface.", "Faint smell near the bridge.",
    "Some litter caught on the bank.", "Ducks and a heron nearby.", "Water looked a bit cloudy after the rain.",
    "Foam collecting by the culvert.", "Low flow, mostly pools.",
)


def ensure_samples(conn: psycopg.Connection, now: datetime | None = None) -> int:
    """Insert the labelled sample reports once, so a fresh demo is not empty. Returns how many were added.

    They are deterministic (fixed seed) and clearly marked `is_sample`; they exist only to show the feature.
    """
    now = now or datetime.now(UTC)
    conn.execute("select pg_advisory_xact_lock(hashtext('pharmashed_sample_reports'))")
    if conn.execute("select exists(select 1 from reports where is_sample) as e").fetchone()["e"]:
        return 0
    rng = random.Random(20260101)
    catalogue = data.sites()
    added = 0
    for city in catalogue["cities"]:
        city_sites = [s for s in catalogue["sites"] if s["city"] == city["id"]]
        for site in rng.sample(city_sites, k=min(4, len(city_sites))):
            lon, lat = site["lonlat"]
            checklist = {
                "water_colour": rng.choice(CHECKLIST["water_colour"][:3]),
                "smell": rng.choice(CHECKLIST["smell"][:3]),
                "foam": rng.choice(CHECKLIST["foam"]),
                "litter": rng.choice(CHECKLIST["litter"]),
                "flow": rng.choice(CHECKLIST["flow"][1:]),
            }
            conn.execute(
                """
                insert into reports (user_id, is_sample, lat, lon, site_id, city, distance_m, observed_at,
                                     checklist, note_raw)
                values (%s, true, %s, %s, %s, %s, 0, %s, %s, %s)
                """,
                (SAMPLE_USER, lat, lon, site["id"], city["id"], now - timedelta(days=rng.randint(1, 20),
                 hours=rng.randint(0, 12)), Jsonb(checklist), rng.choice(_SAMPLE_NOTES)),
            )
            added += 1
    return added
