"""Generate contracts/fixtures/*: a small, obviously-fake example of every
contract file (M01), for web and engine to develop against before the real
pipeline (M02-M14) exists.

Fixed seed, dev_placeholders=true throughout. Values here are NOT sourced
parameters -- never copy them into data/params/ or treat them as real.
"""

from __future__ import annotations

import json
import struct
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

SEED = 20260918
GENERATED_AT = "2026-01-01T00:00:00Z"
N_STORED = 64  # small on purpose; real runs use N_STORED=1000 (CONTEXT D12)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "contracts" / "fixtures"

DRUGS = ["carbamazepine", "atenolol", "losartan", "irbesartan", "paracetamol", "citalopram"]

CITIES = [
    {"id": "TLS", "name": "Toulouse", "country": "FR", "center": [1.4442, 43.6047], "zoom": 12},
    {"id": "GNT", "name": "Ghent", "country": "BE", "center": [3.7174, 51.0543], "zoom": 12},
]

SIZE_CLASSES = ["S", "M", "L"]

PNEC_FAKE = {  # ng/L, obviously round fixture numbers, not sourced
    "carbamazepine": 500.0,
    "atenolol": 1500.0,
    "losartan": 1000.0,
    "irbesartan": 500.0,
    "paracetamol": 3300.0,
    "citalopram": 200.0,
}
LOD_FAKE = dict.fromkeys(DRUGS, 1.0)


def make_sites() -> dict:
    sites = []
    for city in CITIES:
        for i in range(1, 4):
            sites.append(
                {
                    "id": f"{city['id']}-{i:02d}",
                    "city": city["id"],
                    "name": f"Synthetic fixture site {city['id']}-{i:02d}",
                    "lonlat": [city["center"][0] + 0.01 * i, city["center"][1] + 0.01 * i],
                    "synthetic": True,
                    "size_class": SIZE_CLASSES[(i - 1) % 3],
                    "w": 0,
                    "valid": True,
                    "population_buffer": 1000 * i,
                    "population_source_key": "pop:ghs-pop-2020",
                }
            )
    return {
        "meta": {"generated_at": GENERATED_AT, "synthetic": True},
        "cities": CITIES,
        "sites": sites,
    }


def tier_for(score: float) -> str:
    if score >= 0.5:
        return "high"
    if score >= 0.1:
        return "medium"
    return "low"


