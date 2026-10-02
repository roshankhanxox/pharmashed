"""Points, badges, the weekly challenge and the leaderboard (S5 phase 4).

Rules (all numbers live in POINTS and CAPS so they are easy to tune):
- An approved report near one of our sites earns +10; a photo that passed the check +5; the person's first
  report at that site +5; a site nobody had reported in the previous 30 days +10; a weekly streak bonus
  (+5 per consecutive week beyond the first, at most +20); the weekly challenge +20.
- At most 3 rewarded reports per UTC day, and one rewarded report per site per person per 7 days. Extra reports
  are still saved and shown, they just earn nothing. A reason row with 0 points records why.
- Points are only awarded for approved reports (call award_for_report again when a moderator approves) and are
  reversed with negative rows when a report is hidden. Badges are recomputed from the ledger, so a reversal can
  also take a badge back.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg

POINTS = {"report": 10, "photo": 5, "first_at_site": 5, "neglected_site": 10, "challenge": 20}
STREAK_STEP, STREAK_MAX = 5, 20
CAPS = {"per_day": 3, "site_cooldown_days": 7, "neglected_days": 30}

REASON_LABELS = {
    "report": "Report approved",
    "photo": "Photo passed the check",
    "first_at_site": "Your first report at this site",
    "neglected_site": "A site nobody had reported in 30 days",
    "streak": "Weekly streak bonus",
    "challenge": "Weekly challenge completed",
    "no_points:outside_coverage": "Not near one of our sites, so no points (it is still on the map)",
    "no_points:daily_cap": "You have reached 3 rewarded reports today",
    "no_points:site_cooldown": "You already earned points at this site in the last 7 days",
}

BADGES: dict[str, tuple[str, str]] = {
    "first_report": ("First report", "Had a report approved"),
    "regular": ("Regular", "5 rewarded reports"),
    "explorer": ("Explorer", "Rewarded reports at 5 different sites"),
    "photographer": ("Photographer", "5 rewarded reports with a checked photo"),
    "streak_3": ("Three-week streak", "Rewarded reports in 3 weeks in a row"),
    "neglected_hero": ("Neglected-stream hero", "3 sites nobody had reported in 30 days"),
    "challenger": ("Challenger", "Completed a weekly challenge"),
}

CHALLENGES: list[tuple[str, str, str]] = [
    ("new_site", "Somewhere new", "Report a site you have not reported before."),
    ("photo", "Show us", "Add a photo that passes the check."),
    ("neglected", "Forgotten stream", "Report a site nobody has reported in the last 30 days."),
    ("detailed", "Look closely", "Answer at least five of the questions."),
]

# Positive events that have not been cancelled by a matching reversal row.
_ACTIVE = (
    "points_events e where e.points > 0 and not exists ("
    "select 1 from points_events x where x.report_id = e.report_id and x.reason = 'reversal:' || e.reason)"
)


def week_key(when: datetime) -> str:
    """ISO week label such as 2026-W23 (weeks start on Monday, UTC)."""
    iso = when.astimezone(UTC).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def week_start(when: datetime) -> datetime:
    """Monday 00:00 UTC of the week containing `when`."""
    d = when.astimezone(UTC)
    return (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def challenge_for(when: datetime) -> dict[str, str]:
    """This week's challenge, chosen from the list by ISO week number (no table needed)."""
    key, title, text = CHALLENGES[when.astimezone(UTC).isocalendar().week % len(CHALLENGES)]
    return {"key": key, "title": title, "description": text, "week": week_key(when)}


def _add(conn: psycopg.Connection, user_id: str, report_id: Any, points: int, reason: str, when: datetime) -> bool:
    """Insert one ledger row; False if this (report, reason) already exists."""
    row = conn.execute(
        "insert into points_events (user_id, report_id, points, reason, created_at) values (%s, %s, %s, %s, %s)"
        " on conflict (report_id, reason) do nothing returning id",
        (user_id, report_id, points, reason, when),
    ).fetchone()
    return row is not None


def _rewarded_weeks(conn: psycopg.Connection, user_id: str) -> set[str]:
    rows = conn.execute(
        "select r.created_at from points_events e join reports r on r.id = e.report_id"
        " where e.user_id = %s and e.reason = 'report' and e.points > 0 and not exists ("
        "select 1 from points_events x where x.report_id = e.report_id and x.reason = 'reversal:report')",
        (user_id,),
    ).fetchall()
    return {week_key(r["created_at"]) for r in rows}


