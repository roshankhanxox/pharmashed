"""
Generate rich illustrative fixtures: 45 sites × 5 cities × 6 drugs.
Scores vary realistically — red/yellow/green spread — without running the engine.
Output goes to contracts/fixtures/ (overwriting the minimal 2-city placeholders).

All values are ILLUSTRATIVE — round numbers chosen to produce plausible variation.
Run: python scripts/gen_rich_fixtures.py
"""
from __future__ import annotations

import json
import math
import random
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contracts" / "fixtures"
SITES_GEO = ROOT / "data" / "sites" / "sites.geojson"

random.seed(20260918)

DRUGS = ["carbamazepine", "atenolol", "losartan", "irbesartan", "paracetamol", "citalopram"]
N_STORED = 200  # draws per (site, drug)
N_DRAWS = 10_000

# ------------------------------------------------------------------
# City metadata (center coords, zoom, country, pop scale)
# ------------------------------------------------------------------
CITIES = {
    "TLS": {"name": "Toulouse", "country": "FR", "center": [1.4442, 43.6047], "zoom": 11, "pop_scale": 1.0},
    "GNT": {"name": "Ghent",    "country": "BE", "center": [3.7174, 51.0543], "zoom": 11, "pop_scale": 0.6},
    "BNV": {"name": "Benevento","country": "IT", "center": [14.782,  41.130],  "zoom": 12, "pop_scale": 0.3},
    "CBR": {"name": "Coimbra",  "country": "PT", "center": [-8.4294, 40.2033], "zoom": 12, "pop_scale": 0.35},
    "OSL": {"name": "Oslo",     "country": "NO", "center": [10.7522, 59.9139], "zoom": 11, "pop_scale": 0.9},
}

# Site size-class → approximate stream flow multiplier (dilution ∝ flow)
SIZE_FLOW = {"S": 0.5, "M": 1.0, "L": 2.5}

# ------------------------------------------------------------------
# Drug baseline parameters (illustrative, all_params_cited=False)
# PNEC in ng/L, typical fe (excretion fraction), DDD proxy
# ------------------------------------------------------------------
DRUG_PARAMS = {
    # drug: (pnec_ng_l, fe, ddd_proxy, lod_ng_l, in_stream_loss)
    # fe values adjusted so RQ_median spans low–high across drugs at the chosen scale
    "carbamazepine": (500,   0.03, 1.0, 40,  0.05),
    "atenolol":      (10000, 0.65, 1.0, 20,  0.10),  # high PNEC (low ecotox concern)
    "losartan":      (2000,  0.04, 1.0, 30,  0.07),
    "irbesartan":    (500,   0.02, 1.2, 50,  0.04),
    "paracetamol":   (10000, 0.05, 3.0, 100, 0.80),
    "citalopram":    (200,   0.14, 0.3, 15,  0.06),
}

# City × drug consumption multiplier (relative to baseline)
# Higher = more consumption in that city → higher PEC
CITY_CONSUMPTION = {
    "TLS": {"carbamazepine": 1.4, "atenolol": 1.1, "losartan": 1.0, "irbesartan": 2.0, "paracetamol": 1.2, "citalopram": 0.9},
    "GNT": {"carbamazepine": 1.1, "atenolol": 0.9, "losartan": 1.2, "irbesartan": 1.3, "paracetamol": 1.0, "citalopram": 1.1},
    "BNV": {"carbamazepine": 0.8, "atenolol": 1.3, "losartan": 0.7, "irbesartan": 0.9, "paracetamol": 0.8, "citalopram": 0.7},
    "CBR": {"carbamazepine": 0.9, "atenolol": 1.0, "losartan": 0.9, "irbesartan": 1.1, "paracetamol": 0.9, "citalopram": 0.8},
    "OSL": {"carbamazepine": 0.7, "atenolol": 0.8, "losartan": 0.8, "irbesartan": 0.7, "paracetamol": 1.1, "citalopram": 0.6},
}

# Leakage priors by city (illustrative urban leakage differences)
CITY_LAMBDA_MEAN = {
    "TLS": 0.08, "GNT": 0.05, "BNV": 0.12, "CBR": 0.10, "OSL": 0.03,
}

