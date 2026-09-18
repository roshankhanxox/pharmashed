"""Scenario endpoint (M16).

Server-side scenario math — same closed-form as the client (D13):
  RQ' = RQ · mλ · mC / mQ
"""

from __future__ import annotations

import statistics
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pharmashed_api import data as _data

router = APIRouter()


class ScenarioRequest(BaseModel):
    site_id: str
    drug: str
    multipliers: dict[str, float] = Field(default_factory=lambda: {"lambda": 1.0, "Q": 1.0, "C": 1.0})


class ScenarioResponse(BaseModel):
    site_id: str
    drug: str
    score: float
    tier: str
    rq_quantiles: dict[str, float]
    multipliers: dict[str, float]


def _tier(s: float) -> str:
    if s >= 0.5:
        return "high"
    if s >= 0.1:
        return "medium"
    return "low"


@router.post("/scenario", response_model=ScenarioResponse)
def scenario(req: ScenarioRequest) -> ScenarioResponse:
    draws = _data.draws_for(req.site_id, req.drug)
    if draws is None:
        raise HTTPException(
            404,
            f"No stored draws for site={req.site_id!r} drug={req.drug!r}",
        )

    m_lam = req.multipliers.get("lambda", 1.0)
    m_q   = req.multipliers.get("Q", 1.0)
    m_c   = req.multipliers.get("C", 1.0)

    if m_q <= 0:
        raise HTTPException(422, "Q multiplier must be > 0")

    # D13: RQ' = RQ · mλ · mC / mQ (valid for w=0)
    scale = (m_lam * m_c) / m_q
    scaled = [rq * scale for rq in draws]

    n = len(scaled)
    score = sum(1 for rq in scaled if rq > 1.0) / n
    sorted_draws = sorted(scaled)

    def pct(p: float) -> float:
        idx = max(0, min(n - 1, int(p / 100 * n)))
        return round(sorted_draws[idx], 6)

    return ScenarioResponse(
        site_id=req.site_id,
        drug=req.drug,
        score=round(score, 6),
        tier=_tier(score),
        rq_quantiles={"p5": pct(5), "p50": pct(50), "p95": pct(95)},
        multipliers=req.multipliers,
    )