def _streak_length(weeks: set[str], when: datetime) -> int:
    """Consecutive weeks, ending at the week of `when`, that contain a rewarded report."""
    n, cursor = 0, week_start(when)
    while week_key(cursor) in weeks:
        n += 1
        cursor -= timedelta(days=7)
    return n


def award_for_report(conn: psycopg.Connection, report_id: Any) -> dict[str, Any]:
    """Apply the rules to one report. Safe to call again: a report is only ever scored once.

    Returns {"lines": [{reason, label, points}], "total": int, "new_badges": [{key, title}]}; empty if the report is a
    sample, not approved, or already scored.
    """
    rep = conn.execute(
        "select r.*, ph.ai_ok from reports r left join report_photos ph on ph.report_id = r.id where r.id = %s",
        (report_id,),
    ).fetchone()
    nothing = {"lines": [], "total": 0, "new_badges": []}
    if rep is None or rep["is_sample"] or rep["status"] != "approved":
        return nothing
    user_id, site_id, when = rep["user_id"], rep["site_id"], rep["created_at"]
    conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"points:{user_id}",))
    if conn.execute("select 1 from points_events where report_id = %s limit 1", (report_id,)).fetchone():
        return nothing

    lines: list[tuple[str, int]] = []

    def skip(reason: str) -> dict[str, Any]:
        _add(conn, user_id, report_id, 0, reason, when)
        return {"lines": [_line(reason, 0)], "total": 0, "new_badges": []}

    if not site_id:
        return skip("no_points:outside_coverage")
    day_start = when.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today = conn.execute(
        "select count(*) as n from points_events e join reports r on r.id = e.report_id"
        " where e.user_id = %s and e.reason = 'report' and e.points > 0 and r.created_at >= %s and r.created_at < %s"
        " and not exists (select 1 from points_events x where x.report_id = e.report_id and x.reason = 'reversal:report')",
        (user_id, day_start, day_start + timedelta(days=1)),
    ).fetchone()["n"]
    if today >= CAPS["per_day"]:
        return skip("no_points:daily_cap")
    at_site = conn.execute(
        "select r.created_at from points_events e join reports r on r.id = e.report_id"
        " where e.user_id = %s and e.reason = 'report' and e.points > 0 and r.site_id = %s and r.id <> %s"
        " and not exists (select 1 from points_events x where x.report_id = e.report_id and x.reason = 'reversal:report')",
        (user_id, site_id, report_id),
    ).fetchall()
    if any(abs((when - r["created_at"]).total_seconds()) < CAPS["site_cooldown_days"] * 86400 for r in at_site):
        return skip("no_points:site_cooldown")

    lines.append(("report", POINTS["report"]))
    if rep["ai_ok"] is True:
        lines.append(("photo", POINTS["photo"]))
    first_here = not at_site
    if first_here:
        lines.append(("first_at_site", POINTS["first_at_site"]))
    neglected = conn.execute(
        "select 1 from reports r where r.site_id = %s and r.id <> %s and r.status = 'approved' and not r.is_sample"
        " and r.created_at > %s and r.created_at < %s limit 1",
        (site_id, report_id, when - timedelta(days=CAPS["neglected_days"]), when),
    ).fetchone() is None
    if neglected:
        lines.append(("neglected_site", POINTS["neglected_site"]))

    # Weekly streak: counted after this report's own week is known to have a rewarded report.
    weeks = _rewarded_weeks(conn, user_id) | {week_key(when)}
    streak = _streak_length(weeks, when)
    already = conn.execute(
        "select 1 from points_events where user_id = %s and reason = 'streak' and points > 0 and created_at >= %s and created_at < %s",
        (user_id, week_start(when), week_start(when) + timedelta(days=7)),
    ).fetchone()
    if streak >= 2 and not already:
        lines.append(("streak", min(STREAK_STEP * (streak - 1), STREAK_MAX)))

    # Weekly challenge, once per week.
    ch = challenge_for(when)
    answered = sum(1 for v in rep["checklist"].values() if v)
    met = {"new_site": first_here, "photo": rep["ai_ok"] is True, "neglected": neglected, "detailed": answered >= 5}[ch["key"]]
    got_it = conn.execute(
        "select 1 from points_events where user_id = %s and points > 0 and reason like 'challenge%%' and created_at >= %s and created_at < %s",
        (user_id, week_start(when), week_start(when) + timedelta(days=7)),
    ).fetchone()
    if met and not got_it:
        lines.append(("challenge", POINTS["challenge"]))

    for reason, points in lines:
        _add(conn, user_id, report_id, points, reason, when)
    new_badges = sync_badges(conn, user_id, when)
    return {"lines": [_line(r, p) for r, p in lines], "total": sum(p for _, p in lines),
            "new_badges": [{"key": k, "title": BADGES[k][0]} for k in new_badges]}