def load_sites() -> list[dict]:
    geo = json.loads(SITES_GEO.read_text())
    return [f["properties"] | {"lonlat": f["geometry"]["coordinates"]} for f in geo["features"]]

def lognormal_samples(mean_val: float, cv: float, n: int) -> list[float]:
    """Lognormal draws with given mean and coefficient of variation."""
    sigma2 = math.log(1 + cv**2)
    mu = math.log(mean_val) - sigma2 / 2
    return [math.exp(random.gauss(mu, math.sqrt(sigma2))) for _ in range(n)]

def compute_rq_draws(site: dict, drug: str) -> list[float]:
    city = site["city"]
    pnec, fe, ddd_proxy, _lod, k = DRUG_PARAMS[drug]
    city_info = CITIES[city]
    pop_scale = city_info["pop_scale"]
    consumption_mult = CITY_CONSUMPTION[city][drug]
    flow_mult = SIZE_FLOW.get(site.get("size_class", "M"), 1.0)
    lam_mean = CITY_LAMBDA_MEAN[city]

    # PEC = (C_drug × λ × pop) / (Q × (1 - k))
    # We embed it as RQ = PEC / PNEC directly from draws
    # Baseline PEC_median = ddd_proxy × fe × consumption_mult × pop_scale × lam_mean / flow_mult / (1-k) × scale_factor
    # Scale chosen so irbesartan at TLS-S-site has median RQ ≈ 1.5
    # (Rodrigues 2025 observed 31,659 ng/L at Toulouse >> PNEC 500 ng/L)
    scale = 120_000
    pec_median = scale * ddd_proxy * fe * consumption_mult * pop_scale * lam_mean / (flow_mult * (1 - k + 0.01))
    rq_median = pec_median / pnec

    # Draw with ~50% CV on PEC (reflects λ, Q, C uncertainty)
    rq_draws = lognormal_samples(rq_median, 0.5, N_STORED)
    return rq_draws

def score_from_rq(rqs: list[float]) -> float:
    return sum(1 for r in rqs if r > 1.0) / len(rqs)

def tier(score: float) -> str:
    if score >= 0.5: return "high"
    if score >= 0.1: return "medium"
    return "low"

def quantiles(rqs: list[float]) -> dict:
    s = sorted(rqs)
    n = len(s)
    def q(p): return s[int(p * (n - 1))]
    return {"p5": q(0.05), "p50": q(0.50), "p95": q(0.95)}

def histogram(rqs: list[float]) -> dict:
    edges = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    counts = [0] * (len(edges) - 1)
    for r in rqs:
        log_r = math.log10(max(r, 1e-9))
        for i in range(len(edges) - 1):
            if edges[i] <= log_r < edges[i + 1]:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return {"log10_edges": edges, "counts": counts}

def drivers(rqs: list[float]) -> list[dict]:
    """Fake but plausible Spearman ρ values — λ drives most, Q second."""
    return [
        {"param": "lambda", "rho": round(random.uniform(0.55, 0.85), 2)},
        {"param": "Q",      "rho": round(-random.uniform(0.30, 0.65), 2)},
        {"param": "C",      "rho": round(random.uniform(0.15, 0.45), 2)},
    ]

def flip_info(score: float, site_id: str, drug: str) -> dict:
    up = None if score >= 0.95 else {"param": "lambda", "multiplier": round(random.uniform(1.2, 3.0), 2), "to_tier": "high" if score < 0.5 else None}
    down = None if score <= 0.02 else {"param": "lambda", "multiplier": round(random.uniform(0.2, 0.8), 2), "to_tier": "low" if score >= 0.1 else None}
    if up and up["to_tier"] is None: up = None
    if down and down["to_tier"] is None: down = None
    return {"up": up, "down": down}

def driver_sentence(drv: list[dict]) -> str:
    top = max(drv, key=lambda d: abs(d["rho"]))
    direction = "positively" if top["rho"] > 0 else "inversely"
    return f"Score is most {direction} correlated with {top['param']} (ρ = {top['rho']:.2f})."

