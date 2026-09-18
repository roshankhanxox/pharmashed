"""Assistant tool implementations (M17).

Each function maps directly to a tool the assistant can call.
All data comes from build artifacts — no computation here.
"""

from __future__ import annotations

from pharmashed_api import data as _data


def list_priority_sites(
    city: str | None = None,
    drug: str | None = None,
    limit: int = 5,
) -> dict:
    """Return sites ranked by sampling priority score.

    Args:
        city: three-letter city code (TLS/GNT/BNV/CBR/OSL) or None for all.
        drug: drug name or None for site_overall (max score across drugs).
        limit: max sites to return.

    Returns:
        Dict with 'sites' list and 'city'/'drug' context.
    """
    results = _data.results()
    if drug:
        entries = results.get("results", [])
        if city:
            entries = [e for e in entries if e["site_id"].startswith(city)]
        entries = [e for e in entries if e["drug"] == drug]
        entries.sort(key=lambda e: (-e["score"], -e["rq"]["p50"]))
        out = [
            {
                "site_id": e["site_id"],
                "drug": e["drug"],
                "score": e["score"],
                "tier": e["tier"],
                "rank_in_city": e["rank_in_city"],
                "n_in_city": e["n_in_city"],
                "driver_sentence": e.get("driver_sentence", ""),
            }
            for e in entries[:limit]
        ]
    else:
        overalls = results.get("site_overall", [])
        if city:
            overalls = [o for o in overalls if o["site_id"].startswith(city)]
        overalls.sort(key=lambda o: (-o["score"], o["site_id"]))
        out = [
            {
                "site_id": o["site_id"],
                "top_drug": o["top_drug"],
                "score": o["score"],
                "rank_in_city": o["rank_in_city"],
            }
            for o in overalls[:limit]
        ]

    return {"sites": out, "city": city, "drug": drug, "limit": limit}


def get_site_profile(site_id: str) -> dict:
    """Return all drug results for one site.

    Args:
        site_id: site identifier.

    Returns:
        Dict with site metadata and per-drug summaries.
    """
    results = _data.results()
    entries = [e for e in results.get("results", []) if e["site_id"] == site_id]

    # Site from sites.json
    sites_doc = _data.sites()
    site = next(
        (s for s in sites_doc.get("sites", []) if s["id"] == site_id),
        None,
    )

    drugs = []
    for e in sorted(entries, key=lambda e: -e["score"]):
        drugs.append({
            "drug": e["drug"],
            "score": e["score"],
            "tier": e["tier"],
            "pec_p50_ng_l": e["pec_ng_l"]["p50"],
            "rq_p50": e["rq"]["p50"],
            "rank_in_city": e["rank_in_city"],
            "n_in_city": e["n_in_city"],
        })

    return {
        "site_id": site_id,
        "name": site.get("name", site_id) if site else site_id,
        "city": site.get("city", site_id[:3]) if site else site_id[:3],
        "size_class": site.get("size_class", "?") if site else "?",
        "population_buffer": site.get("population_buffer", 0) if site else 0,
        "valid": site.get("valid", True) if site else True,
        "drugs": drugs,
    }


def explain_drivers(site_id: str, drug: str) -> dict:
    """Return sensitivity drivers and flip thresholds for one (site, drug).

    Args:
        site_id: site identifier.
        drug: drug name.

    Returns:
        Dict with drivers, driver_sentence, flip, and score context.
    """
    results = _data.results()
    entry = next(
        (e for e in results.get("results", [])
         if e["site_id"] == site_id and e["drug"] == drug),
        None,
    )
    if entry is None:
        return {"error": f"No results found for site={site_id!r} drug={drug!r}"}

    flip = entry.get("flip", {})
    return {
        "site_id": site_id,
        "drug": drug,
        "score": entry["score"],
        "tier": entry["tier"],
        "drivers": entry.get("drivers", []),
        "driver_sentence": entry.get("driver_sentence", ""),
        "flip": {
            "up": flip.get("up"),
            "down": flip.get("down"),
        },
        "note": "Drivers are Spearman ρ between sampled inputs and RQ. All values under stated priors.",
    }


