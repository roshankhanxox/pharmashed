"""Unit tests for assistant tools (M17) — uses fixture build artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def build_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("build")
    from pharmashed.export import export_build
    from pharmashed.montecarlo import RunContext

    ctx = RunContext.from_paths(mode="dev")
    ctx.n_draws = 30
    ctx.n_stored = 30
    export_build(ctx, d)
    return d


@pytest.fixture(autouse=True)
def set_data_env(build_dir, monkeypatch):
    monkeypatch.setenv("PHARMASHED_DATA", str(build_dir))
    import pharmashed_api.data as _data
    _data._load_json.cache_clear()


def test_list_priority_sites_all():
    from pharmashed_api.assistant.tools import list_priority_sites
    result = list_priority_sites()
    assert "sites" in result
    assert len(result["sites"]) <= 5


def test_list_priority_sites_city():
    from pharmashed_api.assistant.tools import list_priority_sites
    result = list_priority_sites(city="TLS")
    assert all(s["site_id"].startswith("TLS") for s in result["sites"])


def test_list_priority_sites_drug():
    from pharmashed_api.assistant.tools import list_priority_sites
    result = list_priority_sites(drug="carbamazepine", limit=3)
    assert all(s["drug"] == "carbamazepine" for s in result["sites"])
    assert len(result["sites"]) <= 3


def test_get_site_profile_returns_drugs():
    from pharmashed_api.assistant.tools import get_site_profile, list_priority_sites
    sites = list_priority_sites(city="TLS")
    site_id = sites["sites"][0]["site_id"]
    profile = get_site_profile(site_id)
    assert profile["site_id"] == site_id
    assert len(profile["drugs"]) == 6


def test_explain_drivers_structure():
    from pharmashed_api.assistant.tools import explain_drivers, list_priority_sites
    sites = list_priority_sites(city="GNT", drug="irbesartan")
    entry = sites["sites"][0]
    result = explain_drivers(entry["site_id"], "irbesartan")
    assert "drivers" in result
    assert "driver_sentence" in result
    assert "flip" in result


def test_run_scenario_baseline():
    from pharmashed_api.assistant.tools import list_priority_sites, run_scenario
    sites = list_priority_sites(drug="carbamazepine")
    site_id = sites["sites"][0]["site_id"]
    result = run_scenario(site_id, "carbamazepine", {"lambda": 1.0, "Q": 1.0, "C": 1.0})
    assert "baseline" in result
    assert "scenario" in result
    assert 0 <= result["scenario"]["score"] <= 1


def test_run_scenario_lambda_increases_score():
    from pharmashed_api.assistant.tools import list_priority_sites, run_scenario
    sites = list_priority_sites(drug="irbesartan")
    site_id = sites["sites"][0]["site_id"]
    base = run_scenario(site_id, "irbesartan", {"lambda": 1.0})
    high = run_scenario(site_id, "irbesartan", {"lambda": 5.0})
    assert high["scenario"]["score"] >= base["scenario"]["score"]


def test_run_scenario_invalid_q():
    from pharmashed_api.assistant.tools import list_priority_sites, run_scenario
    sites = list_priority_sites(drug="atenolol")
    site_id = sites["sites"][0]["site_id"]
    result = run_scenario(site_id, "atenolol", {"Q": 0})
    assert "error" in result


def test_get_provenance_lambda():
    from pharmashed_api.assistant.tools import get_provenance
    result = get_provenance("prior:lambda")
    assert "label" in result
    assert "error" not in result


def test_get_provenance_missing():
    from pharmashed_api.assistant.tools import get_provenance
    result = get_provenance("no:such:key:xyz")
    assert "error" in result


def test_assistant_endpoint_503_without_key(build_dir, monkeypatch):
    monkeypatch.setenv("PHARMASHED_DATA", str(build_dir))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import pharmashed_api.data as _data
    _data._load_json.cache_clear()
    from pharmashed_api.main import app
    client = TestClient(app)
    r = client.post("/api/assistant", json={"question": "hello"})
    assert r.status_code == 503