def make_results_and_draws(sites: list[dict], rng: np.random.Generator):
    results = []
    draws_entries = []
    draws_blocks: list[np.ndarray] = []
    offset = 0

    for site in sites:
        for drug in DRUGS:
            # fake lognormal-ish RQ draws, deterministic given the seed
            draws = rng.lognormal(mean=-0.5, sigma=1.2, size=N_STORED).astype(np.float32)
            score = float(np.mean(draws > 1))
            p5, p50, p95 = (float(x) for x in np.percentile(draws, [5, 50, 95]))
            pnec = PNEC_FAKE[drug]
            pec_p5, pec_p50, pec_p95 = p5 * pnec, p50 * pnec, p95 * pnec
            lod = LOD_FAKE[drug]
            lod_share = float(np.mean(draws * pnec > lod))

            results.append(
                {
                    "site_id": site["id"],
                    "drug": drug,
                    "pec_ng_l": {"p5": pec_p5, "p50": pec_p50, "p95": pec_p95},
                    "rq": {"p5": p5, "p50": p50, "p95": p95},
                    "pnec_ng_l": pnec,
                    "lod_ng_l": lod,
                    "score": score,
                    "tier": tier_for(score),
                    "lod_share": lod_share,
                    "rank_in_city": 1,
                    "n_in_city": len(DRUGS),
                    "drivers": [
                        {"param": "lambda", "rho": 0.7},
                        {"param": "Q", "rho": -0.55},
                    ],
                    "driver_sentence": "Mostly driven by assumed leakage (λ); flow (Q) second.",
                    "flip": {
                        "up": {"param": "lambda", "multiplier": 1.4, "to_tier": "high"},
                        "down": {"param": "lambda", "multiplier": 0.35, "to_tier": "low"},
                    },
                    "histogram": {
                        "log10_edges": [round(x, 2) for x in np.linspace(-3, 2, 6).tolist()],
                        "counts": [3, 7, 20, 18, 12, 4],
                    },
                    "draws": {"offset": offset, "count": N_STORED},
                    "provenance_keys": [
                        f"param:{drug}:ddd_g",
                        f"param:{drug}:fe",
                        "prior:lambda",
                        f"cons:{site['city']}:{drug}",
                    ],
                    "fhir_ids": {"prediction": f"Observation/pred-{site['id']}-{drug}"},
                }
            )
            draws_entries.append(
                {"site_id": site["id"], "drug": drug, "offset": offset, "count": N_STORED}
            )
            draws_blocks.append(draws)
            offset += N_STORED

    # rank within city by score, descending
    by_site = {}
    for r in results:
        by_site.setdefault(r["site_id"], []).append(r)
    for entries in by_site.values():
        for rank, r in enumerate(sorted(entries, key=lambda e: -e["score"]), start=1):
            r["rank_in_city"] = rank

    site_overall = []
    for site in sites:
        entries = by_site[site["id"]]
        top = max(entries, key=lambda e: e["score"])
        site_overall.append(
            {
                "site_id": site["id"],
                "score": top["score"],
                "top_drug": top["drug"],
                "rank_in_city": 1,
            }
        )
    order = sorted(site_overall, key=lambda e: -e["score"])
    for rank, e in enumerate(order, start=1):
        e["rank_in_city"] = rank

    city_summary = []
    for city in CITIES:
        city_sites = [s["id"] for s in sites if s["city"] == city["id"]]
        # tier of each site's top drug only
        top_tiers = [max(by_site[sid], key=lambda e: e["score"])["tier"] for sid in city_sites]
        city_summary.append(
            {
                "city": city["id"],
                "high": top_tiers.count("high"),
                "medium": top_tiers.count("medium"),
                "low": top_tiers.count("low"),
            }
        )

    results_doc = {
        "meta": {
            "engine_version": "0.0.0",
            "generated_at": GENERATED_AT,
            "seed": SEED,
            "n_draws": 10000,
            "n_stored": N_STORED,
            "variant": "full",
            "dev_placeholders": True,
            "frozen_tag": None,
            "param_count": 42,
            "all_params_cited": False,
        },
        "drugs": DRUGS,
        "results": results,
        "site_overall": site_overall,
        "city_summary": city_summary,
    }

    draws_index = {
        "dtype": "float32",
        "endianness": "little",
        "n_stored": N_STORED,
        "entries": draws_entries,
    }

    draws_bin = b"".join(struct.pack(f"<{len(b)}f", *b.tolist()) for b in draws_blocks)

    return results_doc, draws_index, draws_bin


def make_checks() -> dict:
    return {
        "meta": {
            "frozen_tag": "fixture-not-frozen",
            "frozen_sha256": "0" * 64,
            "generated_at": GENERATED_AT,
        },
        "circularity_statement": (
            "Fixture placeholder: these checks compare model output to the "
            "same observed dataset used to design the checks; treat as a "
            "consistency check, not a validation."
        ),
        "checks": [
            {
                "id": "C1",
                "status": "unavailable",
                "reason": "LOD not yet sourced (fixture)",
                "data": {},
            },
            {
                "id": "C2",
                "status": "pass",
                "reason": None,
                "data": {
                    "observed_order": ["TLS", "GNT", "BNV", "CBR", "OSL"],
                    "predicted_order": ["TLS", "GNT"],
                    "kendall_tau": 1.0,
                },
            },
            {
                "id": "C3",
                "status": "unavailable",
                "reason": "Oslo not in fixture cities",
                "data": {},
            },
            {
                "id": "C4",
                "status": "pass",
                "reason": None,
                "data": {"rows": []},
            },
            {
                "id": "C5",
                "status": "unavailable",
                "reason": "ablations not run in fixture",
                "data": {},
            },
        ],
    }


