"""Build-artifact exporter (M11).

Writes results.json, draws.bin, draws_index.json, sites.json,
provenance.json, methodology.json, glossary.json to a build directory.
"""

from __future__ import annotations

import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pharmashed import config
from pharmashed.contracts import (
    AblationRanking,
    Ablations,
    CitySummary,
    DrawsIndex,
    DrawsIndexEntry,
    DrawsRef,
    FhirIds,
    Flip,
    Histogram,
    Methodology,
    MethodologyMeta,
    PercentileTriplet,
    PriorRow,
    Results,
    ResultEntry,
    ResultsMeta,
    Site,
    SiteOverall,
    Sites,
    SitesMeta,
    Stage,
)
from pharmashed import consumption as _cons_mod
from pharmashed import params as _params_mod
from pharmashed.montecarlo import PairResult, RunContext, run_all
from pharmashed.scoring import (
    city_summary,
    compute_ranks,
    histogram,
    lod_share,
    score,
    site_overall,
    tier,
)
from pharmashed.sensitivity import driver_sentence, flip_thresholds, spearman_drivers
from pharmashed.sites import cities as load_cities

try:
    import pharmashed as _pkg
    _ENGINE_VERSION = getattr(_pkg, "__version__", "0.0.0")
except Exception:
    _ENGINE_VERSION = "0.0.0"

_GLOSSARY = {
    "PEC":   {"symbol": "PEC",   "name": "predicted concentration",    "definition": "Model estimate of drug concentration at a site, in ng/L."},
    "PNEC":  {"symbol": "PNEC",  "name": "no-effect threshold",        "definition": "Concentration below which no ecotoxicological effect is expected, in ng/L."},
    "RQ":    {"symbol": "RQ",    "name": "risk ratio",                 "definition": "PEC ÷ PNEC; values > 1 indicate potential concern."},
    "LOD":   {"symbol": "LOD",   "name": "detection limit",            "definition": "Analytical limit of detection for a drug, in ng/L."},
    "λ":     {"symbol": "λ",     "name": "leakage",                    "definition": "Fraction of wastewater entering the stream untreated (sewer leakage, misconnections)."},
    "Q":     {"symbol": "Q",     "name": "stream flow",                "definition": "Stream discharge in m³/s; higher flow dilutes concentrations."},
    "τ":     {"symbol": "τ",     "name": "travel time",                "definition": "Time for water to travel from entry point to monitoring site, in hours."},
    "k":     {"symbol": "k",     "name": "in-stream loss rate",        "definition": "First-order decay rate constant in 1/h (biodegradation, sorption, photolysis)."},
    "fe":    {"symbol": "fe",    "name": "excretion fraction",         "definition": "Fraction of a dose excreted as unchanged parent compound."},
    "DDD":   {"symbol": "DDD",   "name": "daily dose",                 "definition": "WHO defined daily dose in grams; used to convert consumption statistics to mass."},
    "score": {"symbol": "score", "name": "sampling priority score",    "definition": "Fraction of simulation draws with RQ > 1. Guides where to sample first. Not a probability of exceedance."},
}

_IDENTIFIABILITY_TEXT = (
    "The model has three unidentifiable parameters per site: λ (leakage fraction), "
    "Q (stream flow), and τ (travel time). These are drawn from prior distributions "
    "informed by published sewer-leakage studies and OSM stream geometry. "
    "The sensitivity analysis (Spearman ρ) identifies which prior dominates "
    "the score uncertainty at each site. Parameters informed by measured data "
    "(DDD, fe, PNEC, LOD) reduce uncertainty only when sourced. "
    "With illustrative parameters (D33), the model demonstrates the pipeline "
    "mechanism only — scores are not evidence of actual risk."
)

_STAGES: list[Stage] = [
    Stage(id="pop",  name="Population",  symbol="P",   prior_summary="GHS-POP 100 m, 500 m buffer",      provenance_key="prior:population"),
    Stage(id="cons", name="Consumption", symbol="C",   prior_summary="DDD/1000 inh/day, national data",  provenance_key="prior:consumption"),
    Stage(id="excr", name="Excretion",   symbol="fe",  prior_summary="Per-drug excretion fraction",      provenance_key="prior:excretion"),
    Stage(id="load", name="Mass load",   symbol="M",   prior_summary="g/day entering stream",            provenance_key="prior:lambda"),
    Stage(id="dil",  name="Dilution",    symbol="Q",   prior_summary="m³/s log-uniform by size class",   provenance_key="prior:Q"),
    Stage(id="pec",  name="PEC",         symbol="PEC", prior_summary="ng/L after in-stream loss",        provenance_key="prior:tau"),
    Stage(id="rq",   name="RQ",          symbol="RQ",  prior_summary="PEC ÷ PNEC",                       provenance_key="prior:pnec"),
]