def _line(reason: str, points: int) -> dict[str, Any]:
    return {"reason": reason, "label": REASON_LABELS.get(reason, reason), "points": points}


def reverse_for_report(conn: psycopg.Connection, report_id: Any, when: datetime | None = None) -> int:
    """Cancel every point a report earned (call when a moderator hides it). Returns the points removed."""
    when = when or datetime.now(UTC)
    rows = conn.execute(
        f"select e.user_id, e.reason, e.points from {_ACTIVE} and e.report_id = %s", (report_id,)
    ).fetchall()
    removed = 0
    for r in rows:
        if _add(conn, r["user_id"], report_id, -r["points"], f"reversal:{r['reason']}", when):
            removed += r["points"]
    for user_id in {r["user_id"] for r in rows}:
        sync_badges(conn, user_id, when)
    return removed


def _earned_keys(conn: psycopg.Connection, user_id: str) -> set[str]:
    """Badges the person qualifies for right now, from the ledger."""
    ev = conn.execute(
        "select e.report_id, e.reason, r.site_id, r.created_at from points_events e join reports r on r.id = e.report_id"
        " where e.user_id = %s and e.points > 0 and not exists ("
        "select 1 from points_events x where x.report_id = e.report_id and x.reason = 'reversal:' || e.reason)",
        (user_id,),
    ).fetchall()
    rewarded = [e for e in ev if e["reason"] == "report"]
    sites = {e["site_id"] for e in rewarded if e["site_id"]}
    weeks = {week_key(e["created_at"]) for e in rewarded}
    best = 0
    for w in weeks:
        # a streak starts where the previous week is missing
        start = datetime.fromisocalendar(int(w[:4]), int(w[6:]), 1).replace(tzinfo=UTC)
        if week_key(start - timedelta(days=7)) not in weeks:
            best = max(best, _run(weeks, start))
    keys = set()
    if rewarded:
        keys.add("first_report")
    if len(rewarded) >= 5:
        keys.add("regular")
    if len(sites) >= 5:
        keys.add("explorer")
    if sum(1 for e in ev if e["reason"] == "photo") >= 5:
        keys.add("photographer")
    if best >= 3:
        keys.add("streak_3")
    if sum(1 for e in ev if e["reason"] == "neglected_site") >= 3:
        keys.add("neglected_hero")
    if any(e["reason"] == "challenge" for e in ev):
        keys.add("challenger")
    return keys


def _run(weeks: set[str], start: datetime) -> int:
    """Length of the run of consecutive weeks beginning at `start`."""
    n, cursor = 0, start
    while week_key(cursor) in weeks:
        n += 1
        cursor += timedelta(days=7)
    return n


def sync_badges(conn: psycopg.Connection, user_id: str, when: datetime | None = None) -> list[str]:
    """Make the badge table match the ledger. Returns the badges newly awarded."""
    when = when or datetime.now(UTC)
    want = _earned_keys(conn, user_id)
    have = {r["badge"] for r in conn.execute("select badge from badges_awarded where user_id = %s", (user_id,))}
    for badge in sorted(want - have):
        conn.execute("insert into badges_awarded (user_id, badge, awarded_at) values (%s, %s, %s)", (user_id, badge, when))
    for badge in have - want:
        conn.execute("delete from badges_awarded where user_id = %s and badge = %s", (user_id, badge))
    return sorted(want - have)


