"""M02 acceptance: drug parameter registry and priors loaders."""

import csv
from pathlib import Path

import numpy as np
import pytest
from pharmashed.params import (
    DRUGS,
    Dist,
    ParamRow,
    UnsourcedParameterError,
    load_drug_params,
    load_priors,
    load_rows,
    provenance_entries,
)
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
PARAMS_CSV = REPO_ROOT / "data" / "params" / "drug_parameters.csv"
PRIORS_YAML = REPO_ROOT / "data" / "params" / "priors.yaml"

CSV_COLUMNS = [
    "drug",
    "param",
    "distribution",
    "value",
    "min",
    "max",
    "unit",
    "source_title",
    "source_url",
    "source_note",
    "evidence_quote",
    "retrieved_at",
    "verified",
    "verify_note",
    "status",
]


def _row(**overrides) -> dict:
    base = dict.fromkeys(CSV_COLUMNS, "")
    base.update(drug="irbesartan", param="fe", status="todo", verified="none")
    base.update(overrides)
    return base


def _todo_file(tmp_path):
    """A 42-row all-todo file (R rows carry the D27 note), the state before values were filled in."""
    from pharmashed.params import PARAMS

    path = tmp_path / "params_todo.csv"
    rows = []
    for drug in DRUGS:
        for param in PARAMS:
            note = "not required: w=0 for all MVP sites" if param == "R" else ""
            rows.append(_row(drug=drug, param=param, source_note=note))
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


# --- shipped file -------------------------------------------------------


def test_shipped_csv_has_42_rows_covering_every_drug():
    rows = load_rows(PARAMS_CSV)
    assert len(rows) == 42
    assert {r.drug for r in rows} == set(DRUGS)
    assert all(r.status in ("sourced", "illustrative", "todo") for r in rows)


def test_shipped_csv_passes_strict_mode_because_illustrative_rows_are_declared():
    """D36: strict mode refuses `todo` rows only (R excepted, D27), and accepts illustrative ones."""
    params, dev_used = load_drug_params(PARAMS_CSV, mode="strict")
    assert set(params) == set(DRUGS)
    assert dev_used is False


def test_todo_file_fails_strict_mode(tmp_path):
    with pytest.raises(UnsourcedParameterError) as exc_info:
        load_drug_params(_todo_file(tmp_path), mode="strict")
    # 42 rows - 6 R rows (optional, CONTEXT D27) = 36
    assert len(exc_info.value.missing) == 36
    assert all(":R" not in m for m in exc_info.value.missing)


def test_shipped_csv_r_rows_have_not_required_note():
    rows = load_rows(PARAMS_CSV)
    r_rows = [r for r in rows if r.param == "R"]
    assert len(r_rows) == 6
    assert all(r.source_note == "not required: w=0 for all MVP sites" for r in r_rows)


# --- ParamRow validation rules -------------------------------------------------------


def test_unknown_drug_rejected():
    with pytest.raises(ValidationError):
        ParamRow(**_row(drug="ibuprofen"))


def test_unknown_param_rejected():
    with pytest.raises(ValidationError):
        ParamRow(**_row(param="half_life"))


def test_sourced_requires_source_url_and_note():
    with pytest.raises(ValidationError, match="source_url"):
        ParamRow(
            **_row(
                status="sourced",
                distribution="fixed",
                value="0.6",
                source_note="p.3",
            )
        )


def test_fixed_distribution_requires_value():
    with pytest.raises(ValidationError, match="needs a value"):
        ParamRow(
            **_row(
                status="sourced",
                distribution="fixed",
                source_url="https://example.org",
                source_note="p.3",
            )
        )


def test_ranged_distribution_requires_min_max():
    with pytest.raises(ValidationError, match="needs min/max"):
        ParamRow(
            **_row(
                status="sourced",
                distribution="uniform",
                source_url="https://example.org",
                source_note="p.3",
            )
        )


def test_min_must_be_less_than_max():
    with pytest.raises(ValidationError, match="min must be"):
        ParamRow(
            **_row(
                status="sourced",
                distribution="uniform",
                min="0.8",
                max="0.2",
                source_url="https://example.org",
                source_note="p.3",
            )
        )


def test_fraction_param_out_of_range_rejected():
    with pytest.raises(ValidationError, match=r"outside \[0,1\]"):
        ParamRow(
            **_row(
                param="fe",
                status="sourced",
                distribution="fixed",
                value="1.5",
                source_url="https://example.org",
                source_note="p.3",
            )
        )


def test_positive_param_rejects_zero_or_negative():
    with pytest.raises(ValidationError, match="must be > 0"):
        ParamRow(
            **_row(
                param="pnec_ng_l",
                status="sourced",
                distribution="fixed",
                value="0",
                source_url="https://example.org",
                source_note="p.3",
            )
        )


def test_valid_sourced_fraction_row_accepted():
    row = ParamRow(
        **_row(
            param="fe",
            status="sourced",
            distribution="fixed",
            value="0.6",
            source_url="https://example.org",
            source_note="p.3",
        )
    )
    assert row.status == "sourced"