def _pct(arr: np.ndarray, p: float) -> float:
    return float(np.percentile(arr, p))


def _build_result_entry(
    pr: PairResult,
    rank: int,
    n_in_city: int,
    draws_offset: int,
) -> ResultEntry:
    sc = score(pr.rq_arr)
    pnec_val = float(np.mean(pr.inputs["pnec_ng_l"]))
    lod_val = float(np.mean(pr.inputs["lod_ng_l"]))
    drivers = spearman_drivers(pr.inputs, pr.rq_arr)
    flip_result = flip_thresholds(pr.rq_arr, pr.inputs)
    flip_obj = flip_result if flip_result is not None else Flip(up=None, down=None)

    return ResultEntry(
        site_id=pr.site_id,
        drug=pr.drug,
        pec_ng_l=PercentileTriplet(
            p5=_pct(pr.pec, 5), p50=_pct(pr.pec, 50), p95=_pct(pr.pec, 95)
        ),
        rq=PercentileTriplet(
            p5=_pct(pr.rq_arr, 5), p50=_pct(pr.rq_arr, 50), p95=_pct(pr.rq_arr, 95)
        ),
        pnec_ng_l=max(pnec_val, 1e-9),
        lod_ng_l=max(lod_val, 1e-9),
        score=sc,
        tier=tier(sc),
        lod_share=lod_share(pr.pec, lod_val),
        rank_in_city=rank,
        n_in_city=n_in_city,
        drivers=drivers,
        driver_sentence=driver_sentence(drivers),
        flip=flip_obj,
        histogram=histogram(pr.rq_arr),
        draws=DrawsRef(offset=draws_offset, count=len(pr.rq_stored)),
        provenance_keys=[
            f"param:{pr.drug}:fe",
            f"param:{pr.drug}:ddd_g",
            f"param:{pr.drug}:pnec_ng_l",
            f"param:{pr.drug}:lod_ng_l",
            f"param:{pr.drug}:k_per_h",
            "prior:lambda",
            "prior:Q",
            "prior:tau",
            f"consumption:{pr.site_id[:3]}:{pr.drug}",
        ],
        fhir_ids=FhirIds(prediction=f"pred-{pr.site_id}-{pr.drug}"),
    )