def progress(conn: psycopg.Connection, user_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Everything the My streams page shows, in four queries (each costs a network round trip to the database)."""
    now = now or datetime.now(UTC)
    this_week = week_start(now)
    summary = conn.execute(
        """
        select coalesce(sum(points), 0) as total,
               coalesce(sum(points) filter (where created_at >= %s), 0) as week,
               (select rank from (select user_id, rank() over (order by sum(points) desc) as rank
                                  from points_events group by user_id having sum(points) > 0) t
                where user_id = %s) as rank
        from points_events where user_id = %s
        """,
        (this_week, user_id, user_id),
    ).fetchone()
    earned = {r["badge"]: r["awarded_at"] for r in conn.execute("select badge, awarded_at from badges_awarded where user_id = %s", (user_id,))}
    recent = conn.execute(
        "select e.points, e.reason, e.created_at, r.site_id from points_events e left join reports r on r.id = e.report_id"
        " where e.user_id = %s order by e.created_at desc, e.id desc limit 20",
        (user_id,),
    ).fetchall()
    active = conn.execute(
        "select e.reason, r.created_at from points_events e join reports r on r.id = e.report_id"
        " where e.user_id = %s and e.reason in ('report', 'challenge') and e.points > 0 and not exists ("
        "select 1 from points_events x where x.report_id = e.report_id and x.reason = 'reversal:' || e.reason)",
        (user_id,),
    ).fetchall()
    weeks = {week_key(r["created_at"]) for r in active if r["reason"] == "report"}
    done = any(r["reason"] == "challenge" and this_week <= r["created_at"] < this_week + timedelta(days=7) for r in active)
    ch = challenge_for(now)
    return {
        "points": summary["total"],
        "points_this_week": summary["week"],
        "rank": summary["rank"],
        "streak_weeks": _streak_length(weeks, now) or _streak_length(weeks, now - timedelta(days=7)),
        "badges": [
            {"key": k, "title": t, "description": d, "earned": k in earned,
             "awarded_at": earned[k].isoformat() if k in earned else None}
            for k, (t, d) in BADGES.items()
        ],
        "challenge": {**ch, "done": done},
        "recent": [{**_line(e["reason"].removeprefix("reversal:"), e["points"]), "created_at": e["created_at"].isoformat(),
                    "site_id": e["site_id"], "reversed": e["reason"].startswith("reversal:")} for e in recent],
    }


def rank_of(conn: psycopg.Connection, user_id: str) -> int | None:
    """All-time rank (1 = most points) among people with points, or None if the person has none."""
    row = conn.execute(
        "select rank from (select user_id, rank() over (order by sum(points) desc) as rank from points_events"
        " group by user_id having sum(points) > 0) t where user_id = %s",
        (user_id,),
    ).fetchone()
    return row["rank"] if row else None


def leaderboard(
    conn: psycopg.Connection,
    viewer_id: str | None,
    *,
    scope: str = "all",
    city: str | None = None,
    limit: int = 25,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Top people by points. Only people who chose to appear are listed, by nickname. scope: all | week | month."""
    now = now or datetime.now(UTC)
    since = {"all": None, "week": week_start(now), "month": now - timedelta(days=30)}.get(scope)
    where, params = ["1=1"], []
    if since is not None:
        where.append("e.created_at >= %s")
        params.append(since)
    if city:
        where.append("r.city = %s")
        params.append(city)
    rows = conn.execute(
        f"""
        select t.*, p.nickname, p.show_on_leaderboard,
               (select count(*) from badges_awarded b where b.user_id = t.user_id) as badges
        from (
            select e.user_id, sum(e.points) as points,
                   count(*) filter (where e.reason = 'report' and e.points > 0) as reports,
                   rank() over (order by sum(e.points) desc) as rank
            from points_events e left join reports r on r.id = e.report_id
            where {' and '.join(where)}
            group by e.user_id having sum(e.points) > 0
        ) t join profiles p on p.user_id = t.user_id
        order by t.rank, p.nickname
        """,
        params,
    ).fetchall()
    shown = [r for r in rows if r["show_on_leaderboard"]]
    mine = next((r for r in rows if r["user_id"] == viewer_id), None)
    return {
        "scope": scope,
        "city": city,
        "entries": [
            {"rank": r["rank"], "nickname": r["nickname"], "points": r["points"], "reports": r["reports"],
             "badges": r["badges"], "is_me": r["user_id"] == viewer_id}
            for r in shown[: max(1, min(limit, 100))]
        ],
        "me": {"rank": mine["rank"], "points": mine["points"], "listed": bool(mine["show_on_leaderboard"])} if mine else None,
    }
