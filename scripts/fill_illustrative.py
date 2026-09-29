"""Fill still-`todo` parameter and consumption rows with declared illustrative values (D33).

Reads data/params/illustrative_values.yaml and writes status=illustrative rows into
drug_parameters.csv and consumption.csv. Rows that are already `sourced` are never
touched, rows that are already `illustrative` are only rewritten with --refresh, and the optional R row stays `todo` (w=0 for every MVP site, D27).

Illustrative rows carry source_note "illustrative — not sourced (D33)" and no citation, so the UI
badges them and they can never be mistaken for sourced values.

Run: uv run python scripts/fill_illustrative.py [--refresh]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALUES = ROOT / "data" / "params" / "illustrative_values.yaml"
PARAMS_CSV = ROOT / "data" / "params" / "drug_parameters.csv"
CONSUMPTION_CSV = ROOT / "data" / "consumption" / "consumption.csv"

NOTE = "illustrative — not sourced (D33)"
NUMERIC_PARAMS = ("ddd_g", "fe", "k_per_h", "pnec_ng_l", "lod_ng_l")


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _eligible(row: dict[str, str], refresh: bool) -> bool:
    """Todo rows always; already-illustrative rows only when refreshing. Sourced rows never."""
    return row["status"] == "todo" or (refresh and row["status"] == "illustrative")


def fill_params(values: dict, refresh: bool = False) -> int:
    """Set illustrative values on todo rows of drug_parameters.csv. Returns rows changed."""
    fields, rows = _read(PARAMS_CSV)
    changed = 0
    for row in rows:
        if not _eligible(row, refresh) or row["param"] == "R":
            continue
        spec = values["drugs"].get(row["drug"], {})
        if row["param"] == "atc":
            value = spec.get("atc")
        elif row["param"] in NUMERIC_PARAMS:
            value = spec.get(row["param"])
        else:
            value = None
        if value is None:
            continue
        row["value"] = str(value)
        if row["param"] != "atc":
            row["distribution"] = "fixed"
        row["source_note"] = NOTE
        row["status"] = "illustrative"
        changed += 1
    _write(PARAMS_CSV, fields, rows)
    return changed


def fill_consumption(values: dict, refresh: bool = False) -> int:
    """Set illustrative values on todo rows of consumption.csv. Returns rows changed."""
    fields, rows = _read(CONSUMPTION_CSV)
    base = values["consumption"]["base"]
    factor = values["consumption"]["country_factor"]
    changed = 0
    for row in rows:
        if not _eligible(row, refresh):
            continue
        drug, country = row["drug"], row["country"]
        if drug not in base or country not in factor:
            continue
        row["atc"] = values["drugs"][drug]["atc"]
        row["ddd_per_1000_per_day"] = str(round(base[drug] * factor[country], 2))
        row["granularity"] = "molecule"
        row["source_note"] = NOTE
        row["status"] = "illustrative"
        changed += 1
    _write(CONSUMPTION_CSV, fields, rows)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="also rewrite rows that are already illustrative")
    args = parser.parse_args()
    values = yaml.safe_load(VALUES.read_text())
    print(f"drug_parameters.csv: {fill_params(values, args.refresh)} row(s) set to illustrative")
    print(f"consumption.csv:     {fill_consumption(values, args.refresh)} row(s) set to illustrative")


if __name__ == "__main__":
    main()
