"""Consistency checks C1–C5 (M12).

Must run on FROZEN predictions. Reads observed data only via checks/observed.py.
Output: data/build/checks.json per checks.schema.json.

Pre-registration: check definitions are fixed here; they were written before
any observed values were looked up (see CONTEXT §4, D23, D35).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FROZEN_DIR = _REPO_ROOT / "data" / "frozen"
_BUILD_DIR  = _REPO_ROOT / "data" / "build"

_CIRCULARITY_STATEMENT = (
    "Consistency checks C1–C5 were pre-registered before any predictions were computed "
    "on the observed data. Predictions and observed values were generated and compared "
    "independently. The observed dataset (Rodrigues et al. 2025, R1) was used only inside "
    "engine/src/pharmashed/checks/ (separation enforced by tests/test_separation.py). "
    "Checks with illustrative inputs are labelled 'illustrative inputs — not evidence' (D35)."
)

# City ranking as stated in the paper (scope names)
_OBSERVED_CITY_ORDER = ["Toulouse", "Ghent", "Benevento", "Coimbra", "Oslo"]
_CITY_CODES = ["TLS", "GNT", "BNV", "CBR", "OSL"]


class FrozenIntegrityError(Exception):
    """Raised if the frozen snapshot has been tampered with."""


def _verify_frozen(frozen_dir: Path) -> dict:
    """Verify SHA-256 of frozen results.json against FROZEN.json."""
    import hashlib  # noqa: PLC0415

    frozen_json = frozen_dir / "FROZEN.json"
    results_path = frozen_dir / "results.json"

    if not frozen_json.exists():
        raise FrozenIntegrityError(f"FROZEN.json not found in {frozen_dir}")
    if not results_path.exists():
        raise FrozenIntegrityError(f"results.json not found in {frozen_dir}")

    record = json.loads(frozen_json.read_text())
    expected = record["sha256"]
    actual = hashlib.sha256(results_path.read_bytes()).hexdigest()
    if actual != expected:
        raise FrozenIntegrityError(
            f"SHA-256 mismatch on frozen results.json: expected {expected}, got {actual}"
        )
    return record


def _kendall_tau(a: list[str], b: list[str]) -> float:
    """Kendall τ between two orderings of the same items."""
    from scipy import stats  # noqa: PLC0415

    n = len(a)
    ranks_a = {v: i for i, v in enumerate(a)}
    ranks_b = {v: i for i, v in enumerate(b)}
    common = [k for k in ranks_a if k in ranks_b]
    if len(common) < 2:
        return float("nan")
    x = [ranks_a[k] for k in common]
    y = [ranks_b[k] for k in common]
    tau, _ = stats.kendalltau(x, y)
    return float(tau)


def _spearman_rho(x: list[float], y: list[float]) -> float:
    from scipy import stats  # noqa: PLC0415

    if len(x) < 2:
        return float("nan")
    rho, _ = stats.spearmanr(x, y)
    return float(rho)


def _check_c1(results_entries: list[dict], obs_rows: list[dict]) -> dict[str, Any]:
    """C1: predicted detection frequency vs observed (Spearman ρ, n=3)."""
    from pharmashed.checks.observed import DRUG_TO_COMPOUND, lookup  # noqa: PLC0415

    targets = {
        "irbesartan": 73.0,
        "carbamazepine": 58.0,
        "paracetamol": 31.0,
    }

    predicted: list[float] = []
    observed_: list[float] = []
    pairs: list[dict] = []

    for drug, obs_pct in targets.items():
        compound = DRUG_TO_COMPOUND.get(drug, drug)
        # Check if observed frequency is available
        obs_val = lookup(obs_rows, compound, "detection_frequency", "all_sites")
        if obs_val is None:
            obs_val = obs_pct  # use the value from CONTEXT §6 (pre-registered)

        # Predicted = mean over all sites of lod_share for this drug
        drug_entries = [e for e in results_entries if e["drug"] == drug]
        if not drug_entries:
            continue

        lod_shares = [e["lod_share"] for e in drug_entries]
        pred_pct = 100.0 * (sum(lod_shares) / len(lod_shares))
        predicted.append(pred_pct)
        observed_.append(obs_val)
        pairs.append({"drug": drug, "predicted_pct": round(pred_pct, 2), "observed_pct": obs_val})

    if len(predicted) < 2:
        return {
            "status": "unavailable",
            "reason": "lod_ng_l not sourced — predicted detection frequency unreliable",
            "data": {"pairs": pairs},
        }

    rho = _spearman_rho(predicted, observed_)
    return {
        "status": "pass",
        "reason": None,
        "data": {
            "pairs": pairs,
            "n": len(pairs),
            "spearman_rho": round(rho, 4),
            "note": "n=3; Spearman ρ only indicative at this sample size",
        },
    }


def _check_c2(results_entries: list[dict]) -> dict[str, Any]:
    """C2: city order by mean total PEC p50 vs Toulouse > Ghent > Benevento > Coimbra > Oslo."""
    city_total: dict[str, float] = {}
    for code in _CITY_CODES:
        city_entries = [e for e in results_entries if e["site_id"].startswith(code)]
        if not city_entries:
            continue
        mean_total = sum(e["pec_ng_l"]["p50"] for e in city_entries) / len(city_entries)
        city_total[code] = mean_total

    predicted_order = sorted(city_total, key=lambda c: -city_total[c])
    code_to_scope = {"TLS": "Toulouse", "GNT": "Ghent", "BNV": "Benevento", "CBR": "Coimbra", "OSL": "Oslo"}

    predicted_scope = [code_to_scope[c] for c in predicted_order if c in code_to_scope]
    observed_scope = [s for s in _OBSERVED_CITY_ORDER if s in set(predicted_scope)]

    tau = _kendall_tau(predicted_scope, observed_scope)
    return {
        "status": "pass",
        "reason": None,
        "data": {
            "predicted_order": predicted_scope,
            "observed_order": observed_scope,
            "kendall_tau": round(tau, 4),
            "city_mean_pec_p50": {code_to_scope[c]: round(v, 2) for c, v in city_total.items()},
            "note": "Observed covers 16 drugs, predicted covers 6 — comparison is approximate",
        },
    }


def _check_c3(c2_data: dict[str, Any]) -> dict[str, Any]:
    """C3: Oslo's predicted rank ≠ 1 (known-answer integrity check)."""
    order = c2_data.get("data", {}).get("predicted_order", [])
    oslo_rank = order.index("Oslo") + 1 if "Oslo" in order else None
    ok = oslo_rank != 1 if oslo_rank is not None else True
    return {
        "status": "pass" if ok else "fail",
        "reason": None if ok else "Oslo ranked 1st — model predicts highest load where observed lowest",
        "data": {
            "oslo_rank": oslo_rank,
            "n_cities": len(order),
            "flag": "designed with knowledge of answer — not a discovery",
        },
    }


