"""Reader for data/observed/observed_rodrigues2025.csv.

This is the ONLY module allowed to read data/observed/ (M12 import rule).
Tests enforce this via tests/test_separation.py.
"""

from __future__ import annotations

import csv
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_OBSERVED_PATH = _REPO_ROOT / "data" / "observed" / "observed_rodrigues2025.csv"

# Engine drug name → CSV compound name (D01)
DRUG_TO_COMPOUND: dict[str, str] = {
    "carbamazepine": "carbamazepine",
    "atenolol": "atenolol",
    "losartan": "losartan",
    "irbesartan": "irbesartan",
    "paracetamol": "acetaminophen",
    "citalopram": "citalopram",
}

# Engine city code → CSV scope name
CITY_TO_SCOPE: dict[str, str] = {
    "TLS": "Toulouse",
    "GNT": "Ghent",
    "BNV": "Benevento",
    "CBR": "Coimbra",
    "OSL": "Oslo",
}


def load_observed(path: Path | None = None) -> list[dict]:
    """Load all rows from observed_rodrigues2025.csv.

    Args:
        path: override CSV path (default data/observed/observed_rodrigues2025.csv).

    Returns:
        List of dicts with keys: compound, therapeutic_group, metric, value, unit, scope, site, source_ref, note.
    """
    p = path or _OBSERVED_PATH
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def lookup(
    rows: list[dict],
    compound: str,
    metric: str,
    scope: str,
) -> float | None:
    """Return the numeric value of a single (compound, metric, scope) lookup.

    Args:
        rows: output of load_observed().
        compound: CSV compound name (use DRUG_TO_COMPOUND for mapping).
        metric: CSV metric name, e.g. 'detection_frequency'.
        scope: CSV scope name, e.g. 'all_sites' or 'Toulouse'.

    Returns:
        Float value, or None if not found.
    """
    for row in rows:
        if row["compound"] == compound and row["metric"] == metric and row["scope"] == scope:
            try:
                return float(row["value"])
            except (ValueError, TypeError):
                return None
    return None
