"""Model core — vectorised A4 equations (M07).

All functions are pure: no I/O, no global state. Every parameter is in the
units listed in A4 (g, ng/L, m³/s, h, DDD/1000-inh/day, persons).
"""

from __future__ import annotations

from typing import Literal

import numpy as np

Variant = Literal["full", "wwtp_only", "pop_only"]


def pec_ng_l(
    P: np.ndarray | float,
    C: np.ndarray | float,
    ddd_g: np.ndarray | float,
    fe: np.ndarray | float,
    lam: np.ndarray | float,
    w: int,
    R: np.ndarray | float,
    Q_m3s: np.ndarray | float,
    k_per_h: np.ndarray | float,
    tau_h: np.ndarray | float,
) -> np.ndarray:
    """Predicted environmental concentration at a site, in ng/L.

    Implements A4 exactly:
        L = P · C · DDD / 1000          (g/day consumed near site)
        E = L · fe                       (g/day excreted as parent)
        M = E · (λ + w·(1−λ)·(1−R))     (g/day entering stream)
        Qd = Q · 86400 · 1000           (m³/s → L/day)
        PEC = M / Qd · exp(−k·τ) · 1e9  (ng/L)

    Args:
        P: population within buffer (persons).
        C: consumption in DDD / 1000 inhabitants / day.
        ddd_g: defined daily dose in grams.
        fe: fraction excreted unchanged [0, 1].
        lam: untreated fraction λ [0, 1].
        w: WWTP flag (0 = no outfall, 1 = outfall). All MVP sites have w=0.
        R: WWTP removal efficiency [0, 1]. Ignored when w=0.
        Q_m3s: stream flow in m³/s.
        k_per_h: in-stream first-order loss rate in 1/h.
        tau_h: travel time in hours.

    Returns:
        PEC array in ng/L, same shape as the broadcast of the inputs.
    """
    L = P * C * ddd_g / 1000.0
    E = L * fe
    M = E * (lam + w * (1.0 - lam) * (1.0 - R))
    Qd = Q_m3s * 86400.0 * 1000.0
    return M / Qd * np.exp(-k_per_h * tau_h) * 1e9


def rq(pec: np.ndarray, pnec: np.ndarray | float) -> np.ndarray:
    """Risk quotient: PEC / PNEC (dimensionless).

    Args:
        pec: PEC array in ng/L.
        pnec: PNEC value or array in ng/L.

    Returns:
        RQ array, same shape as pec.
    """
    return pec / pnec


def apply_variant(
    inputs: dict[str, np.ndarray | float],
    variant: Variant,
    cross_country_mean_C: float,
) -> dict[str, np.ndarray | float]:
    """Return a modified copy of inputs for the requested model variant.

    Variants (D24):
        full       — no change (the default).
        wwtp_only  — sets λ=0, so PEC=0 for all w=0 sites. Mirrors the ePiE
                     blind spot: streams without a WWTP outfall appear clean.
        pop_only   — replaces C with the cross-country mean for this drug,
                     removing country-specific consumption signal.

    Args:
        inputs: dict produced by the Monte Carlo runner (site + drug draws).
        variant: one of "full", "wwtp_only", "pop_only".
        cross_country_mean_C: mean consumption value across all countries for
            this drug, in DDD/1000 inh/day.

    Returns:
        A shallow copy of ``inputs`` with the relevant field overridden.
    """
    if variant == "full":
        return inputs
    out = dict(inputs)
    if variant == "wwtp_only":
        n = np.asarray(inputs["lambda"]).shape[0] if hasattr(inputs["lambda"], "__len__") else 1
        out["lambda"] = np.zeros(n) if n > 1 else 0.0
    elif variant == "pop_only":
        n = np.asarray(inputs["C"]).shape[0] if hasattr(inputs.get("C", 0.0), "__len__") else 1
        out["C"] = np.full(n, cross_country_mean_C) if n > 1 else cross_country_mean_C
    else:
        raise ValueError(f"Unknown variant: {variant!r}")
    return out
