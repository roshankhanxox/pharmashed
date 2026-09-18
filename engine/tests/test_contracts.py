"""M01 acceptance: fixtures validate against their JSON Schemas, and the
draws.bin binary layout matches draws_index.json."""

import json
import struct
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pharmashed.contracts import (
    Checks,
    DrawsIndex,
    FhirIndex,
    Methodology,
    ProvenanceEntry,
    Results,
    Sites,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "contracts" / "schemas"
FIXTURES_DIR = REPO_ROOT / "contracts" / "fixtures"

SCHEMA_TO_FIXTURE = {
    "sites": "sites.json",
    "results": "results.json",
    "draws": "draws_index.json",
    "checks": "checks.json",
    "methodology": "methodology.json",
    "provenance": "provenance.json",
    "fhir_index": "fhir_index.json",
}


@pytest.mark.parametrize("schema_name,fixture_name", sorted(SCHEMA_TO_FIXTURE.items()))
def test_fixture_validates_against_schema(schema_name: str, fixture_name: str):
    schema = json.loads((SCHEMAS_DIR / f"{schema_name}.schema.json").read_text())
    data = json.loads((FIXTURES_DIR / fixture_name).read_text())
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(data))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_draws_bin_matches_index():
    index = json.loads((FIXTURES_DIR / "draws_index.json").read_text())
    draws_bin = (FIXTURES_DIR / "draws.bin").read_bytes()

    assert index["dtype"] == "float32"
    assert index["endianness"] == "little"

    expected_len = sum(e["count"] for e in index["entries"]) * 4
    assert len(draws_bin) == expected_len

    for entry in index["entries"]:
        start = entry["offset"] * 4
        end = start + entry["count"] * 4
        block = struct.unpack(f"<{entry['count']}f", draws_bin[start:end])
        assert len(block) == entry["count"]


def test_draws_offsets_match_results():
    results = json.loads((FIXTURES_DIR / "results.json").read_text())
    index = json.loads((FIXTURES_DIR / "draws_index.json").read_text())
    index_by_key = {(e["site_id"], e["drug"]): e for e in index["entries"]}

    for r in results["results"]:
        key = (r["site_id"], r["drug"])
        assert key in index_by_key
        assert index_by_key[key]["offset"] == r["draws"]["offset"]
        assert index_by_key[key]["count"] == r["draws"]["count"]


@pytest.mark.parametrize(
    "model,fixture_name",
    [
        (Sites, "sites.json"),
        (Results, "results.json"),
        (DrawsIndex, "draws_index.json"),
        (Checks, "checks.json"),
        (Methodology, "methodology.json"),
        (FhirIndex, "fhir_index.json"),
    ],
)
def test_fixture_parses_with_pydantic_model(model, fixture_name: str):
    data = json.loads((FIXTURES_DIR / fixture_name).read_text())
    model.model_validate(data)


def test_provenance_fixture_parses_with_pydantic_model():
    data = json.loads((FIXTURES_DIR / "provenance.json").read_text())
    for entry in data.values():
        ProvenanceEntry.model_validate(entry)
