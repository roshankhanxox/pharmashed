"""Monte Carlo runner (M08).

For every (site × drug) pair: sample inputs, compute PEC and RQ over N_DRAWS,
store summaries and N_STORED draws for the web client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from pharmashed import config
from pharmashed.consumption import ConsumptionRow, consumption_value, load_consumption
from pharmashed.contracts import Site
from pharmashed.model import Variant, apply_variant, pec_ng_l, rq
from pharmashed.params import DrugParams, Priors, load_drug_params, load_priors
from pharmashed.params import load_rows as load_param_rows
from pharmashed.priors import make_rng, sample_consumption, sample_drug_inputs, sample_site_inputs
from pharmashed.sites import load_sites

_REPO_ROOT = Path(__file__).resolve().parents[3]

Mode = Literal["dev", "strict"]


@dataclass
class RunContext:
    """Bundles all inputs needed by the Monte Carlo runner."""

    sites: list[Site]
    drug_params: dict[str, DrugParams]
    priors: Priors
    consumption_rows: list[ConsumptionRow]
    seed: int = config.SEED
    mode: Mode = "dev"
    n_draws: int = config.N_DRAWS
    n_stored: int = config.N_STORED
    # Rows behind the drug parameters (for provenance and honest run metadata) and whether the
    # dev-mode placeholder fallback filled any `todo` parameter (D16).
    param_rows: list = field(default_factory=list)
    dev_placeholders: bool = False

    # Derived: consumption[country][drug] → float (DDD/1000/day)
    _consumption: dict[str, dict[str, float]] = field(default_factory=dict, init=False, repr=False)
    # Derived: cross-country mean per drug for pop_only variant
    _mean_C: dict[str, float] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        for row in self.consumption_rows:
            if row.status == "todo":
                continue
            self._consumption.setdefault(row.country, {})[row.drug] = consumption_value(row)
        drugs = config.DRUGS
        for drug in drugs:
            vals = [
                self._consumption[c][drug]
                for c in self._consumption
                if drug in self._consumption[c]
            ]
            self._mean_C[drug] = float(np.mean(vals)) if vals else 1.0

    def illustrative_count(self) -> int:
        """Number of parameter and consumption rows that are declared illustrative (D33)."""
        rows = [*self.param_rows, *self.consumption_rows]
        return sum(1 for r in rows if r.status == "illustrative")

    def sourced_count(self) -> int:
        """Number of parameter and consumption rows that are sourced."""
        rows = [*self.param_rows, *self.consumption_rows]
        return sum(1 for r in rows if r.status == "sourced")

    def all_inputs_sourced(self) -> bool:
        """True only if no parameter or consumption row is illustrative or still todo.

        The optional R row is ignored: every MVP site has w=0, so R is never used (D27).
        """
        rows = [r for r in self.param_rows if getattr(r, "param", "") != "R"] + list(self.consumption_rows)
        return bool(rows) and all(r.status == "sourced" for r in rows)

    def consumption_for(self, city: str, drug: str) -> float:
        """Return DDD/1000/day for the country that maps to city (D02)."""
        country_map = {"TLS": "FR", "GNT": "BE", "BNV": "IT", "CBR": "PT", "OSL": "NO"}
        country = country_map[city]
        return self._consumption.get(country, {}).get(drug, 1.0)

    def mean_C(self, drug: str) -> float:
        return self._mean_C.get(drug, 1.0)

    @classmethod
    def from_paths(
        cls,
        params_path: Path | None = None,
        priors_path: Path | None = None,
        consumption_path: Path | None = None,
        sites_path: Path | None = None,
        mode: Mode = "dev",
        seed: int = config.SEED,
    ) -> "RunContext":
        params_path = params_path or _REPO_ROOT / "data" / "params" / "drug_parameters.csv"
        priors_path = priors_path or _REPO_ROOT / "data" / "params" / "priors.yaml"
        consumption_path = consumption_path or _REPO_ROOT / "data" / "consumption" / "consumption.csv"
        sites_path = sites_path or _REPO_ROOT / "data" / "sites" / "sites.geojson"

        drug_params, dev_placeholders = load_drug_params(params_path, mode=mode)
        param_rows = load_param_rows(params_path)
        priors = load_priors(priors_path)
        consumption_dict = load_consumption(consumption_path, mode=mode)
        consumption_rows = list(consumption_dict.values())
        sites = load_sites(sites_path)

        return cls(
            sites=sites,
            drug_params=drug_params,
            priors=priors,
            consumption_rows=consumption_rows,
            seed=seed,
            mode=mode,
            param_rows=param_rows,
            dev_placeholders=dev_placeholders,
        )


@dataclass
class PairResult:
    """Full draw arrays for one (site, drug) pair, kept in memory during a run."""

    site_id: str
    drug: str
    pec: np.ndarray    # shape (N_DRAWS,), ng/L
    rq_arr: np.ndarray # shape (N_DRAWS,), dimensionless
    inputs: dict[str, np.ndarray]  # sampled inputs (N_DRAWS,) each
    # N_STORED draws (first N_STORED of the same arrays)
    pec_stored: np.ndarray
    rq_stored: np.ndarray


def run_pair(
    site: Site,
    drug: str,
    ctx: RunContext,
    variant: Variant = "full",
) -> PairResult:
    """Run the Monte Carlo simulation for one (site, drug) pair.

    Args:
        site: site object.
        drug: drug name (lowercase INN).
        ctx: RunContext with all data and settings.
        variant: model variant (full / wwtp_only / pop_only).

    Returns:
        PairResult with pec, rq_arr and inputs arrays of length ctx.n_draws.
    """
    rng = make_rng(ctx.seed, site.id, drug)
    dp = ctx.drug_params[drug]
    n = ctx.n_draws

    site_draws = sample_site_inputs(site, ctx.priors, rng, n)
    drug_draws = sample_drug_inputs(
        {
            "ddd_g": dp.ddd_g,
            "fe": dp.fe,
            "k_per_h": dp.k_per_h,
            "pnec_ng_l": dp.pnec_ng_l,
            "lod_ng_l": dp.lod_ng_l,
        },
        rng,
        n,
    )

    C_point = ctx.consumption_for(site.city, drug)
    C_draws = sample_consumption(C_point, ctx.priors, rng, n)

    inputs: dict[str, np.ndarray] = {
        **site_draws,
        **drug_draws,
        "C": C_draws,
        "P": np.full(n, float(site.population_buffer)),
        "w": np.full(n, float(site.w)),
        "R": dp.R.sample(rng, n),
    }

    if variant != "full":
        inputs = apply_variant(inputs, variant, ctx.mean_C(drug))

    pec_arr = pec_ng_l(
        P=inputs["P"],
        C=inputs["C"],
        ddd_g=inputs["ddd_g"],
        fe=inputs["fe"],
        lam=inputs["lambda"],
        w=int(site.w),
        R=inputs["R"],
        Q_m3s=inputs["Q_m3s"],
        k_per_h=inputs["k_per_h"],
        tau_h=inputs["tau_h"],
    )
    rq_arr = rq(pec_arr, inputs["pnec_ng_l"])

    ns = ctx.n_stored
    return PairResult(
        site_id=site.id,
        drug=drug,
        pec=pec_arr,
        rq_arr=rq_arr,
        inputs=inputs,
        pec_stored=pec_arr[:ns],
        rq_stored=rq_arr[:ns],
    )


def run_all(ctx: RunContext, variant: Variant = "full") -> list[PairResult]:
    """Run all (site × drug) pairs and return results.

    Args:
        ctx: RunContext.
        variant: model variant applied to every pair.

    Returns:
        List of PairResult, one per (site, drug) pair.
    """
    results: list[PairResult] = []
    for site in ctx.sites:
        if not site.valid:
            continue
        for drug in config.DRUGS:
            if drug not in ctx.drug_params:
                continue
            results.append(run_pair(site, drug, ctx, variant=variant))
    return results
