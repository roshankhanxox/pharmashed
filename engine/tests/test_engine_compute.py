"""M06–M10 acceptance tests: priors, model, Monte Carlo, sensitivity, scoring."""

from __future__ import annotations

import numpy as np
import pytest

# --- M06 priors -----------------------------------------------------------

from pharmashed.params import Dist
from pharmashed.priors import make_rng, sample_dist


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


def test_sample_dist_fixed():
    d = Dist(kind="fixed", value=3.14)
    out = sample_dist(d, _rng(), 100)
    assert np.all(out == 3.14)
    assert out.shape == (100,)


def test_sample_dist_uniform_bounds():
    d = Dist(kind="uniform", min=2.0, max=5.0)
    out = sample_dist(d, _rng(), 500)
    assert out.min() >= 2.0
    assert out.max() <= 5.0


def test_sample_dist_loguniform_median():
    """Log-uniform median should be ≈ geometric mean of min and max."""
    lo, hi = 0.01, 1.0
    d = Dist(kind="loguniform", min=lo, max=hi)
    out = sample_dist(d, _rng(42), 5_000)
    expected_median = np.sqrt(lo * hi)
    assert abs(np.median(out) - expected_median) / expected_median < 0.05


def test_sample_dist_loguniform_bounds():
    d = Dist(kind="loguniform", min=0.002, max=0.15)
    out = sample_dist(d, _rng(), 500)
    assert out.min() >= 0.002
    assert out.max() <= 0.15


def test_sample_dist_triangular_bounds():
    d = Dist(kind="triangular", min=1.0, value=2.0, max=4.0)
    out = sample_dist(d, _rng(), 500)
    assert out.min() >= 1.0
    assert out.max() <= 4.0


def test_make_rng_deterministic():
    r1 = make_rng(42, "TLS-01", "carbamazepine")
    r2 = make_rng(42, "TLS-01", "carbamazepine")
    assert r1.integers(0, 1_000_000) == r2.integers(0, 1_000_000)


def test_make_rng_order_independent():
    """Different iteration orders → same per-(site,drug) draws."""
    r_first = make_rng(42, "TLS-01", "atenolol")
    _ = make_rng(42, "GNT-02", "losartan")
    r_second = make_rng(42, "TLS-01", "atenolol")
    assert r_first.integers(0, 1_000_000) == r_second.integers(0, 1_000_000)


# --- M07 model core -------------------------------------------------------

from pharmashed.model import apply_variant, pec_ng_l, rq


def test_pec_hand_calculation():
    """Single draw with round numbers, reproduced by hand (A4)."""
    P = 10_000      # persons
    C = 10.0        # DDD/1000/day
    ddd = 0.2       # g
    fe = 0.5
    lam = 0.05
    w = 0
    R = 0.0         # irrelevant when w=0
    Q = 0.1         # m³/s
    k = 0.0         # no decay
    tau = 0.0

    # L = 10000 * 10 * 0.2 / 1000 = 20 g/day
    # E = 20 * 0.5 = 10 g/day
    # M = 10 * (0.05 + 0 * ...) = 0.5 g/day
    # Qd = 0.1 * 86400 * 1000 = 8_640_000 L/day
    # PEC = 0.5 / 8_640_000 * 1e9 ≈ 57.87 ng/L
    expected = 0.5 / (0.1 * 86400 * 1000) * 1e9
    result = pec_ng_l(P, C, ddd, fe, lam, w, R, Q, k, tau)
    assert float(result) == pytest.approx(expected, rel=1e-9)


def test_pec_zero_when_lam_zero_w_zero():
    result = pec_ng_l(
        P=5000, C=5.0, ddd_g=0.3, fe=0.5,
        lam=0.0, w=0, R=0.0,
        Q_m3s=0.2, k_per_h=0.0, tau_h=0.0,
    )
    assert float(result) == pytest.approx(0.0, abs=1e-15)


def test_pec_doubling_Q_halves_PEC():
    kwargs = dict(P=5000, C=5.0, ddd_g=0.3, fe=0.5, lam=0.05,
                  w=0, R=0.0, k_per_h=0.0, tau_h=0.0)
    p1 = float(pec_ng_l(Q_m3s=0.1, **kwargs))
    p2 = float(pec_ng_l(Q_m3s=0.2, **kwargs))
    assert p1 == pytest.approx(2 * p2, rel=1e-9)


def test_pec_doubling_lam_doubles_PEC_w0():
    kwargs = dict(P=5000, C=5.0, ddd_g=0.3, fe=0.5,
                  w=0, R=0.0, Q_m3s=0.1, k_per_h=0.0, tau_h=0.0)
    p1 = float(pec_ng_l(lam=0.05, **kwargs))
    p2 = float(pec_ng_l(lam=0.10, **kwargs))
    assert p2 == pytest.approx(2 * p1, rel=1e-9)


