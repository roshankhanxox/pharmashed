"""Community routes (S5 phase 1): sign-in status, the signed-in user, and their profile."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from pharmashed_api.community import auth, db, profiles, reports

router = APIRouter()


def require_database() -> None:
    """503 with a clear message when no database is configured or it cannot be reached."""
    if not db.is_configured():
        raise HTTPException(503, "Citizen reports are not set up on this server (no database).")


class ProfileIn(BaseModel):
    nickname: str
    show_on_leaderboard: bool = True
    home_city: str | None = None

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, value: str) -> str:
        return profiles.validate_nickname(value)

    @field_validator("home_city")
    @classmethod
    def _home_city(cls, value: str | None) -> str | None:
        return profiles.validate_city(value)


@router.get("/community/status")
def community_status() -> dict:
    """Which parts of the community features are configured, so the UI can hide what is unavailable."""
    database, sign_in = db.is_configured(), auth.auth_configured()
    return {"enabled": database and sign_in, "database": database, "auth": sign_in}


@router.get("/me", dependencies=[Depends(require_database)])
def me(user: auth.AuthUser = auth.CurrentUser) -> dict:
    """The signed-in user and their profile (null until they choose a nickname)."""
    with db.connection() as conn:
        profile = profiles.get_profile(conn, user.id)
    return {"user": {"name": user.name}, "profile": profile, "is_admin": user.is_admin}


@router.put("/me/profile", dependencies=[Depends(require_database)])
def save_profile(body: ProfileIn, user: auth.AuthUser = auth.CurrentUser) -> dict:
    """Create or update the signed-in user's profile."""
    try:
        with db.connection() as conn:
            return profiles.save_profile(
                conn, user.id, body.nickname, body.show_on_leaderboard, body.home_city
            )
    except profiles.NicknameTaken:
        raise HTTPException(409, "That nickname is taken. Please pick another.") from None


class ReportIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    observed_at: datetime
    checklist: dict[str, Any]
    note: str | None = None


@router.post("/reports", status_code=201, dependencies=[Depends(require_database)])
def create_report(body: ReportIn, user: auth.AuthUser = auth.CurrentUser) -> dict:
    """File a report. The person needs a nickname first, so the map can credit them."""
    try:
        with db.connection() as conn:
            if profiles.get_profile(conn, user.id) is None:
                raise HTTPException(409, "Choose a nickname before filing a report.")
            return reports.create_report(
                conn, user.id, lat=body.lat, lon=body.lon, observed_at=body.observed_at,
                checklist=body.checklist, note=body.note,
            )
    except reports.InvalidReport as e:
        raise HTTPException(422, str(e)) from None
    except reports.TooManyReports:
        raise HTTPException(429, "You have filed a lot of reports today. Please try again tomorrow.") from None


@router.get("/reports", dependencies=[Depends(require_database)])
def list_reports(
    site_id: str | None = None,
    city: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    user: auth.AuthUser | None = auth.OptionalUser,
) -> list[dict]:
    """Approved reports, newest visit first. Public: no sign-in needed to read."""
    with db.connection() as conn:
        return reports.list_reports(conn, user.id if user else None, site_id=site_id, city=city, limit=limit)


@router.get("/me/reports", dependencies=[Depends(require_database)])
def my_reports(user: auth.AuthUser = auth.CurrentUser) -> list[dict]:
    """The signed-in person's own reports, whatever their status."""
    with db.connection() as conn:
        return reports.my_reports(conn, user.id)