def run_scenario(
    site_id: str,
    drug: str,
    multipliers: dict[str, float] | None = None,
) -> dict:
    """Apply scenario multipliers to stored draws and return revised scores.

    Args:
        site_id: site identifier.
        drug: drug name.
        multipliers: dict with optional 'lambda', 'Q', 'C' keys (default 1.0).

    Returns:
        Dict with baseline and scenario scores, quantiles, tier.
    """
    m = multipliers or {}
    m_lam = float(m.get("lambda", 1.0))
    m_q   = float(m.get("Q", 1.0))
    m_c   = float(m.get("C", 1.0))

    if m_q <= 0:
        return {"error": "Q multiplier must be > 0"}

    draws = _data.draws_for(site_id, drug)
    if draws is None:
        return {"error": f"No stored draws for site={site_id!r} drug={drug!r}"}

    n = len(draws)
    # Baseline on the same 1000 draws
    base_score = sum(1 for rq in draws if rq > 1.0) / n

    scale = (m_lam * m_c) / m_q
    scaled = [rq * scale for rq in draws]
    scen_score = sum(1 for rq in scaled if rq > 1.0) / n

    def pct(lst: list[float], p: float) -> float:
        idx = max(0, min(n - 1, int(p / 100 * n)))
        return round(sorted(lst)[idx], 4)

    def tier_label(s: float) -> str:
        return "high" if s >= 0.5 else ("medium" if s >= 0.1 else "low")

    return {
        "site_id": site_id,
        "drug": drug,
        "baseline": {
            "score": round(base_score, 4),
            "tier": tier_label(base_score),
            "rq_p50": pct(draws, 50),
        },
        "scenario": {
            "score": round(scen_score, 4),
            "tier": tier_label(scen_score),
            "rq_p50": pct(scaled, 50),
            "multipliers": {"lambda": m_lam, "Q": m_q, "C": m_c},
        },
        "note": "Recomputed on 1,000 stored draws. Scenario score may differ slightly from results.json baseline (computed on all draws).",
    }


def get_provenance(key: str) -> dict:
    """Return provenance for a parameter key.

    Args:
        key: provenance key, e.g. 'param:irbesartan:pnec_ng_l'.

    Returns:
        Provenance entry dict or error.
    """
    prov = _data.provenance()
    if key not in prov:
        # Try partial key match
        matches = [k for k in prov if key in k]
        if len(matches) == 1:
            return {"key": matches[0], **prov[matches[0]]}
        if matches:
            return {"error": f"Ambiguous key {key!r}. Matches: {matches[:5]}"}
        return {"error": f"Provenance key {key!r} not found"}
    return {"key": key, **prov[key]}


# Tool schemas for the Anthropic API
TOOL_SCHEMAS = [
    {
        "name": "list_priority_sites",
        "description": "List sites ranked by sampling priority score. Use city and/or drug to narrow. Returns score, tier, rank, and the top driver sentence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Three-letter city code: TLS, GNT, BNV, CBR, OSL. Omit for all cities."},
                "drug": {"type": "string", "description": "Drug name (lowercase INN). Omit to show site_overall (max score across drugs)."},
                "limit": {"type": "integer", "description": "Max sites to return (default 5)."},
            },
            "required": [],
        },
    },
    {
        "name": "get_site_profile",
        "description": "Return all drug scores, ranks, and PEC p50 for a single site.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "description": "Site identifier, e.g. TLS-001."},
            },
            "required": ["site_id"],
        },
    },
    {
        "name": "explain_drivers",
        "description": "Return the sensitivity drivers (Spearman rho per parameter) and flip-threshold multipliers for one site-drug pair.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string"},
                "drug": {"type": "string"},
            },
            "required": ["site_id", "drug"],
        },
    },
    {
        "name": "run_scenario",
        "description": "Apply multipliers (lambda, Q, C) to stored draws and return the revised sampling priority score and tier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string"},
                "drug": {"type": "string"},
                "multipliers": {
                    "type": "object",
                    "description": "Optional overrides: lambda (leakage multiplier), Q (flow multiplier), C (consumption multiplier).",
                    "properties": {
                        "lambda": {"type": "number"},
                        "Q": {"type": "number"},
                        "C": {"type": "number"},
                    },
                },
            },
            "required": ["site_id", "drug"],
        },
    },
    {
        "name": "get_provenance",
        "description": "Return the provenance entry for a parameter key (source, value, status, distribution).",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Provenance key, e.g. 'param:irbesartan:pnec_ng_l' or 'prior:lambda'."},
            },
            "required": ["key"],
        },
    },
]


def _anthropic_to_openai(schema: dict) -> dict:
    """Convert one Anthropic tool schema to OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }


TOOL_SCHEMAS_OPENAI = [_anthropic_to_openai(s) for s in TOOL_SCHEMAS]

TOOL_FN_MAP = {
    "list_priority_sites": list_priority_sites,
    "get_site_profile": get_site_profile,
    "explain_drivers": explain_drivers,
    "run_scenario": run_scenario,
    "get_provenance": get_provenance,
}
