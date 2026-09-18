"""Scoring, tiers and ranking (M10).

Pure functions over draw arrays. No I/O.
"""

from __future__ import annotations

import numpy as np

from pharmashed.contracts import (
    CitySummary,
    Histogram,
    SiteOverall,
    Tier,
)

# Tier boundaries (D09)
_TIER_HIGH = 0.5
_TIER_MEDIUM = 0.1


def score(rq_arr: np.ndarray) -> float:
    """Sampling priority score = fraction of draws with RQ > 1.

    Args:
        rq_arr: RQ draws, shape (N,).

    Returns:
        Float in [0, 1]. Never call this a probability (D08).
    """
    return float(np.mean(rq_arr > 1.0))


def lod_share(pec_arr: np.ndarray, lod: float) -> float:
    """Fraction of draws where PEC exceeds the limit of detection.

    Args:
        pec_arr: PEC draws in ng/L.
        lod: detection limit in ng/L.

    Returns:
        Float in [0, 1].
    """
    return float(np.mean(pec_arr > lod))


def tier(s: float) -> Tier:
    """Assign a tier from a sampling priority score (D09).

    Boundaries: high ≥ 0.5, medium ≥ 0.1, else low.

    Args:
        s: sampling priority score in [0, 1].

    Returns:
        "high", "medium", or "low".
    """
    if s >= _TIER_HIGH:
        return "high"
    if s >= _TIER_MEDIUM:
        return "medium"
    return "low"


def rank_in_city(results: list, city: str, drug: str) -> tuple[int, int]:
    """Return (rank, n_in_city) for a (city, drug) pair sorted by score desc.

    Ties broken by RQ p50 descending.

    Args:
        results: list of objects with .site_id, .city (str parsed from site_id),
            .drug, .score, .rq_p50 attributes.
        city: three-letter city code.
        drug: drug name.

    Returns:
        (1-based rank, n sites with the same drug in this city).
    """
    city_drug = [r for r in results if r["city"] == city and r["drug"] == drug]
    city_drug.sort(key=lambda r: (-r["score"], -r["rq_p50"]))
    n = len(city_drug)
    for i, r in enumerate(city_drug, start=1):
        if r["site_id"] == r["site_id"]:  # always true — locate via identity
            pass
    # Return mapping
    return {r["site_id"]: (i + 1, n) for i, r in enumerate(city_drug)}, n


def compute_ranks(flat: list[dict]) -> dict[tuple[str, str], dict[str, tuple[int, int]]]:
    """Compute ranks for all (city, drug) pairs at once.

    Args:
        flat: list of dicts with keys site_id, city, drug, score, rq_p50.

    Returns:
        Mapping (city, drug) → {site_id: (rank, n_in_city)}.
    """
    from collections import defaultdict  # noqa: PLC0415
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in flat:
        groups[(r["city"], r["drug"])].append(r)

    out: dict[tuple[str, str], dict[str, tuple[int, int]]] = {}
    for (city, drug), group in groups.items():
        group.sort(key=lambda r: (-r["score"], -r["rq_p50"]))
        n = len(group)
        out[(city, drug)] = {r["site_id"]: (i + 1, n) for i, r in enumerate(group)}
    return out


def site_overall(flat: list[dict]) -> list[SiteOverall]:
    """For each site: max score over drugs, top drug, rank within city.

    Args:
        flat: list of dicts with site_id, city, drug, score, rank_in_city.

    Returns:
        List of SiteOverall, one per site.
    """
    from collections import defaultdict  # noqa: PLC0415
    by_site: dict[str, list[dict]] = defaultdict(list)
    for r in flat:
        by_site[r["site_id"]].append(r)

    site_rows: list[dict] = []
    for site_id, rows in by_site.items():
        best = max(rows, key=lambda r: (r["score"], r["rq_p50"]))
        site_rows.append({
            "site_id": site_id,
            "score": best["score"],
            "top_drug": best["drug"],
            "city": best["city"],
        })

    # rank within city by max score
    city_groups: dict[str, list[dict]] = defaultdict(list)
    for r in site_rows:
        city_groups[r["city"]].append(r)

    result: list[SiteOverall] = []
    for city, group in city_groups.items():
        group.sort(key=lambda r: -r["score"])
        for i, r in enumerate(group, start=1):
            result.append(SiteOverall(
                site_id=r["site_id"],
                score=r["score"],
                top_drug=r["top_drug"],
                rank_in_city=i,
            ))
    return result


def city_summary(overalls: list[SiteOverall]) -> list[CitySummary]:
    """Count tier distribution per city based on site_overall scores.

    Args:
        overalls: list of SiteOverall (from site_overall()).

    Returns:
        List of CitySummary, one per city.
    """
    from collections import defaultdict  # noqa: PLC0415
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"high": 0, "medium": 0, "low": 0})

    for o in overalls:
        city = o.site_id[:3]
        t = tier(o.score)
        counts[city][t] += 1

    return [
        CitySummary(city=c, high=v["high"], medium=v["medium"], low=v["low"])
        for c, v in sorted(counts.items())
    ]


def histogram(rq_arr: np.ndarray, bins: int = 40) -> Histogram:
    """Log10 histogram of RQ draws over the [p0.1, p99.9] range.

    Args:
        rq_arr: RQ draws.
        bins: number of bins (default 40).

    Returns:
        Histogram with log10_edges (bins+1 values) and counts (bins values).
    """
    # Clamp to > 0 for log10
    positive = rq_arr[rq_arr > 0]
    if len(positive) == 0:
        edges = list(np.linspace(-3, 1, bins + 1))
        return Histogram(log10_edges=edges, counts=[0] * bins)

    lo = float(np.percentile(positive, 0.1))
    hi = float(np.percentile(positive, 99.9))
    lo = max(lo, 1e-6)
    hi = max(hi, lo * 10)

    edges = list(np.linspace(np.log10(lo), np.log10(hi), bins + 1))
    counts_arr, _ = np.histogram(np.log10(np.clip(rq_arr, 1e-10, None)), bins=edges)
    return Histogram(log10_edges=edges, counts=list(counts_arr.astype(int)))