def export_build(
    ctx: RunContext,
    out_dir: Path,
    variant: str = "full",
    frozen_tag: str | None = None,
) -> Path:
    """Run the full pipeline and write all build artifacts.

    Args:
        ctx: RunContext with all inputs loaded.
        out_dir: directory to write artifacts (created if absent).
        variant: model variant (full / wwtp_only / pop_only).
        frozen_tag: optional git tag to embed in results.meta.

    Returns:
        Path to the written results.json.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = run_all(ctx, variant=variant)  # type: ignore[arg-type]

    flat = [
        {
            "site_id": pr.site_id,
            "city": pr.site_id[:3],
            "drug": pr.drug,
            "score": score(pr.rq_arr),
            "rq_p50": _pct(pr.rq_arr, 50),
        }
        for pr in pairs
    ]
    ranks_map = compute_ranks(flat)

    # draws.bin + draws_index.json
    draws_bin = bytearray()
    index_entries: list[DrawsIndexEntry] = []
    draw_offset = 0
    for pr in pairs:
        stored = pr.rq_stored.astype(np.float32)
        draws_bin.extend(struct.pack(f"<{len(stored)}f", *stored))
        index_entries.append(DrawsIndexEntry(
            site_id=pr.site_id, drug=pr.drug,
            offset=draw_offset, count=len(stored),
        ))
        draw_offset += len(stored)

    (out_dir / "draws.bin").write_bytes(bytes(draws_bin))
    draws_index = DrawsIndex(
        dtype="float32", endianness="little",
        n_stored=ctx.n_stored, entries=index_entries,
    )
    (out_dir / "draws_index.json").write_text(draws_index.model_dump_json(indent=2))

    # result entries
    result_entries: list[ResultEntry] = []
    entry_offset = 0
    for pr in pairs:
        city = pr.site_id[:3]
        city_drug_ranks = ranks_map.get((city, pr.drug), {})
        rank, n = city_drug_ranks.get(pr.site_id, (1, 1))
        entry = _build_result_entry(pr, rank, n, entry_offset)
        result_entries.append(entry)
        entry_offset += ctx.n_stored

    overalls = site_overall(flat)
    summaries = city_summary(overalls)

    results = Results(
        meta=ResultsMeta(
            engine_version=_ENGINE_VERSION,
            generated_at=datetime.now(timezone.utc),
            seed=ctx.seed,
            n_draws=ctx.n_draws,
            n_stored=ctx.n_stored,
            variant=variant,  # type: ignore[arg-type]
            dev_placeholders=ctx.dev_placeholders,
            frozen_tag=frozen_tag,
            param_count=len(ctx.param_rows),
            all_params_cited=ctx.all_inputs_sourced(),
        ),
        drugs=config.DRUGS,
        results=result_entries,
        site_overall=overalls,
        city_summary=summaries,
    )
    results_path = out_dir / "results.json"
    results_path.write_text(results.model_dump_json(indent=2))

    # sites.json
    sites_doc = Sites(
        meta=SitesMeta(generated_at=datetime.now(timezone.utc), synthetic=True),
        cities=load_cities(),
        sites=ctx.sites,
    )
    (out_dir / "sites.json").write_text(sites_doc.model_dump_json(indent=2))

    # provenance.json
    prov = _params_mod.provenance_entries(ctx.param_rows, ctx.priors)
    prov.update(_cons_mod.provenance_entries(ctx.consumption_rows))
    (out_dir / "provenance.json").write_text(
        json.dumps({k: v.model_dump() for k, v in prov.items()}, indent=2)
    )

    # methodology.json
    _write_methodology(ctx, out_dir)

    # glossary.json
    (out_dir / "glossary.json").write_text(json.dumps(_GLOSSARY, indent=2))

    return results_path


def _write_methodology(ctx: RunContext, out_dir: Path) -> None:
    """Write methodology.json including ablation rankings."""
    ablation_data: list[AblationRanking] = []
    for v in ("full", "pop_only", "wwtp_only"):
        v_pairs = run_all(ctx, variant=v)  # type: ignore[arg-type]
        v_flat = [
            {
                "site_id": p.site_id,
                "city": p.site_id[:3],
                "drug": p.drug,
                "score": score(p.rq_arr),
                "rq_p50": _pct(p.rq_arr, 50),
            }
            for p in v_pairs
        ]
        v_overalls = site_overall(v_flat)
        cities_seen: dict[str, list[SiteOverall]] = {}
        for o in v_overalls:
            cities_seen.setdefault(o.site_id[:3], []).append(o)
        for city, c_overalls in sorted(cities_seen.items()):
            c_overalls.sort(key=lambda o: o.rank_in_city)
            ablation_data.append(AblationRanking(
                city=city,
                variant=v,  # type: ignore[arg-type]
                ranking=[o.site_id for o in c_overalls],
            ))

    priors_table: list[PriorRow] = [
        PriorRow(param="λ (leakage)", distribution="loguniform", range="0.002–0.15",
                 unit="fraction", status="assumption", source_url=None, shape="log-uniform"),
        PriorRow(param="Q (S class)", distribution="loguniform", range="0.005–0.1",
                 unit="m³/s", status="assumption", source_url=None, shape="log-uniform"),
        PriorRow(param="Q (M class)", distribution="loguniform", range="0.02–0.5",
                 unit="m³/s", status="assumption", source_url=None, shape="log-uniform"),
        PriorRow(param="Q (L class)", distribution="loguniform", range="0.1–2.0",
                 unit="m³/s", status="assumption", source_url=None, shape="log-uniform"),
        PriorRow(param="τ (travel time)", distribution="uniform", range="0.5–12",
                 unit="hours", status="assumption", source_url=None, shape="uniform"),
        PriorRow(param="C multiplier", distribution="loguniform", range="0.5–2.0",
                 unit="dimensionless", status="assumption", source_url=None, shape="log-uniform"),
    ]

    methodology = Methodology(
        meta=MethodologyMeta(generated_at=datetime.now(timezone.utc)),
        stages=_STAGES,
        priors_table=priors_table,
        identifiability_text=_IDENTIFIABILITY_TEXT,
        ablations=Ablations(
            variants=["full", "pop_only", "wwtp_only"],
            per_city=ablation_data,
        ),
    )
    (out_dir / "methodology.json").write_text(methodology.model_dump_json(indent=2))


def sha256_file(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