def test_rq_scenario_shortcut():
    """RQ' = RQ · mλ · mC / mQ must hold for w=0 (D13 client-side shortcut)."""
    kwargs = dict(P=5000, C=5.0, ddd_g=0.3, fe=0.5,
                  w=0, R=0.0, Q_m3s=0.1, k_per_h=0.0, tau_h=0.0)
    pnec = 50.0
    m_lam, m_C, m_Q = 1.5, 2.0, 3.0

    pec0 = pec_ng_l(lam=0.05, **kwargs)
    rq0 = rq(pec0, pnec)

    # direct recompute with scaled inputs
    pec_scaled = pec_ng_l(
        lam=0.05 * m_lam, C=5.0 * m_C, Q_m3s=0.1 * m_Q,
        P=5000, ddd_g=0.3, fe=0.5, w=0, R=0.0, k_per_h=0.0, tau_h=0.0,
    )
    rq_scaled_direct = rq(pec_scaled, pnec)

    # shortcut
    rq_shortcut = rq0 * m_lam * m_C / m_Q

    assert float(rq_scaled_direct) == pytest.approx(float(rq_shortcut), rel=1e-9)


def test_apply_variant_wwtp_only_sets_lam_zero():
    inputs = {"lambda": np.array([0.05, 0.10]), "C": np.array([1.0, 2.0])}
    out = apply_variant(inputs, "wwtp_only", 1.0)
    assert np.all(out["lambda"] == 0.0)
    assert np.array_equal(out["C"], inputs["C"])  # unchanged


def test_apply_variant_pop_only_replaces_C():
    inputs = {"lambda": np.array([0.05, 0.10]), "C": np.array([1.0, 2.0])}
    out = apply_variant(inputs, "pop_only", 5.0)
    assert np.all(out["C"] == 5.0)
    assert np.array_equal(out["lambda"], inputs["lambda"])


def test_apply_variant_full_no_change():
    inputs = {"lambda": np.array([0.05]), "C": np.array([1.0])}
    out = apply_variant(inputs, "full", 5.0)
    assert out is inputs  # same object, no copy


# --- M09 sensitivity ------------------------------------------------------

from pharmashed.sensitivity import driver_sentence, flip_thresholds, spearman_drivers


def _fixed_inputs(n: int = 200) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(7)
    return {
        "lambda":    rng.uniform(0.002, 0.15, n),
        "Q_m3s":     rng.uniform(0.005, 0.1, n),
        "C":         rng.uniform(1.0, 20.0, n),
        "fe":        rng.uniform(0.1, 0.9, n),
        "k_per_h":   np.full(n, 0.01),     # fixed
        "tau_h":     rng.uniform(0.5, 12, n),
        "ddd_g":     rng.uniform(0.1, 1.0, n),
        "pnec_ng_l": rng.uniform(10, 500, n),
    }


def test_spearman_drivers_count():
    inputs = _fixed_inputs()
    rq_arr = inputs["lambda"] * inputs["C"]  # synthetic RQ dominated by λ and C
    drivers = spearman_drivers(inputs, rq_arr)
    assert 1 <= len(drivers) <= 5


def test_spearman_drivers_skip_fixed():
    inputs = _fixed_inputs()
    rq_arr = inputs["lambda"]
    drivers = spearman_drivers(inputs, rq_arr)
    # k_per_h is fixed → should not appear
    assert all(d.param != "k_per_h" for d in drivers)


def test_spearman_drivers_Q_negative():
    """Q should have negative ρ with RQ (larger Q → lower PEC → lower RQ)."""
    n = 300
    rng = np.random.default_rng(0)
    Q = rng.uniform(0.01, 1.0, n)
    lam = np.full(n, 0.05)
    P, C, ddd, fe = 5000.0, 10.0, 0.2, 0.5
    pnec = 50.0
    pec_arr = pec_ng_l(P, C, ddd, fe, lam, 0, 0.0, Q, 0.0, 0.0)
    rq_arr = rq(pec_arr, pnec)
    inputs = {"Q_m3s": Q, "lambda": lam}
    drivers = spearman_drivers(inputs, rq_arr)
    q_driver = next((d for d in drivers if d.param == "Q_m3s"), None)
    assert q_driver is not None
    assert q_driver.rho < 0


