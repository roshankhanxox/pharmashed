"""M03 acceptance: national consumption registry loader."""

import csv
from pathlib import Path

import pytest
from pharmashed.consumption import (
    COLUMNS,
    COUNTRIES,
    ConsumptionRow,
    UnsourcedConsumptionError,
    consumption_value,
    load_consumption,
    load_rows,
    provenance_entries,
)
from pharmashed.params import DRUGS
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSUMPTION_CSV = REPO_ROOT / "data" / "consumption" / "consumption.csv"


def _row(**overrides) -> dict:
    base = dict.fromkeys(COLUMNS, "")
    base.update(country="PT", drug="irbesartan", status="todo", verified="none")
    base.update(overrides)
    return base


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# --- shipped file -------------------------------------------------------


def test_shipped_csv_has_30_rows_all_todo():
    rows = load_rows(CONSUMPTION_CSV)
    assert len(rows) == 30
    assert all(r.status == "todo" for r in rows)
    assert {r.country for r in rows} == set(COUNTRIES)
    assert {r.drug for r in rows} == set(DRUGS)


def test_shipped_csv_fails_strict_mode():
    with pytest.raises(UnsourcedConsumptionError) as exc_info:
        load_consumption(CONSUMPTION_CSV, mode="strict")
    assert len(exc_info.value.missing) == 30


def test_shipped_csv_ok_in_dev_mode():
    by_key = load_consumption(CONSUMPTION_CSV, mode="dev")
    assert len(by_key) == 30
    assert by_key[("PT", "irbesartan")].status == "todo"


# --- ConsumptionRow validation rules -------------------------------------------------------


def test_unknown_country_rejected():
    with pytest.raises(ValidationError):
        ConsumptionRow(**_row(country="XX"))


def test_unknown_drug_rejected():
    with pytest.raises(ValidationError):
        ConsumptionRow(**_row(drug="ibuprofen"))


def test_sourced_requires_source_url_and_note():
    with pytest.raises(ValidationError, match="source_url"):
        ConsumptionRow(
            **_row(
                status="sourced",
                granularity="molecule",
                ddd_per_1000_per_day="1.5",
                source_note="table 3",
            )
        )


def test_sourced_requires_granularity():
    with pytest.raises(ValidationError, match="granularity"):
        ConsumptionRow(
            **_row(
                status="sourced",
                ddd_per_1000_per_day="1.5",
                source_url="https://example.org",
                source_note="table 3",
            )
        )


def test_molecule_row_needs_positive_ddd():
    with pytest.raises(ValidationError, match="ddd_per_1000_per_day"):
        ConsumptionRow(
            **_row(
                status="sourced",
                granularity="molecule",
                source_url="https://example.org",
                source_note="table 3",
            )
        )


def test_downscaled_row_needs_group_value():
    with pytest.raises(ValidationError, match="group_value"):
        ConsumptionRow(
            **_row(
                status="sourced",
                granularity="group_downscaled",
                molecule_share="0.4",
                share_source_url="https://example.org/share",
                source_url="https://example.org",
                source_note="oecd table",
            )
        )


def test_downscaled_row_needs_molecule_share_in_range():
    with pytest.raises(ValidationError, match="molecule_share"):
        ConsumptionRow(
            **_row(
                status="sourced",
                granularity="group_downscaled",
                group_value="10",
                molecule_share="1.5",
                share_source_url="https://example.org/share",
                source_url="https://example.org",
                source_note="oecd table",
            )
        )


def test_downscaled_row_needs_share_source_url():
    with pytest.raises(ValidationError, match="share_source_url"):
        ConsumptionRow(
            **_row(
                status="sourced",
                granularity="group_downscaled",
                group_value="10",
                molecule_share="0.4",
                source_url="https://example.org",
                source_note="oecd table",
            )
        )


def test_valid_molecule_row_accepted():
    row = ConsumptionRow(
        **_row(
            status="sourced",
            granularity="molecule",
            ddd_per_1000_per_day="2.3",
            source_url="https://example.org",
            source_note="table 3",
        )
    )
    assert row.status == "sourced"


def test_duplicate_row_rejected(tmp_path):
    path = tmp_path / "dupes.csv"
    _write_csv(path, [_row(), _row()])
    with pytest.raises(ValueError, match="duplicate row"):
        load_rows(path)


# --- share-not-copied rule -------------------------------------------------------


def _downscaled_row(**overrides) -> dict:
    base = _row(
        status="sourced",
        granularity="group_downscaled",
        group_value="10",
        molecule_share="0.4",
        share_source_url="https://example.org/share",
        source_url="https://example.org",
        source_note="oecd table",
    )
    base.update(overrides)
    return base


def test_same_share_same_source_across_countries_rejected(tmp_path):
    path = tmp_path / "copied.csv"
    _write_csv(
        path,
        [
            _downscaled_row(country="PT", drug="citalopram"),
            _downscaled_row(country="IT", drug="citalopram"),
        ],
    )
    with pytest.raises(ValueError, match="reused"):
        load_rows(path)


def test_same_share_different_source_across_countries_accepted(tmp_path):
    path = tmp_path / "distinct_sources.csv"
    _write_csv(
        path,
        [
            _downscaled_row(country="PT", drug="citalopram", share_source_url="https://pt.example/share"),
            _downscaled_row(country="IT", drug="citalopram", share_source_url="https://it.example/share"),
        ],
    )
    rows = load_rows(path)
    assert len(rows) == 2


def test_different_shares_across_countries_accepted(tmp_path):
    path = tmp_path / "distinct_shares.csv"
    _write_csv(
        path,
        [
            _downscaled_row(country="PT", drug="citalopram", molecule_share="0.4"),
            _downscaled_row(country="IT", drug="citalopram", molecule_share="0.35"),
        ],
    )
    rows = load_rows(path)
    assert len(rows) == 2


# --- consumption_value -------------------------------------------------------


def test_consumption_value_molecule():
    row = ConsumptionRow(
        **_row(
            status="sourced",
            granularity="molecule",
            ddd_per_1000_per_day="2.3",
            source_url="https://example.org",
            source_note="table 3",
        )
    )
    assert consumption_value(row) == 2.3


def test_consumption_value_downscaled():
    row = ConsumptionRow(**_downscaled_row())
    assert consumption_value(row) == pytest.approx(4.0)


def test_consumption_value_raises_on_todo_row():
    row = ConsumptionRow(**_row())
    with pytest.raises(ValueError, match="no resolvable value"):
        consumption_value(row)


# --- load_consumption: dev vs strict -------------------------------------------------------


def test_strict_mode_succeeds_when_all_rows_sourced(tmp_path):
    path = tmp_path / "consumption.csv"
    rows = []
    for country in COUNTRIES:
        for drug in DRUGS:
            rows.append(
                _row(
                    country=country,
                    drug=drug,
                    status="sourced",
                    granularity="molecule",
                    ddd_per_1000_per_day="1.0",
                    source_url="u",
                    source_note="n",
                )
            )
    _write_csv(path, rows)

    by_key = load_consumption(path, mode="strict")
    assert len(by_key) == 30
    assert by_key[("PT", "irbesartan")].status == "sourced"


# --- provenance_entries -------------------------------------------------------


def test_provenance_entries_keys():
    rows = load_rows(CONSUMPTION_CSV)
    entries = provenance_entries(rows)
    assert "consumption:PT:irbesartan" in entries
    assert entries["consumption:PT:irbesartan"].status == "todo"
    assert entries["consumption:PT:irbesartan"].value is None
