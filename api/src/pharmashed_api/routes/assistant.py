"""Assistant routes (M17): ask a question, and check whether the assistant is configured."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pharmashed_api.assistant import loop

router = APIRouter()

# Site ids look like "TLS-01"; drug names are lowercase words. The pattern keeps free text
# out of the system prompt, since these values are interpolated into it.
_ID_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"


class AssistantContext(BaseModel):
    """The site (and optionally drug) the user has open in the app."""

    site_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    drug: str | None = Field(default=None, pattern=_ID_PATTERN)


class AssistantRequest(BaseModel):
    question: str = Field(max_length=2000)
    context: AssistantContext | None = None


@router.get("/assistant/status")
def assistant_status() -> dict:
    """Whether an API key is configured, and which provider and model would answer.

    Lets the UI check availability without spending a model call.
    """
    prov = loop.provider()
    return {
        "available": prov is not None,
        "provider": prov,
        "model": loop.model_name(prov) if prov else None,
    }


@router.post("/assistant")
def assistant(req: AssistantRequest) -> dict:
    if loop.provider() is None:
        raise HTTPException(
            503,
            "No assistant API key configured — set OPENAI_API_KEY (or GROQ_API_KEY) to enable the assistant.",
        )
    context = req.context.model_dump() if req.context else None
    return loop.run(req.question, context)