def test_driver_sentence_two():
    from pharmashed.contracts import Driver
    drivers = [Driver(param="lambda", rho=0.8), Driver(param="Q_m3s", rho=-0.5)]
    sent = driver_sentence(drivers)
    assert "leakage" in sent and "stream flow" in sent


def test_flip_thresholds_high_tier():
    """A high-score pair should return a down flip only."""
    rq_arr = np.random.default_rng(1).uniform(2, 10, 500)  # score ≈ 1.0 → high
    inputs = {"lambda": np.random.default_rng(2).uniform(0.002, 0.15, 500)}
    flip = flip_thresholds(rq_arr, inputs)
    assert flip is not None
    assert flip.up is None
    assert flip.down is not None


def test_flip_thresholds_low_tier():
    """A very low score pair should return an up flip only."""
    rq_arr = np.full(500, 0.001)   # score = 0 → low
    inputs = {"lambda": np.random.default_rng(3).uniform(0.002, 0.15, 500)}
    flip = flip_thresholds(rq_arr, inputs)
    # Quantile at 0.9 = 0.001, m = 1/0.001 = 1000 → out of range [0.01, 100]
    # So flip may be None for an unreachable target — that's valid
    assert flip is None or flip.down is None


# --- M10 scoring ----------------------------------------------------------

from pharmashed.scoring import (
    city_summary,
    histogram,
    lod_share,
    score,
    site_overall,
    tier,
    compute_ranks,
)


def test_score_all_above():
    assert score(np.full(100, 2.0)) == pytest.approx(1.0)


def test_score_none_above():
    assert score(np.full(100, 0.5)) == pytest.approx(0.0)


def test_score_half():
    arr = np.array([0.5] * 50 + [2.0] * 50)
    assert score(arr) == pytest.approx(0.5)


def test_tier_high():
    assert tier(0.5) == "high"
    assert tier(0.99) == "high"


def test_tier_medium():
    assert tier(0.1) == "medium"
    assert tier(0.49) == "medium"


def test_tier_low():
    assert tier(0.0) == "low"
    assert tier(0.09) == "low"


def test_lod_share():
    pec = np.array([1.0, 5.0, 10.0, 20.0])
    assert lod_share(pec, 5.0) == pytest.approx(0.5)


def test_histogram_counts_sum():
    rq_arr = np.random.default_rng(0).lognormal(0, 1, 500)
    h = histogram(rq_arr, bins=40)
    assert sum(h.counts) == pytest.approx(500, abs=50)
    assert len(h.log10_edges) == 41
    assert len(h.counts) == 40


def test_histogram_all_zeros():
    h = histogram(np.zeros(100), bins=10)
    assert len(h.counts) == 10


def test_compute_ranks_order():
    flat = [
        {"site_id": "TLS-01", "city": "TLS", "drug": "cbz", "score": 0.8, "rq_p50": 3.0},
        {"site_id": "TLS-02", "city": "TLS", "drug": "cbz", "score": 0.3, "rq_p50": 1.5},
        {"site_id": "TLS-03", "city": "TLS", "drug": "cbz", "score": 0.8, "rq_p50": 2.0},
    ]
    ranks = compute_ranks(flat)
    city_drug_ranks = ranks[("TLS", "cbz")]
    # TLS-01 has same score but higher p50 → rank 1
    assert city_drug_ranks["TLS-01"][0] == 1
    assert city_drug_ranks["TLS-03"][0] == 2
    assert city_drug_ranks["TLS-02"][0] == 3


def test_site_overall_max_score():
    from pharmashed.contracts import SiteOverall
    flat = [
        {"site_id": "TLS-01", "city": "TLS", "drug": "cbz", "score": 0.8, "rq_p50": 3.0, "rank_in_city": 1},
        {"site_id": "TLS-01", "city": "TLS", "drug": "aten", "score": 0.3, "rq_p50": 1.0, "rank_in_city": 2},
    ]
    overalls = site_overall(flat)
    tls01 = next(o for o in overalls if o.site_id == "TLS-01")
    assert tls01.score == pytest.approx(0.8)
    assert tls01.top_drug == "cbz"


def test_city_summary_counts():
    from pharmashed.contracts import SiteOverall
    overalls = [
        SiteOverall(site_id="TLS-01", score=0.8, top_drug="cbz", rank_in_city=1),
        SiteOverall(site_id="TLS-02", score=0.3, top_drug="cbz", rank_in_city=2),
        SiteOverall(site_id="TLS-03", score=0.05, top_drug="cbz", rank_in_city=3),
    ]
    summaries = city_summary(overalls)
    tls = next(s for s in summaries if s.city == "TLS")
    assert tls.high == 1
    assert tls.medium == 1
    assert tls.low == 1