def test_sourced_atc_row_only_needs_value():
    row = ParamRow(
        **_row(
            param="atc",
            status="sourced",
            value="C09CA04",
            source_url="https://example.org",
            source_note="WHO ATC index",
        )
    )
    assert row.value == "C09CA04"


def test_duplicate_row_rejected(tmp_path):
    path = tmp_path / "dupes.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(_row())
        writer.writerow(_row())
    with pytest.raises(ValueError, match="duplicate row"):
        load_rows(path)


# --- Dist.sample -------------------------------------------------------


def test_dist_fixed_sample():
    d = Dist(kind="fixed", value=2.0)
    out = d.sample(np.random.default_rng(0), 5)
    assert (out == 2.0).all()


def test_dist_uniform_sample_in_range():
    d = Dist(kind="uniform", min=1.0, max=2.0)
    out = d.sample(np.random.default_rng(0), 1000)
    assert out.min() >= 1.0
    assert out.max() <= 2.0


def test_dist_loguniform_sample_in_range():
    d = Dist(kind="loguniform", min=0.002, max=0.15)
    out = d.sample(np.random.default_rng(0), 1000)
    assert out.min() >= 0.002
    assert out.max() <= 0.15


def test_dist_triangular_sample_in_range():
    d = Dist(kind="triangular", min=0.0, value=0.5, max=1.0)
    out = d.sample(np.random.default_rng(0), 1000)
    assert out.min() >= 0.0
    assert out.max() <= 1.0


# --- load_drug_params: dev vs strict -------------------------------------------------------


def test_dev_mode_uses_placeholders_and_flags_it(tmp_path):
    params, dev_placeholders_used = load_drug_params(_todo_file(tmp_path), mode="dev")
    assert dev_placeholders_used is True
    assert set(params) == set(DRUGS)
    for drug_params in params.values():
        assert drug_params.fe.kind == "fixed"
        assert drug_params.pnec_ng_l.value is not None


def test_dev_mode_does_not_flag_placeholders_when_only_r_is_todo():
    """The shipped file has every required row illustrative and R (unused, w=0) still todo."""
    _, dev_placeholders_used = load_drug_params(PARAMS_CSV, mode="dev")
    assert dev_placeholders_used is False


def test_strict_mode_succeeds_when_all_required_rows_sourced(tmp_path):
    path = tmp_path / "params.csv"
    rows = []
    for drug in DRUGS:
        rows.append(
            _row(
                drug=drug,
                param="atc",
                status="sourced",
                value="X01AA01",
                source_url="u",
                source_note="n",
            )
        )
        rows.append(
            _row(
                drug=drug,
                param="ddd_g",
                status="sourced",
                distribution="fixed",
                value="1.0",
                source_url="u",
                source_note="n",
            )
        )
        rows.append(
            _row(
                drug=drug,
                param="fe",
                status="sourced",
                distribution="fixed",
                value="0.5",
                source_url="u",
                source_note="n",
            )
        )
        rows.append(
            _row(
                drug=drug,
                param="R",
                status="todo",
                source_note="not required: w=0 for all MVP sites",
            )
        )
        rows.append(
            _row(
                drug=drug,
                param="k_per_h",
                status="sourced",
                distribution="fixed",
                value="0.02",
                source_url="u",
                source_note="n",
            )
        )
        rows.append(
            _row(
                drug=drug,
                param="pnec_ng_l",
                status="sourced",
                distribution="fixed",
                value="500",
                source_url="u",
                source_note="n",
            )
        )
        rows.append(
            _row(
                drug=drug,
                param="lod_ng_l",
                status="sourced",
                distribution="fixed",
                value="1.0",
                source_url="u",
                source_note="n",
            )
        )
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    params, dev_placeholders_used = load_drug_params(path, mode="strict")
    assert dev_placeholders_used is False
    assert params["irbesartan"].fe.value == 0.5


# --- priors.yaml -------------------------------------------------------


def test_load_priors():
    priors = load_priors(PRIORS_YAML)
    assert priors.lambda_.min == 0.002
    assert priors.lambda_.max == 0.15
    assert priors.Q_by_size_class.S.min == 0.005
    assert priors.tau_h.min == 0.5
    assert priors.scenario_presets["leakage_hotspot"]["lambda"] == 3.0
    assert priors.tiers == {"high": 0.5, "medium": 0.1}


def test_lambda_prior_to_dist_samples_in_range():
    priors = load_priors(PRIORS_YAML)
    out = priors.lambda_.to_dist().sample(np.random.default_rng(1), 1000)
    assert out.min() >= 0.002
    assert out.max() <= 0.15


# --- provenance_entries -------------------------------------------------------


def test_provenance_entries_keys(tmp_path):
    rows = load_rows(_todo_file(tmp_path))
    priors = load_priors(PRIORS_YAML)
    entries = provenance_entries(rows, priors)

    assert "param:irbesartan:fe" in entries
    assert entries["param:irbesartan:fe"].status == "todo"
    assert "prior:lambda" in entries
    assert entries["prior:lambda"].status == "assumption"
    assert "prior:Q" in entries
    assert "prior:tau_h" in entries
