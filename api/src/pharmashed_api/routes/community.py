"""Community routes (S5 phase 1): sign-in status, the signed-in user, and their profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from pharmashed_api.community import auth, db, profiles

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
