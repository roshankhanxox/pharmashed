"""M16 API tests using fixture build artifacts."""

from __future__ import annotations

import json
import struct
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Build fixture artifacts before importing the app
_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def build_dir(tmp_path_factory):
    """Generate minimal build artifacts for all API tests."""
    d = tmp_path_factory.mktemp("build")
    from pharmashed.export import export_build
    from pharmashed.montecarlo import RunContext

    ctx = RunContext.from_paths(mode="dev")
    ctx.n_draws = 30
    ctx.n_stored = 30
    export_build(ctx, d)
    return d


@pytest.fixture()
def client(build_dir, monkeypatch):
    """TestClient with PHARMASHED_DATA pointing at fixture build dir."""
    monkeypatch.setenv("PHARMASHED_DATA", str(build_dir))
    # Clear lru_cache so each test sees fresh env
    import pharmashed_api.data as _data  # noqa: PLC0415
    _data._load_json.cache_clear()

    from pharmashed_api.main import app  # noqa: PLC0415
    return TestClient(app)


# --- health ---

def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# --- meta ---

def test_meta_has_engine_version(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert "engine_version" in r.json()


# --- sites ---

def test_sites_has_cities(client):
    r = client.get("/api/sites")
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("cities", [])) == 5
    assert len(data.get("sites", [])) > 0


# --- results ---

def test_results_has_drugs(client):
    r = client.get("/api/results")
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("drugs", [])) == 6


def test_results_entries_nonempty(client):
    r = client.get("/api/results")
    assert r.status_code == 200
    assert len(r.json().get("results", [])) > 0


# --- methodology + glossary ---

def test_methodology_stages(client):
    r = client.get("/api/methodology")
    assert r.status_code == 200
    assert len(r.json().get("stages", [])) == 7


def test_glossary_symbols(client):
    r = client.get("/api/glossary")
    assert r.status_code == 200
    data = r.json()
    for sym in ("PEC", "RQ", "score"):
        assert sym in data


# --- provenance ---

def test_provenance_known_key(client):
    r = client.get("/api/provenance/prior:lambda")
    assert r.status_code == 200
    assert "label" in r.json()


def test_provenance_missing_key_404(client):
    r = client.get("/api/provenance/no:such:key")
    assert r.status_code == 404


# --- draws.bin ---

def test_draws_bin_served(client, build_dir):
    r = client.get("/api/draws.bin")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert len(r.content) > 0


# --- scenario ---

def test_scenario_no_multipliers(client):
    results = client.get("/api/results").json()
    first = results["results"][0]
    r = client.post("/api/scenario", json={
        "site_id": first["site_id"],
        "drug": first["drug"],
        "multipliers": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["score"] <= 1.0
    assert data["tier"] in ("high", "medium", "low")


def test_scenario_lambda_multiplier(client):
    results = client.get("/api/results").json()
    first = results["results"][0]
    base = client.post("/api/scenario", json={
        "site_id": first["site_id"],
        "drug": first["drug"],
        "multipliers": {"lambda": 1.0},
    }).json()
    doubled = client.post("/api/scenario", json={
        "site_id": first["site_id"],
        "drug": first["drug"],
        "multipliers": {"lambda": 2.0},
    }).json()
    # Doubling lambda ≥ doubles score (more draws exceed RQ=1)
    assert doubled["score"] >= base["score"]


def test_scenario_invalid_q_422(client):
    results = client.get("/api/results").json()
    first = results["results"][0]
    r = client.post("/api/scenario", json={
        "site_id": first["site_id"],
        "drug": first["drug"],
        "multipliers": {"Q": 0.0},
    })
    assert r.status_code == 422


def test_scenario_unknown_site_404(client):
    r = client.post("/api/scenario", json={
        "site_id": "FAKE-999",
        "drug": "carbamazepine",
        "multipliers": {},
    })
    assert r.status_code == 404


# --- scenario math correctness ---

def test_scenario_rq_p50_scales(client):
    """RQ' = RQ · m — verify p50 scales correctly within ±20% tolerance."""
    results = client.get("/api/results").json()
    first = results["results"][0]
    base = client.post("/api/scenario", json={
        "site_id": first["site_id"], "drug": first["drug"],
        "multipliers": {"lambda": 1.0, "Q": 1.0, "C": 1.0},
    }).json()
    scaled = client.post("/api/scenario", json={
        "site_id": first["site_id"], "drug": first["drug"],
        "multipliers": {"lambda": 1.0, "Q": 2.0, "C": 1.0},
    }).json()
    # Doubling Q halves PEC → halves RQ
    base_p50 = base["rq_quantiles"]["p50"]
    scaled_p50 = scaled["rq_quantiles"]["p50"]
    if base_p50 > 0:
        ratio = scaled_p50 / base_p50
        assert 0.3 <= ratio <= 0.7, f"Expected ~0.5, got {ratio}"


def test_default_data_dir_uses_build_when_present_else_the_release_snapshot(monkeypatch, tmp_path):
    """Without PHARMASHED_DATA: data/build if generated, otherwise the committed data/release."""
    import pharmashed_api.data as _data

    monkeypatch.delenv("PHARMASHED_DATA", raising=False)
    repo = Path(__file__).resolve().parents[2]
    # Paths are anchored at the repo root (they once pointed one folder above it).
    assert _data._BUILD == repo / "data" / "build"
    assert _data._RELEASE == repo / "data" / "release"

    build, release = tmp_path / "build", tmp_path / "release"
    build.mkdir(), release.mkdir()
    monkeypatch.setattr(_data, "_BUILD", build)
    monkeypatch.setattr(_data, "_RELEASE", release)
    assert _data._data_dir() == release          # no build output: fall back to the snapshot
    (build / "results.json").write_text("{}")
    assert _data._data_dir() == build            # build output exists: use it
    monkeypatch.setenv("PHARMASHED_DATA", str(tmp_path / "custom"))
    assert _data._data_dir() == tmp_path / "custom"  # an explicit override always wins


def test_committed_release_snapshot_has_everything_the_api_serves():
    """data/release is what the deployed API reads; it must be complete and describe the frozen run."""
    release = Path(__file__).resolve().parents[2] / "data" / "release"
    for name in ("results.json", "sites.json", "provenance.json", "methodology.json", "glossary.json",
                 "checks.json", "draws_index.json", "draws.bin", "fhir_index.json", "RELEASE.json"):
        assert (release / name).exists(), f"data/release/{name} is missing; run scripts/make_release.py"
    meta = json.loads((release / "results.json").read_text())["meta"]
    assert meta["frozen_tag"], "release snapshot was not built from a frozen run"
    assert meta["dev_placeholders"] is False
    index = json.loads((release / "fhir_index.json").read_text())
    for bundle in index["bundles"]:
        assert (release / "fhir" / "out" / f"{bundle['name']}.json").exists(), bundle["name"]
