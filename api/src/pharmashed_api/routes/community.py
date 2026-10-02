"""Community routes (S5 phase 1): sign-in status, the signed-in user, and their profile."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator

from pharmashed_api.assistant import loop
from pharmashed_api.assistant.limits import limiter
from pharmashed_api.community import auth, db, photos, points, profiles, proofread, reports, storage

log = logging.getLogger(__name__)
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
    return {"enabled": database and sign_in, "database": database, "auth": sign_in, "photos": storage.is_configured()}


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
    note_clean: str | None = None
    photo_id: str | None = None


@router.post("/reports", status_code=201, dependencies=[Depends(require_database)])
def create_report(body: ReportIn, user: auth.AuthUser = auth.CurrentUser) -> dict:
    """File a report. The person needs a nickname first, so the map can credit them."""
    try:
        with db.connection() as conn:
            if profiles.get_profile(conn, user.id) is None:
                raise HTTPException(409, "Choose a nickname before filing a report.")
            return reports.create_report(
                conn, user.id, lat=body.lat, lon=body.lon, observed_at=body.observed_at,
                checklist=body.checklist, note=body.note, note_clean=body.note_clean,
                photo_id=body.photo_id,
            )
    except (reports.InvalidReport, photos.InvalidPhoto) as e:
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


class ProofreadIn(BaseModel):
    note: str = Field(max_length=reports.NOTE_MAX)


@router.post("/ai/proofread")
def ai_proofread(body: ProofreadIn, user: auth.AuthUser = auth.CurrentUser) -> dict:
    """Suggest a tidied version of a report note and warn about personal details. Needs sign-in; rate limited."""
    if loop.provider() is None:
        raise HTTPException(503, "The note helper is not available right now. You can still send your note as it is.")
    if body.note.strip():  # an empty note costs nothing, so it does not use the allowance
        refusal = limiter.check(f"proofread:{user.id}")
        if refusal:
            raise HTTPException(429, refusal)
    try:
        return proofread.proofread(body.note)
    except reports.InvalidReport as e:
        raise HTTPException(422, str(e)) from None
    except Exception:
        log.exception("proofread failed")
        raise HTTPException(502, "The note helper could not answer. You can still send your note as it is.") from None


@router.post("/photos", status_code=201, dependencies=[Depends(require_database)])
async def upload_photo(file: UploadFile = File(...), user: auth.AuthUser = auth.CurrentUser) -> dict:
    """Upload one photo (checked, resized, stored). Attach it by sending its id when filing the report."""
    if not storage.is_configured():
        raise HTTPException(503, "Photos are not set up on this server. You can still send a report without one.")
    raw = await file.read(photos.MAX_UPLOAD_BYTES + 1)
    try:
        with db.connection() as conn:
            return photos.save_upload(conn, user.id, raw)
    except photos.InvalidPhoto as e:
        raise HTTPException(422, str(e)) from None
    except photos.TooManyUploads:
        raise HTTPException(429, "You have uploaded a lot of photos today. Please try again tomorrow.") from None
    except Exception:
        log.exception("photo upload failed")
        raise HTTPException(502, "The photo could not be saved. You can still send a report without it.") from None


@router.get("/photos/{photo_id}", dependencies=[Depends(require_database)])
def get_photo(photo_id: uuid.UUID) -> RedirectResponse:
    """Redirect to a short-lived link for a photo. Only photos on approved reports are available."""
    with db.connection() as conn:
        key = photos.public_key(conn, str(photo_id))
    if key is None:
        raise HTTPException(404, "No such photo.")
    return RedirectResponse(storage.presigned_get(key), status_code=302, headers={"Cache-Control": "private, max-age=60"})


@router.get("/me/progress", dependencies=[Depends(require_database)])
def my_progress(user: auth.AuthUser = auth.CurrentUser) -> dict:
    """Points, rank, streak, badges, this week's challenge and recent point events for the signed-in person."""
    with db.connection() as conn:
        return points.progress(conn, user.id)


@router.get("/challenge", dependencies=[Depends(require_database)])
def challenge() -> dict:
    """This week's challenge (public)."""
    return points.challenge_for(datetime.now(UTC))


@router.get("/leaderboard", dependencies=[Depends(require_database)])
def leaderboard(
    scope: str = Query("all", pattern="^(all|week|month)$"),
    city: str | None = Query(None, pattern="^(TLS|GNT|BNV|CBR|OSL)$"),
    limit: int = Query(25, ge=1, le=100),
    user: auth.AuthUser | None = auth.OptionalUser,
) -> dict:
    """Top people by points, by nickname, for everyone or one city, all time, this week or the last 30 days."""
    with db.connection() as conn:
        return points.leaderboard(conn, user.id if user else None, scope=scope, city=city, limit=limit)