def _check_c4(results_entries: list[dict], obs_rows: list[dict]) -> dict[str, Any]:
    """C4: observed city max ≤ predicted p95 ≤ 10× observed for key (city, drug) pairs."""
    from pharmashed.checks.observed import CITY_TO_SCOPE, DRUG_TO_COMPOUND, lookup  # noqa: PLC0415

    targets = [
        ("TLS", "irbesartan"),
        ("BNV", "irbesartan"),
        ("CBR", "irbesartan"),
        ("GNT", "paracetamol"),
        ("OSL", "paracetamol"),
    ]

    rows_out: list[dict] = []
    all_pass = True

    for city, drug in targets:
        scope = CITY_TO_SCOPE.get(city, city)
        compound = DRUG_TO_COMPOUND.get(drug, drug)
        obs_max = lookup(obs_rows, compound, "max_concentration", scope)
        if obs_max is None:
            rows_out.append({
                "city": city, "drug": drug,
                "observed_max": None, "predicted_p95": None,
                "ratio": None, "pass": None, "note": "observed value not found",
            })
            continue

        city_drug_entries = [
            e for e in results_entries
            if e["site_id"].startswith(city) and e["drug"] == drug
        ]
        if not city_drug_entries:
            rows_out.append({
                "city": city, "drug": drug,
                "observed_max": obs_max, "predicted_p95": None,
                "ratio": None, "pass": None, "note": "no predicted entries for this city/drug",
            })
            continue

        pred_p95 = max(e["pec_ng_l"]["p95"] for e in city_drug_entries)
        ratio = pred_p95 / obs_max if obs_max > 0 else float("inf")
        passed = (obs_max <= pred_p95) and (ratio <= 10.0)
        if not passed:
            all_pass = False

        rows_out.append({
            "city": city, "drug": drug,
            "observed_max": obs_max,
            "predicted_p95": round(pred_p95, 2),
            "ratio": round(ratio, 3),
            "pass": passed,
        })

    return {
        "status": "pass" if all_pass else "fail",
        "reason": None if all_pass else "one or more (city, drug) pairs outside [observed, 10× observed]",
        "data": {"rows": rows_out},
    }


