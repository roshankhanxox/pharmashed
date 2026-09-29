"""Tests for M14 FHIR builder."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pharmashed.export import export_build
from pharmashed.fhir.builder import (
    build_locations,
    build_groups,
    build_consumption_observations,
    build_prediction_observations,
    build_all,
    _OAH_PREDICTION_PROFILE,
    _OAH_LOCATION_PROFILE,
)
from pharmashed.checks.fhir_obs import build_reference_observations
from pharmashed.montecarlo import RunContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONSUMPTION_CSV = _REPO_ROOT / "data" / "consumption" / "consumption.csv"


def _minimal_build(tmp_path: Path) -> Path:
    ctx = RunContext.from_paths(mode="dev")
    ctx.n_draws = 30
    ctx.n_stored = 30
    export_build(ctx, tmp_path)
    return tmp_path


# --- Location tests ---

def test_locations_have_oah_profile():
    sites_json = {
        "sites": [
            {"id": "TLS-001", "name": "Test", "lonlat": [1.4, 43.6],
             "size_class": "M", "city": "TLS", "population_buffer": 500}
        ]
    }
    locs = build_locations(sites_json)
    assert len(locs) == 1
    profiles = locs[0]["meta"]["profile"]
    assert _OAH_LOCATION_PROFILE in profiles


def test_location_position_set():
    sites_json = {
        "sites": [
            {"id": "TLS-001", "name": "X", "lonlat": [1.45, 43.61],
             "size_class": "S", "city": "TLS", "population_buffer": 0}
        ]
    }
    loc = build_locations(sites_json)[0]
    assert loc["position"]["longitude"] == pytest.approx(1.45)
    assert loc["position"]["latitude"] == pytest.approx(43.61)


def test_location_id_pattern():
    sites_json = {
        "sites": [
            {"id": "GNT-003", "name": "Y", "lonlat": [3.72, 51.05],
             "size_class": "L", "city": "GNT", "population_buffer": 1000}
        ]
    }
    loc = build_locations(sites_json)[0]
    assert loc["id"] == "site-GNT-003"


# --- Group tests ---

def test_groups_one_per_country():
    groups = build_groups(["FR", "BE", "FR", "IT"])
    ids = {g["id"] for g in groups}
    assert ids == {"pop-FR", "pop-BE", "pop-IT"}


def test_group_type_person():
    groups = build_groups(["NO"])
    assert groups[0]["type"] == "person"
    assert groups[0]["actual"] is False


# --- Consumption Observation tests ---

def test_consumption_obs_resource_type():
    obs = build_consumption_observations(_CONSUMPTION_CSV)
    assert all(o["resourceType"] == "Observation" for o in obs)


def test_consumption_obs_count():
    obs = build_consumption_observations(_CONSUMPTION_CSV)
    assert len(obs) == 30  # 5 countries × 6 drugs


def test_consumption_obs_id_pattern():
    obs = build_consumption_observations(_CONSUMPTION_CSV)
    ids = {o["id"] for o in obs}
    assert "cons-FR-carbamazepine" in ids


# --- Prediction Observation tests ---

def test_prediction_obs_oah_profile(tmp_path):
    build_dir = _minimal_build(tmp_path)
    results = json.loads((build_dir / "results.json").read_text())
    obs = build_prediction_observations(results)
    assert len(obs) > 0
    for o in obs:
        assert _OAH_PREDICTION_PROFILE in o["meta"]["profile"]


def test_prediction_obs_has_six_components(tmp_path):
    build_dir = _minimal_build(tmp_path)
    results = json.loads((build_dir / "results.json").read_text())
    obs = build_prediction_observations(results)
    for o in obs:
        assert len(o["component"]) == 6


def test_prediction_obs_id_deterministic(tmp_path):
    build_dir = _minimal_build(tmp_path)
    results = json.loads((build_dir / "results.json").read_text())
    obs = build_prediction_observations(results)
    ids = {o["id"] for o in obs}
    # Every id should start with 'pred-'
    assert all(oid.startswith("pred-") for oid in ids)


# --- Reference Observation tests (via checks/fhir_obs.py) ---

def test_reference_obs_resource_type():
    obs = build_reference_observations()
    assert all(o["resourceType"] == "Observation" for o in obs)


def test_reference_obs_category_laboratory():
    obs = build_reference_observations()
    for o in obs:
        cats = [c["code"] for cat in o.get("category", []) for c in cat.get("coding", [])]
        assert "laboratory" in cats


def test_reference_obs_has_value_quantity():
    obs = build_reference_observations()
    assert len(obs) > 0
    for o in obs:
        assert "valueQuantity" in o
        assert "value" in o["valueQuantity"]


# --- build_all integration ---

def test_build_all_writes_bundles(tmp_path):
    build_dir = _minimal_build(tmp_path)
    out_dir = tmp_path / "fhir_out"
    ref = build_reference_observations()
    index = build_all(build_dir, out_dir, ref_obs=ref)

    expected_bundles = ["terminology", "locations", "consumption", "reference-measurements"]
    for name in expected_bundles:
        assert (out_dir / f"{name}.json").exists(), f"{name}.json not written"
    assert (out_dir / "fhir_index.json").exists()


def test_build_all_city_bundles(tmp_path):
    build_dir = _minimal_build(tmp_path)
    out_dir = tmp_path / "fhir_out"
    build_all(build_dir, out_dir)
    city_bundles = list(out_dir.glob("predictions-*.json"))
    assert len(city_bundles) == 5  # one per city


def test_fhir_index_has_counts(tmp_path):
    build_dir = _minimal_build(tmp_path)
    out_dir = tmp_path / "fhir_out"
    ref = build_reference_observations()
    index = build_all(build_dir, out_dir, ref_obs=ref)
    assert index["resource_counts"].get("Observation", 0) > 0


def test_bundles_are_valid_json(tmp_path):
    build_dir = _minimal_build(tmp_path)
    out_dir = tmp_path / "fhir_out"
    build_all(build_dir, out_dir)
    for p in out_dir.glob("*.json"):
        data = json.loads(p.read_text())
        assert "resourceType" in data or "resource_counts" in data  # bundle or index


# --- shape rules the HL7 validator enforces against the OneAquaHealth profiles ---------------------


def _built(tmp_path: Path):
    build_dir = _minimal_build(tmp_path)
    out = tmp_path / "fhir"
    index = build_all(build_dir, out, ref_obs=build_reference_observations())
    return out, index


def test_every_bundle_entry_has_a_fullurl_matching_its_resource(tmp_path):
    """Entries outside transactions need a fullUrl, and relative references resolve against it."""
    out, index = _built(tmp_path)
    for b in index["bundles"]:
        bundle = json.loads((out / f"{b['name']}.json").read_text())
        for entry in bundle["entry"]:
            r = entry["resource"]
            assert entry["fullUrl"].endswith(f"/{r['resourceType']}/{r['id']}"), (b["name"], r["id"])


def test_locations_follow_the_real_oah_profile(tmp_path):
    """Profile is location-oah (location-oah-indicators does not exist); it requires identifier, name, mode=instance."""
    assert _OAH_LOCATION_PROFILE.endswith("/StructureDefinition/location-oah")
    site = {"id": "TLS-01", "city": "TLS", "size_class": "S", "lonlat": [1.4, 43.6], "population_buffer": 500}
    loc = build_locations({"sites": [site]})[0]
    assert loc["mode"] == "instance"
    assert loc["identifier"] and loc["name"]


def test_predictions_have_the_performer_and_effective_time_the_profile_requires(tmp_path):
    build_dir = _minimal_build(tmp_path)
    results = json.loads((build_dir / "results.json").read_text())
    obs = build_prediction_observations(results)[0]
    assert obs["performer"] == [{"reference": "Organization/pharmashed"}]
    assert obs["effectiveDateTime"] == results["meta"]["generated_at"]


def test_the_performing_organization_is_in_the_locations_bundle(tmp_path):
    out, _ = _built(tmp_path)
    locations = json.loads((out / "locations.json").read_text())
    assert any(e["resource"]["resourceType"] == "Organization" and e["resource"]["id"] == "pharmashed"
               for e in locations["entry"])


def test_every_tag_names_its_code_system_and_uses_a_defined_code(tmp_path):
    """A code without a system cannot be validated; tag codes must exist in our tags CodeSystem."""
    out, index = _built(tmp_path)
    tags_cs = json.loads((_REPO_ROOT / "fhir" / "terminology" / "CodeSystem-pharmashed-tags.json").read_text())
    defined = {c["code"]: c["display"] for c in tags_cs["concept"]}
    seen = set()
    for b in index["bundles"]:
        if b["name"] in ("terminology", "oah-examples"):
            continue
        for entry in json.loads((out / f"{b['name']}.json").read_text())["entry"]:
            for tag in entry["resource"].get("meta", {}).get("tag", []):
                assert tag["system"] == tags_cs["url"], (b["name"], tag)
                assert tag["code"] in defined, tag
                assert tag.get("display", defined[tag["code"]]) == defined[tag["code"]], tag  # display must match
                seen.add(tag["code"])
    assert {"synthetic", "model-output"} <= seen


def test_reference_measurement_ids_are_valid_fhir_ids():
    import re

    for obs in build_reference_observations():
        assert re.fullmatch(r"[A-Za-z0-9\-.]{1,64}", obs["id"]), obs["id"]


def test_our_location_extension_is_defined_in_the_terminology_folder():
    ext = json.loads((_REPO_ROOT / "fhir" / "terminology" / "StructureDefinition-pharmashed-site-size-class.json").read_text())
    site = {"id": "TLS-01", "city": "TLS", "size_class": "S", "lonlat": [1.4, 43.6]}
    used = build_locations({"sites": [site]})[0]["extension"][0]["url"]
    assert ext["url"] == used


def test_the_index_starts_as_unvalidated_so_a_rebuild_cannot_keep_a_stale_pass(tmp_path):
    _, index = _built(tmp_path)
    assert index["validation"]["status"] == "unknown" and index["validation"]["ran_at"] is None