def make_methodology() -> dict:
    return {
        "meta": {"generated_at": GENERATED_AT},
        "stages": [
            {
                "id": "consumption",
                "name": "Consumption",
                "symbol": "C",
                "prior_summary": "national DDD/1000/day (fixture placeholder)",
                "provenance_key": "cons:FR:irbesartan",
            },
            {
                "id": "excretion",
                "name": "Excretion",
                "symbol": "fe",
                "prior_summary": "fraction excreted unchanged (fixture placeholder)",
                "provenance_key": "param:irbesartan:fe",
            },
            {
                "id": "pathways",
                "name": "Pathways",
                "symbol": "λ, w, R",
                "prior_summary": "untreated leakage λ log-uniform 0.002-0.15",
                "provenance_key": "prior:lambda",
            },
            {
                "id": "dilution",
                "name": "Dilution",
                "symbol": "Q",
                "prior_summary": "stream flow by size class (fixture placeholder)",
                "provenance_key": "prior:Q",
            },
            {
                "id": "instream_loss",
                "name": "In-stream loss",
                "symbol": "k, τ",
                "prior_summary": "first-order decay (fixture placeholder)",
                "provenance_key": "param:irbesartan:k",
            },
            {
                "id": "risk",
                "name": "RQ",
                "symbol": "RQ",
                "prior_summary": "PEC / PNEC (fixture placeholder)",
                "provenance_key": "param:irbesartan:pnec",
            },
        ],
        "priors_table": [
            {
                "param": "lambda",
                "distribution": "log-uniform",
                "range": "0.002-0.15",
                "unit": "fraction",
                "status": "assumption",
                "source_url": None,
                "shape": "log-uniform-band",
            }
        ],
        "identifiability_text": (
            "Fixture placeholder text for the identifiability discussion (docs §5.5)."
        ),
        "ablations": {
            "variants": ["full", "pop_only", "wwtp_only"],
            "per_city": [
                {"city": "TLS", "variant": "full", "ranking": ["TLS-01", "TLS-02", "TLS-03"]},
                {"city": "TLS", "variant": "wwtp_only", "ranking": ["TLS-01", "TLS-02", "TLS-03"]},
                {"city": "GNT", "variant": "full", "ranking": ["GNT-01", "GNT-02", "GNT-03"]},
            ],
        },
    }


def make_provenance(results_doc: dict) -> dict:
    keys = sorted({k for r in results_doc["results"] for k in r["provenance_keys"]})
    entry = {}
    for key in keys:
        entry[key] = {
            "label": key,
            "value": 1.0,
            "unit": "fixture-unit",
            "distribution": None,
            "source_title": None,
            "source_url": None,
            "source_note": "Fixture placeholder value; not a sourced parameter.",
            "status": "todo",
        }
    return entry


def _bundle(name: str, path: str, count: int) -> dict:
    return {"name": name, "path": path, "resource_type": "Bundle", "count": count}


def make_fhir_index() -> dict:
    return {
        "meta": {"generated_at": GENERATED_AT},
        "resource_counts": {
            "Location": 6,
            "Group": 2,
            "Observation": 48,
            "Provenance": 36,
        },
        "bundles": [
            _bundle("terminology", "fhir/out/terminology.json", 4),
            _bundle("locations", "fhir/out/locations.json", 6),
            _bundle("consumption", "fhir/out/consumption.json", 12),
            _bundle("predictions-TLS", "fhir/out/predictions-TLS.json", 18),
            _bundle("predictions-GNT", "fhir/out/predictions-GNT.json", 18),
            _bundle("reference-measurements", "fhir/out/reference-measurements.json", 6),
        ],
        "validation": {
            "status": "unknown",
            "errors": 0,
            "warnings": 0,
            "validator_version": None,
            "ran_at": None,
            "ci_log_url": None,
        },
        "query_demo": {
            "laboratory": {"query": "Observation?category=laboratory", "count": 6},
            "model_prediction": {
                "query": "Observation?category=https://pharmashed.example/fhir/CodeSystem/observation-category|model-prediction",
                "count": 36,
            },
        },
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    sites_doc = make_sites()
    (FIXTURES_DIR / "sites.json").write_text(json.dumps(sites_doc, indent=2) + "\n")

    results_doc, draws_index, draws_bin = make_results_and_draws(sites_doc["sites"], rng)
    (FIXTURES_DIR / "results.json").write_text(json.dumps(results_doc, indent=2) + "\n")
    (FIXTURES_DIR / "draws_index.json").write_text(json.dumps(draws_index, indent=2) + "\n")
    (FIXTURES_DIR / "draws.bin").write_bytes(draws_bin)

    (FIXTURES_DIR / "checks.json").write_text(json.dumps(make_checks(), indent=2) + "\n")
    (FIXTURES_DIR / "methodology.json").write_text(json.dumps(make_methodology(), indent=2) + "\n")
    (FIXTURES_DIR / "provenance.json").write_text(
        json.dumps(make_provenance(results_doc), indent=2) + "\n"
    )
    (FIXTURES_DIR / "fhir_index.json").write_text(
        json.dumps(make_fhir_index(), indent=2) + "\n"
    )

    print(f"[{datetime.now(UTC).isoformat()}] wrote fixtures to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
