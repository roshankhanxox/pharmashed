"""Assistant route (M17)."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AssistantRequest(BaseModel):
    question: str


@router.post("/assistant")
def assistant(req: AssistantRequest) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            503,
            "ANTHROPIC_API_KEY not configured — assistant unavailable in static demo mode.",
        )
    from pharmashed_api.assistant.loop import run  # noqa: PLC0415

    return run(req.question)
