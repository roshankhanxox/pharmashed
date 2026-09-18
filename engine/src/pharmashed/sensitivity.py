"""Sensitivity analysis: drivers and flip thresholds (M09).

Spearman rank correlations between sampled inputs and RQ → top drivers.
Closed-form flip multipliers for w=0 sites (per A4 and D13).
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from pharmashed.contracts import Driver, Flip, FlipStep, Tier

# Map internal key → (glossary symbol, plain name)
_PARAM_GLOSSARY: dict[str, tuple[str, str]] = {
    "lambda":    ("λ", "leakage"),
    "Q_m3s":     ("Q", "stream flow"),
    "C":         ("C", "consumption"),
    "fe":        ("fe", "excretion fraction"),
    "k_per_h":   ("k", "in-stream loss rate"),
    "tau_h":     ("τ", "travel time"),
    "ddd_g":     ("DDD", "daily dose"),
    "pnec_ng_l": ("PNEC", "no-effect threshold"),
}

_TOP_N = 5


def spearman_drivers(
    inputs: dict[str, np.ndarray],
    rq_arr: np.ndarray,
) -> list[Driver]:
    """Compute Spearman ρ between each input and RQ; return top drivers.

    Inputs with zero variance (fixed distributions) are skipped.

    Args:
        inputs: sampled input arrays, keyed by param name.
        rq_arr: RQ draws of the same length.

    Returns:
        Up to _TOP_N Driver objects sorted by |ρ| descending.
    """
    drivers: list[Driver] = []
    for key in _PARAM_GLOSSARY:
        arr = inputs.get(key)
        if arr is None:
            continue
        if np.std(arr) == 0:
            continue  # fixed dist — no information
        rho, _ = stats.spearmanr(arr, rq_arr)
        if np.isnan(rho):
            continue
        drivers.append(Driver(param=key, rho=float(rho)))

    drivers.sort(key=lambda d: abs(d.rho), reverse=True)
    return drivers[:_TOP_N]


def driver_sentence(drivers: list[Driver]) -> str:
    """Produce a one-sentence natural-language summary of the top two drivers.

    Uses glossary names (D10, §7).
    """
    if not drivers:
        return "No variable inputs."
    sym1, name1 = _PARAM_GLOSSARY.get(drivers[0].param, (drivers[0].param, drivers[0].param))
    if len(drivers) < 2:
        return f"Driven by {name1} ({sym1})."
    sym2, name2 = _PARAM_GLOSSARY.get(drivers[1].param, (drivers[1].param, drivers[1].param))
    return f"Mostly driven by {name1} ({sym1}); {name2} ({sym2}) second."


def _score_from_rq(rq_arr: np.ndarray) -> float:
    return float(np.mean(rq_arr > 1.0))


def _tier_of(score: float) -> Tier:
    if score >= 0.5:
        return "high"
    if score >= 0.1:
        return "medium"
    return "low"


def flip_thresholds(
    rq_arr: np.ndarray,
    inputs: dict[str, np.ndarray],
) -> Flip | None:
    """Compute the multiplier required to change the sampling-priority tier.

    Uses the closed-form shortcut valid for w=0 (D13):
        score(m) = P(RQ · m > 1) = P(RQ > 1/m)

    The multiplier is expressed on whichever of {λ, Q} is the top driver
    (Q multiplier is reported as 1/m because larger Q lowers PEC).

    Args:
        rq_arr: RQ draws (N_DRAWS,).
        inputs: sampled input arrays (used to identify top driver).

    Returns:
        Flip object, or None if the tier cannot be changed within [0.01, 100].
    """
    current_score = _score_from_rq(rq_arr)
    current_tier = _tier_of(current_score)

    # target score thresholds for tier changes
    targets: list[tuple[str, float]] = []
    if current_tier == "high":
        targets = [("down", 0.5)]          # high→medium: score drops below 0.5
    elif current_tier == "medium":
        targets = [("up", 0.5), ("down", 0.1)]   # up→high, down→low
    else:  # low
        targets = [("up", 0.1)]            # low→medium

    # identify top driver among {lambda, Q_m3s}
    top_key = "lambda"
    lam_std = float(np.std(inputs.get("lambda", np.array([0.0]))))
    q_std = float(np.std(inputs.get("Q_m3s", np.array([0.0]))))
    if q_std > lam_std:
        top_key = "Q_m3s"

    flip_map: dict[str, FlipStep | None] = {"up": None, "down": None}

    for direction, target_score in targets:
        # P(RQ > 1/m) = target_score  →  quantile of RQ at (1 - target_score) = 1/m
        # → m = 1 / quantile(RQ, 1 - target_score)
        q_level = 1.0 - target_score
        rq_quantile = float(np.quantile(rq_arr, q_level))
        if rq_quantile == 0:
            continue
        m = 1.0 / rq_quantile

        # direction sanity: up → m > 1; down → m < 1
        if direction == "up" and m <= 1.0:
            continue
        if direction == "down" and m >= 1.0:
            continue
        if not (0.01 <= m <= 100.0):
            continue

        # Report as λ multiplier or Q multiplier (inverse for Q since Q ↑ → PEC ↓)
        if top_key == "Q_m3s":
            param_label = "Q"
            reported_m = 1.0 / m
            if not (0.01 <= reported_m <= 100.0):
                continue
        else:
            param_label = "lambda"
            reported_m = m

        target_tier: Tier = _tier_of(target_score + (0.001 if direction == "up" else -0.001))
        flip_map[direction] = FlipStep(
            param=param_label, multiplier=round(reported_m, 3), to_tier=target_tier
        )

    if flip_map["up"] is None and flip_map["down"] is None:
        return None

    return Flip(up=flip_map["up"], down=flip_map["down"])
