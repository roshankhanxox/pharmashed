"""Priors and sampling (M06).

Turns parameter dists and YAML priors into draw arrays of shape (N,).
All samplers are pure functions over an explicit RNG; no global state.
"""

from __future__ import annotations

import numpy as np

from pharmashed.contracts import Site
from pharmashed.params import Dist, Priors


def sample_dist(dist: Dist, rng: np.random.Generator, n: int) -> np.ndarray:
    """Sample *n* draws from a Dist specification.

    Args:
        dist: a Dist object from the parameter registry.
        rng: a numpy Generator (caller owns it).
        n: number of draws.

    Returns:
        float64 array of shape (n,).
    """
    kind = dist.kind
    if kind == "fixed":
        return np.full(n, dist.value, dtype=np.float64)
    if kind == "uniform":
        return rng.uniform(dist.min, dist.max, size=n)
    if kind == "loguniform":
        log_min = np.log(dist.min)
        log_max = np.log(dist.max)
        return np.exp(rng.uniform(log_min, log_max, size=n))
    if kind == "triangular":
        return rng.triangular(dist.min, dist.value, dist.max, size=n)
    raise ValueError(f"Unknown dist kind: {kind!r}")


def sample_site_inputs(
    site: Site,
    priors: Priors,
    rng: np.random.Generator,
    n: int,
) -> dict[str, np.ndarray]:
    """Sample λ, Q, and τ draws for one site.

    Args:
        site: Site object (size_class used for Q prior selection).
        priors: loaded from priors.yaml.
        rng: caller-owned Generator.
        n: number of draws.

    Returns:
        dict with keys ``lambda``, ``Q_m3s``, ``tau_h``.
    """
    lam = sample_dist(priors.lambda_.to_dist(), rng, n)
    q_dist = getattr(priors.Q_by_size_class, site.size_class).to_dist()
    Q = sample_dist(q_dist, rng, n)
    tau = sample_dist(priors.tau_h.to_dist(), rng, n)
    return {"lambda": lam, "Q_m3s": Q, "tau_h": tau}


def sample_drug_inputs(
    drug_params: dict[str, Dist],
    rng: np.random.Generator,
    n: int,
) -> dict[str, np.ndarray]:
    """Sample ddd_g, fe, k_per_h, pnec_ng_l, lod_ng_l for one drug.

    Args:
        drug_params: mapping of param_name → Dist (from params.load_drug_params).
        rng: caller-owned Generator.
        n: number of draws.

    Returns:
        dict with keys ``ddd_g``, ``fe``, ``k_per_h``, ``pnec_ng_l``, ``lod_ng_l``.
    """
    return {
        param: sample_dist(dist, rng, n)
        for param, dist in drug_params.items()
    }


def sample_consumption(
    value: float,
    priors: Priors,
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """Apply the consumption uncertainty multiplier to a point estimate.

    Multiplier is drawn from the consumption_multiplier prior in priors.yaml.

    Args:
        value: point estimate of consumption in DDD/1000 inh/day.
        priors: loaded from priors.yaml.
        rng: caller-owned Generator.
        n: number of draws.

    Returns:
        float64 array of shape (n,): value × multiplier draws.
    """
    multipliers = sample_dist(priors.consumption_multiplier.to_dist(), rng, n)
    return value * multipliers


def make_rng(seed: int, site_id: str, drug: str) -> np.random.Generator:
    """Derive a deterministic per-(site, drug) Generator from a root seed.

    Uses SeedSequence.spawn so the result does not depend on iteration order.

    Args:
        seed: root integer seed (from config.SEED or run args).
        site_id: e.g. ``"TLS-01"``.
        drug: e.g. ``"carbamazepine"``.

    Returns:
        A numpy Generator seeded deterministically for this (site, drug) pair.
    """
    # Fold site_id and drug into the entropy — never use as spawn count
    pair_entropy = abs(hash((site_id, drug))) & 0xFFFF_FFFF
    ss = np.random.SeedSequence([seed, pair_entropy])
    return np.random.default_rng(ss)
