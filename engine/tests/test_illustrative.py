"""Illustrative status (D33/D36): declared placeholders that must never look sourced."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from pharmashed.consumption import ConsumptionRow, load_consumption
from pharmashed.export import export_build
from pharmashed.montecarlo import RunContext
from pharmashed.params import ParamRow, load_drug_params

NOTE = "illustrative — not sourced (D33)"
REPO = Path(__file__).resolve().parents[2]


def _param(**kw) -> dict:
    base = dict(drug="atenolol", param="fe", distribution="fixed", value="0.5", status="illustrative", source_note=NOTE)
    base.update(kw)
    return base


def test_illustrative_param_row_is_valid():
    row = ParamRow(**_param())
    assert row.status == "illustrative"


@pytest.mark.parametrize("field", ["source_url", "source_title", "evidence_quote"])
def test_illustrative_param_must_not_carry_a_citation(field):
    with pytest.raises(ValidationError, match="must not carry"):
        ParamRow(**_param(**{field: "https://example.org/x" if field == "source_url" else "x"}))


def test_illustrative_param_must_say_so():
    with pytest.raises(ValidationError, match="illustrative"):
        ParamRow(**_param(source_note="from a paper"))


def test_illustrative_param_still_gets_range_checks():
    with pytest.raises(ValidationError, match="outside"):
        ParamRow(**_param(value="1.5"))  # fe is a fraction


def test_illustrative_consumption_row_rules():
    ok = ConsumptionRow(
        country="FR", drug="atenolol", status="illustrative", source_note=NOTE,
        granularity="molecule", ddd_per_1000_per_day=8.0,
    )
    assert ok.status == "illustrative"
    with pytest.raises(ValidationError, match="must not carry"):
        ConsumptionRow(
            country="FR", drug="atenolol", status="illustrative", source_note=NOTE,
            granularity="molecule", ddd_per_1000_per_day=8.0, source_url="https://example.org",
        )


def test_shipped_tables_pass_strict_mode_and_are_all_illustrative():
    params, dev_used = load_drug_params(REPO / "data/params/drug_parameters.csv", mode="strict")
    assert not dev_used  # nothing was filled from the dev placeholder file
    assert set(params) >= {"atenolol", "citalopram"}
    cons = load_consumption(REPO / "data/consumption/consumption.csv", mode="strict")
    assert cons and all(r.status in ("illustrative", "sourced") for r in cons.values())


def test_country_keys_in_the_values_file_are_strings_not_booleans():
    """An unquoted NO parses as false in YAML; the values file must quote it."""
    values = yaml.safe_load((REPO / "data/params/illustrative_values.yaml").read_text())
    assert set(values["consumption"]["country_factor"]) == {"FR", "BE", "IT", "PT", "NO"}


def test_run_metadata_is_honest_about_illustrative_inputs(tmp_path):
    ctx = RunContext.from_paths(mode="strict")
    assert ctx.illustrative_count() > 0 and ctx.sourced_count() == 0
    assert not ctx.all_inputs_sourced()
    export_build(ctx, tmp_path)
    meta = json.loads((tmp_path / "results.json").read_text())["meta"]
    assert meta["dev_placeholders"] is False
    assert meta["all_params_cited"] is False
    assert meta["param_count"] == 42  # drug parameter rows, not the number of results
    prov = json.loads((tmp_path / "provenance.json").read_text())
    assert prov["param:atenolol:fe"]["status"] == "illustrative"
    assert prov["param:atenolol:fe"]["source_url"] is None
    assert prov["consumption:FR:atenolol"]["status"] == "illustrative"


def test_real_population_reaches_the_model(tmp_path):
    """Sites carry real GHS-POP populations, so results are not all zero and vary by site."""
    ctx = RunContext.from_paths(mode="strict")
    assert sum(1 for s in ctx.sites if s.population_buffer > 0) >= len(ctx.sites) - 5
    export_build(ctx, tmp_path)
    scores = {e["score"] for e in json.loads((tmp_path / "results.json").read_text())["results"]}
    assert len(scores) > 20