def main():
    sites = load_sites()
    site_ids = [s["id"] for s in sites]

    # Build all (site, drug) RQ draws
    all_rqs: dict[tuple[str, str], list[float]] = {}
    for site in sites:
        for drug in DRUGS:
            all_rqs[(site["id"], drug)] = compute_rq_draws(site, drug)

    # ---------- sites.json ----------
    cities_list = [
        {
            "id": cid,
            "name": info["name"],
            "country": info["country"],
            "center": info["center"],
            "zoom": info["zoom"],
        }
        for cid, info in CITIES.items()
    ]
    sites_list = [
        {
            "id": s["id"],
            "city": s["city"],
            "name": s.get("name", s["id"]),
            "lonlat": s["lonlat"],
            "synthetic": True,
            "size_class": s.get("size_class", "M"),
            "w": s.get("w", 0),
            "valid": s.get("valid", True),
            "population_buffer": s.get("population_buffer", 0),
            "population_source_key": s.get("population_source_key", "pop:pending-m05"),
        }
        for s in sites
    ]
    sites_json = {
        "meta": {"generated_at": "2026-09-18T00:00:00Z", "synthetic": True},
        "cities": cities_list,
        "sites": sites_list,
    }
    (FIXTURES / "sites.json").write_text(json.dumps(sites_json, indent=2))
    print(f"sites.json: {len(sites_list)} sites across {len(cities_list)} cities")

    # ---------- draws.bin + draws_index.json ----------
    draws_entries = []
    draw_buffers: list[float] = []
    offset = 0
    for site in sites:
        for drug in DRUGS:
            rqs = all_rqs[(site["id"], drug)]
            draws_entries.append({
                "site_id": site["id"],
                "drug": drug,
                "offset": offset,
                "count": N_STORED,
            })
            draw_buffers.extend(rqs[:N_STORED])
            offset += N_STORED

    bin_bytes = struct.pack(f"<{len(draw_buffers)}f", *draw_buffers)
    (FIXTURES / "draws.bin").write_bytes(bin_bytes)
    draws_index = {
        "dtype": "float32",
        "endianness": "little",
        "n_stored": N_STORED,
        "entries": draws_entries,
    }
    (FIXTURES / "draws_index.json").write_text(json.dumps(draws_index, indent=2))
    print(f"draws.bin: {len(draw_buffers)} floats ({len(bin_bytes)} bytes)")

    # ---------- results.json ----------
    results_entries = []
    for site in sites:
        for drug in DRUGS:
            rqs = all_rqs[(site["id"], drug)]
            sc = score_from_rq(rqs)
            pnec, fe, ddd_proxy, lod, k = DRUG_PARAMS[drug]
            qs = quantiles(rqs)
            pec_qs = {k2: v * pnec for k2, v in qs.items()}
            drv = drivers(rqs)
            entry = {
                "site_id": site["id"],
                "drug": drug,
                "pec_ng_l": {"p5": round(pec_qs["p5"], 2), "p50": round(pec_qs["p50"], 2), "p95": round(pec_qs["p95"], 2)},
                "rq": {"p5": round(qs["p5"], 4), "p50": round(qs["p50"], 4), "p95": round(qs["p95"], 4)},
                "pnec_ng_l": pnec,
                "lod_ng_l": lod,
                "score": round(sc, 6),
                "tier": tier(sc),
                "lod_share": round(sum(1 for r in rqs if r * pnec < lod) / len(rqs), 4),
                "rank_in_city": 0,   # filled below
                "n_in_city": 9,
                "drivers": drv,
                "driver_sentence": driver_sentence(drv),
                "flip": flip_info(sc, site["id"], drug),
                "histogram": histogram(rqs),
                "draws": {"offset": draws_entries[[e["site_id"] == site["id"] and e["drug"] == drug for e in draws_entries].index(True)]["offset"], "count": N_STORED},
                "provenance_keys": [f"pnec:{drug}", f"prior:lambda", f"cons:{site['city']}:{drug}"],
                "fhir_ids": {"prediction": f"obs-{site['id']}-{drug}"},
            }
            results_entries.append(entry)

    # Fill rank_in_city: for each city × drug sort by score desc
    from collections import defaultdict
    city_drug_groups: dict[tuple, list] = defaultdict(list)
    for e in results_entries:
        city = e["site_id"].split("-")[0]
        city_drug_groups[(city, e["drug"])].append(e)
    for group in city_drug_groups.values():
        group.sort(key=lambda e: e["score"], reverse=True)
        for rank, e in enumerate(group, 1):
            e["rank_in_city"] = rank

    # site_overall
    site_overall = []
    for site in sites:
        sid = site["id"]
        entries = [e for e in results_entries if e["site_id"] == sid]
        best = max(entries, key=lambda e: e["score"])
        city_entries = [e for e in results_entries if e["site_id"].split("-")[0] == site["city"]]
        city_overall_scores = {}
        for e in city_entries:
            sid2 = e["site_id"]
            city_overall_scores[sid2] = city_overall_scores.get(sid2, 0) + e["score"]
        city_ranked = sorted(city_overall_scores.items(), key=lambda x: -x[1])
        rank = next(i + 1 for i, (s, _) in enumerate(city_ranked) if s == sid)
        site_overall.append({
            "site_id": sid,
            "score": round(best["score"], 4),
            "top_drug": best["drug"],
            "rank_in_city": rank,
        })

    # city_summary
    city_summary = []
    for cid in CITIES:
        c_entries = [e for e in results_entries if e["site_id"].startswith(cid)]
        # Count unique sites at each tier (best drug per site)
        site_best_tier: dict[str, str] = {}
        for e in c_entries:
            sid = e["site_id"]
            if sid not in site_best_tier or (e["tier"] == "high") or (site_best_tier[sid] == "low" and e["tier"] == "medium"):
                site_best_tier[sid] = e["tier"]
        city_summary.append({
            "city": cid,
            "high": sum(1 for t in site_best_tier.values() if t == "high"),
            "medium": sum(1 for t in site_best_tier.values() if t == "medium"),
            "low": sum(1 for t in site_best_tier.values() if t == "low"),
        })

    results_json = {
        "meta": {
            "engine_version": "0.0.0-illustrative",
            "generated_at": "2026-09-18T00:00:00Z",
            "seed": 20260918,
            "n_draws": N_DRAWS,
            "n_stored": N_STORED,
            "variant": "full",
            "dev_placeholders": True,
            "frozen_tag": None,
            "param_count": 42,
            "all_params_cited": False,
        },
        "drugs": DRUGS,
        "results": results_entries,
        "site_overall": site_overall,
        "city_summary": city_summary,
    }
    (FIXTURES / "results.json").write_text(json.dumps(results_json, indent=2))

    high_count = sum(1 for e in results_entries if e["tier"] == "high")
    med_count  = sum(1 for e in results_entries if e["tier"] == "medium")
    low_count  = sum(1 for e in results_entries if e["tier"] == "low")
    print(f"results.json: {len(results_entries)} entries — {high_count} high / {med_count} medium / {low_count} low")
    print("City summary:", {c["city"]: f"{c['high']}H/{c['medium']}M/{c['low']}L" for c in city_summary})

    # ---------- provenance.json (minimal additions for new sites) ----------
    prov: dict = {}
    for drug in DRUGS:
        pnec, _, _, _, _ = DRUG_PARAMS[drug]
        prov[f"pnec:{drug}"] = {
            "label": f"PNEC {drug}",
            "value": pnec,
            "unit": "ng/L",
            "distribution": None,
            "source_title": None,
            "source_url": None,
            "source_note": "Illustrative placeholder value; not a sourced PNEC.",
            "status": "todo",
        }
    for cid in CITIES:
        for drug in DRUGS:
            key = f"cons:{cid}:{drug}"
            prov[key] = {
                "label": key,
                "value": 1.0,
                "unit": "DDD/1000/day",
                "distribution": None,
                "source_title": None,
                "source_url": None,
                "source_note": "Illustrative placeholder value; not a sourced parameter.",
                "status": "todo",
            }
    prov["prior:lambda"] = {
        "label": "Leakage fraction λ",
        "value": None,
        "unit": "fraction",
        "distribution": "LogUniform(0.002, 0.15)",
        "source_title": None,
        "source_url": None,
        "source_note": "Prior assumption; not empirically constrained.",
        "status": "assumption",
    }
    (FIXTURES / "provenance.json").write_text(json.dumps(prov, indent=2))
    print(f"provenance.json: {len(prov)} entries")

    print("\nDone. Restart the API to pick up new fixtures.")

if __name__ == "__main__":
    main()
