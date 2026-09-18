"""Tests for M12 consistency checks (run against fixture-frozen data)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pharmashed.checks.observed import DRUG_TO_COMPOUND, CITY_TO_SCOPE, load_observed, lookup
from pharmashed.checks.run import _check_c1, _check_c2, _check_c3, _check_c4, _check_c5, _verify_frozen, FrozenIntegrityError
from pharmashed.contracts import Checks
from pharmashed.export import export_build, sha256_file
from pharmashed.montecarlo import RunContext

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_fixture_frozen(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal frozen snapshot for testing (uses dev mode + low draws)."""
    ctx = RunContext.from_paths(mode="dev")
    ctx.n_draws = 30
    ctx.n_stored = 30

    frozen_dir = tmp_path / "frozen"
    frozen_dir.mkdir()

    results_path = export_build(ctx, frozen_dir, frozen_tag="predictions-frozen-test")
    sha = sha256_file(results_path)

    frozen_json = {
        "sha256": sha,
        "frozen_tag": "predictions-frozen-test",
        "engine_version": "0.0.0",
        "git_commit": "test",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (frozen_dir / "FROZEN.json").write_text(json.dumps(frozen_json))

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    # Copy methodology.json for C5
    import shutil
    shutil.copy(frozen_dir / "methodology.json", build_dir / "methodology.json")

    return frozen_dir, build_dir


# --- observed reader tests ---

def test_drug_to_compound_mapping():
    assert DRUG_TO_COMPOUND["paracetamol"] == "acetaminophen"
    assert DRUG_TO_COMPOUND["carbamazepine"] == "carbamazepine"


def test_city_to_scope_mapping():
    assert CITY_TO_SCOPE["TLS"] == "Toulouse"
    assert CITY_TO_SCOPE["OSL"] == "Oslo"


def test_load_observed_returns_rows():
    rows = load_observed()
    assert len(rows) > 0
    assert "compound" in rows[0]
    assert "metric" in rows[0]


def test_lookup_irbesartan_detection():
    rows = load_observed()
    val = lookup(rows, "irbesartan", "detection_frequency", "all_sites")
    assert val == pytest.approx(73.0)


def test_lookup_paracetamol_max_ghent():
    rows = load_observed()
    val = lookup(rows, "acetaminophen", "max_concentration", "Ghent")
    assert val == pytest.approx(16789.0)


def test_lookup_missing_returns_none():
    rows = load_observed()
    val = lookup(rows, "nonexistent", "metric", "scope")
    assert val is None


# --- frozen verification tests ---

def test_verify_frozen_passes(tmp_path):
    frozen_dir, _ = _build_fixture_frozen(tmp_path)
    record = _verify_frozen(frozen_dir)
    assert "sha256" in record


def test_verify_frozen_fails_on_tamper(tmp_path):
    frozen_dir, _ = _build_fixture_frozen(tmp_path)
    # Tamper with results.json
    p = frozen_dir / "results.json"
    p.write_text(p.read_text() + " ")
    with pytest.raises(FrozenIntegrityError, match="SHA-256"):
        _verify_frozen(frozen_dir)


def test_verify_frozen_fails_missing_frozen_json(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    (d / "results.json").write_text("{}")
    with pytest.raises(FrozenIntegrityError, match="FROZEN.json"):
        _verify_frozen(d)


# --- consistency check tests ---

def test_c1_runs(tmp_path):
    frozen_dir, _ = _build_fixture_frozen(tmp_path)
    results = json.loads((frozen_dir / "results.json").read_text())
    obs = load_observed()
    out = _check_c1(results["results"], obs)
    assert out["status"] in ("pass", "fail", "unavailable")
    assert "data" in out


def test_c2_city_order(tmp_path):
    frozen_dir, _ = _build_fixture_frozen(tmp_path)
    results = json.loads((frozen_dir / "results.json").read_text())
    out = _check_c2(results["results"])
    assert out["status"] in ("pass", "fail")
    assert "predicted_order" in out["data"]
    assert len(out["data"]["predicted_order"]) == 5


def test_c3_oslo_not_first(tmp_path):
    frozen_dir, _ = _build_fixture_frozen(tmp_path)
    results = json.loads((frozen_dir / "results.json").read_text())
    c2 = _check_c2(results["results"])
    c3 = _check_c3(c2)
    assert c3["status"] in ("pass", "fail")
    assert "oslo_rank" in c3["data"]


def test_c4_runs(tmp_path):
    frozen_dir, _ = _build_fixture_frozen(tmp_path)
    results = json.loads((frozen_dir / "results.json").read_text())
    obs = load_observed()
    out = _check_c4(results["results"], obs)
    assert out["status"] in ("pass", "fail")
    assert "rows" in out["data"]
    assert len(out["data"]["rows"]) == 5


def test_c5_runs(tmp_path):
    frozen_dir, build_dir = _build_fixture_frozen(tmp_path)
    out = _check_c5(build_dir / "methodology.json")
    assert out["status"] in ("pass", "fail", "unavailable")


def test_c5_unavailable_without_methodology(tmp_path):
    out = _check_c5(tmp_path / "no_such_file.json")
    assert out["status"] == "unavailable"


def test_run_checks_writes_json(tmp_path):
    from pharmashed.checks.run import run_checks

    frozen_dir, build_dir = _build_fixture_frozen(tmp_path)
    out_path = run_checks(frozen_dir=frozen_dir, build_dir=build_dir)
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    checks = Checks.model_validate(data)
    assert len(checks.checks) == 5
    check_ids = {c.id for c in checks.checks}
    assert check_ids == {"C1", "C2", "C3", "C4", "C5"}


def test_illustrative_label_when_not_all_cited(tmp_path):
    from pharmashed.checks.run import run_checks

    frozen_dir, build_dir = _build_fixture_frozen(tmp_path)
    out_path = run_checks(frozen_dir=frozen_dir, build_dir=build_dir)
    data = json.loads(out_path.read_text())
    # Dev mode → not all_params_cited → illustrative label should appear
    checks = Checks.model_validate(data)
    any_labelled = any(
        "illustrative_label" in c.data
        for c in checks.checks
    )
    assert any_labelled, "expected illustrative_label in at least one check"
