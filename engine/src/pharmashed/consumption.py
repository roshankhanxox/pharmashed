"""National drug consumption registry (M03).

Loads `data/consumption/consumption.csv` (one cited row per country x drug),
DDD/1000 inhabitants/day, either at molecule granularity or downscaled from
an OECD group value via a country-specific molecule share. Never fills a
value from memory -- see CONTEXT.md hard rule 1 and SOURCING.md S3.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from pharmashed.params import DRUGS

Mode = Literal["dev", "strict"]
Granularity = Literal["molecule", "group_downscaled"]

COUNTRIES = ["PT", "IT", "FR", "BE", "NO"]

COLUMNS = [
    "country",
    "drug",
    "atc",
    "year",
    "ddd_per_1000_per_day",
    "granularity",
    "group_value",
    "molecule_share",
    "share_source_url",
    "source_title",
    "source_url",
    "source_note",
    "evidence_quote",
    "retrieved_at",
    "verified",
    "verify_note",
    "status",
]


class UnsourcedConsumptionError(Exception):
    """Raised in strict mode when required rows are still `status=todo`."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("unsourced consumption rows: " + ", ".join(missing))


class ConsumptionRow(BaseModel):
    """One row of consumption.csv."""

    model_config = ConfigDict(extra="forbid")

    country: str
    drug: str
    atc: str | None = None
    year: int | None = None
    ddd_per_1000_per_day: float | None = None
    granularity: Granularity | None = None
    group_value: float | None = None
    molecule_share: float | None = None
    share_source_url: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    source_note: str | None = None
    evidence_quote: str | None = None
    retrieved_at: str | None = None
    verified: Literal["none", "agent", "human", "failed"] = "none"
    verify_note: str | None = None
    status: Literal["sourced", "todo"] = "todo"

    @model_validator(mode="before")
    @classmethod
    def _blank_strings_to_absent(cls, data):
        """Empty-string CSV/kwargs fields fall back to the field default."""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v != ""}
        return data

    @field_validator("country")
    @classmethod
    def _country_known(cls, v: str) -> str:
        if v not in COUNTRIES:
            raise ValueError(f"unknown country {v!r}, expected one of {COUNTRIES}")
        return v

    @field_validator("drug")
    @classmethod
    def _drug_known(cls, v: str) -> str:
        if v not in DRUGS:
            raise ValueError(f"unknown drug {v!r}, expected one of {DRUGS}")
        return v

    @model_validator(mode="after")
    def _check_sourced_rules(self) -> ConsumptionRow:
        if self.status != "sourced":
            return self

        if not self.source_url or not self.source_note:
            raise ValueError(
                f"{self.country}:{self.drug} is status=sourced but missing "
                "source_url and/or source_note"
            )

        if self.granularity is None:
            raise ValueError(f"{self.country}:{self.drug} is sourced but has no granularity")

        if self.granularity == "molecule":
            if self.ddd_per_1000_per_day is None or self.ddd_per_1000_per_day <= 0:
                raise ValueError(
                    f"{self.country}:{self.drug} (molecule) needs a positive ddd_per_1000_per_day"
                )
        else:  # group_downscaled
            if self.group_value is None or self.group_value <= 0:
                raise ValueError(f"{self.country}:{self.drug} (downscaled) needs group_value > 0")
            if self.molecule_share is None or not (0.0 < self.molecule_share <= 1.0):
                raise ValueError(
                    f"{self.country}:{self.drug} (downscaled) needs molecule_share in (0,1]"
                )
            if not self.share_source_url:
                raise ValueError(
                    f"{self.country}:{self.drug} (downscaled) needs share_source_url"
                )

        return self


def _check_shares_not_copied(rows: list[ConsumptionRow]) -> None:
    """A molecule_share must be individually sourced, not pasted across
    countries. Same drug, same share value, same share_source_url from two
    different countries means it was copied rather than looked up per
    country (SOURCING.md S3: "never one share across countries")."""
    seen: dict[tuple[str, float, str], str] = {}
    for row in rows:
        if row.status != "sourced" or row.granularity != "group_downscaled":
            continue
        key = (row.drug, row.molecule_share, row.share_source_url)  # type: ignore[assignment]
        if key in seen and seen[key] != row.country:
            raise ValueError(
                f"{row.drug}: molecule_share {row.molecule_share} from "
                f"{row.share_source_url} is reused for both {seen[key]} and "
                f"{row.country} -- source a country-specific share instead"
            )
        seen[key] = row.country


def load_rows(path: str | Path) -> list[ConsumptionRow]:
    """Load and validate every row of consumption.csv (no strict-mode gate)."""
    path = Path(path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = [ConsumptionRow(**row) for row in reader]

    seen = set()
    for row in rows:
        key = (row.country, row.drug)
        if key in seen:
            raise ValueError(f"duplicate row for {row.country}:{row.drug}")
        seen.add(key)

    _check_shares_not_copied(rows)

    return rows


def load_consumption(
    path: str | Path, mode: Mode = "strict"
) -> dict[tuple[str, str], ConsumptionRow]:
    """Load consumption.csv into a (country, drug) -> ConsumptionRow map.

    In strict mode, raises UnsourcedConsumptionError listing every row still
    `status=todo`. Dev mode returns todo rows as-is; callers needing a
    numeric value must go through consumption_value(), which raises on an
    unsourced row -- unlike drug parameters (M02), consumption has no
    dev-placeholder fallback yet (see JUDGEMENT.md M03).
    """
    path = Path(path)
    rows = load_rows(path)

    todo = [r for r in rows if r.status == "todo"]
    if mode == "strict" and todo:
        raise UnsourcedConsumptionError([f"{r.country}:{r.drug}" for r in todo])

    return {(r.country, r.drug): r for r in rows}


def consumption_value(row: ConsumptionRow) -> float:
    """DDD/1000 inhabitants/day: the molecule value, or group_value x
    molecule_share for a downscaled row."""
    if row.granularity == "molecule":
        assert row.ddd_per_1000_per_day is not None
        return row.ddd_per_1000_per_day
    if row.granularity == "group_downscaled":
        assert row.group_value is not None and row.molecule_share is not None
        return row.group_value * row.molecule_share
    raise ValueError(f"{row.country}:{row.drug} has no resolvable value (status={row.status})")


def provenance_entries(rows: Iterable[ConsumptionRow]) -> dict:
    """Build the provenance lookup keyed like results.json's provenance_keys
    (e.g. "consumption:PT:irbesartan")."""
    from pharmashed.contracts import ProvenanceEntry

    entries = {}
    for row in rows:
        key = f"consumption:{row.country}:{row.drug}"
        value = consumption_value(row) if row.status == "sourced" else None
        entries[key] = ProvenanceEntry(
            label=f"{row.country} {row.drug} consumption",
            value=value,
            unit="DDD/1000 inhabitants/day",
            distribution=None,
            source_title=row.source_title,
            source_url=row.source_url,
            source_note=row.source_note,
            status="sourced" if row.status == "sourced" else "todo",
        )
    return entries