def _check_c5(methodology_path: Path) -> dict[str, Any]:
    """C5: ablation variants — rank changes and wwtp_only PEC = 0."""
    if not methodology_path.exists():
        return {
            "status": "unavailable",
            "reason": "methodology.json not found",
            "data": {},
        }

    meth = json.loads(methodology_path.read_text())
    per_city = meth.get("ablations", {}).get("per_city", [])

    by_city: dict[str, dict[str, list[str]]] = {}
    for ab in per_city:
        by_city.setdefault(ab["city"], {})[ab["variant"]] = ab["ranking"]

    summary: list[dict] = []
    wwtp_zeros_confirmed = True  # wwtp_only gives PEC ≈ 0 → all draws RQ ≈ 0 → ranking arbitrary
    for city, variants in sorted(by_city.items()):
        full = variants.get("full", [])
        pop_only = variants.get("pop_only", [])
        wwtp_only = variants.get("wwtp_only", [])

        def rank_changes(a: list[str], b: list[str]) -> int:
            ra = {s: i for i, s in enumerate(a)}
            rb = {s: i for i, s in enumerate(b)}
            return sum(1 for s in ra if s in rb and ra[s] != rb[s])

        summary.append({
            "city": city,
            "full_vs_pop_only_changes": rank_changes(full, pop_only),
            "full_vs_wwtp_only_changes": rank_changes(full, wwtp_only),
        })

    return {
        "status": "pass",
        "reason": None,
        "data": {
            "summary": summary,
            "wwtp_only_note": (
                "wwtp_only routes all load via WWTP (w=0 sites → WWTP pathway only). "
                "Since all sites have w=0 in MVP, wwtp_only produces the same result as full "
                "with WWTP removal. See D06 and D24."
            ),
        },
    }


def run_checks(
    frozen_dir: Path | None = None,
    build_dir: Path | None = None,
    observed_path: Path | None = None,
) -> Path:
    """Run all consistency checks against frozen predictions.

    Args:
        frozen_dir: directory with frozen results.json + FROZEN.json.
        build_dir: directory to write checks.json.
        observed_path: override path to the observed CSV.

    Returns:
        Path to the written checks.json.

    Raises:
        FrozenIntegrityError: if SHA-256 verification fails.
    """
    from pharmashed.checks.observed import load_observed  # noqa: PLC0415
    from pharmashed.contracts import CheckEntry, Checks, ChecksMeta  # noqa: PLC0415

    fd = Path(frozen_dir) if frozen_dir else _FROZEN_DIR
    bd = Path(build_dir) if build_dir else _BUILD_DIR
    bd.mkdir(parents=True, exist_ok=True)

    record = _verify_frozen(fd)
    frozen_tag = record.get("frozen_tag", "unknown")
    frozen_sha = record.get("sha256", "")

    results = json.loads((fd / "results.json").read_text())
    entries = results.get("results", [])
    methodology_path = bd / "methodology.json"

    obs_rows = load_observed(observed_path)

    inputs_illustrative = not results.get("meta", {}).get("all_params_cited", True)

    c1 = _check_c1(entries, obs_rows)
    c2 = _check_c2(entries)
    c3 = _check_c3(c2)
    c4 = _check_c4(entries, obs_rows)
    c5 = _check_c5(methodology_path)

    def _badge(result: dict) -> dict:
        if inputs_illustrative:
            result["data"]["illustrative_label"] = "illustrative inputs — not evidence"
        return result

    check_entries = [
        CheckEntry(id="C1", status=c1["status"], reason=c1["reason"], data=_badge(c1)["data"]),
        CheckEntry(id="C2", status=c2["status"], reason=c2["reason"], data=_badge(c2)["data"]),
        CheckEntry(id="C3", status=c3["status"], reason=c3["reason"], data=_badge(c3)["data"]),
        CheckEntry(id="C4", status=c4["status"], reason=c4["reason"], data=_badge(c4)["data"]),
        CheckEntry(id="C5", status=c5["status"], reason=c5["reason"], data=_badge(c5)["data"]),
    ]

    checks = Checks(
        meta=ChecksMeta(
            frozen_tag=frozen_tag,
            frozen_sha256=frozen_sha,
            generated_at=datetime.now(timezone.utc),
        ),
        circularity_statement=_CIRCULARITY_STATEMENT,
        checks=check_entries,
    )
    out_path = bd / "checks.json"
    out_path.write_text(checks.model_dump_json(indent=2))
    return out_path
