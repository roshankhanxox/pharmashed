"""Drug parameter registry and site-level priors (M02).

Loads `data/params/drug_parameters.csv` (one cited row per drug x param) and
`data/params/priors.yaml` (site-level and structural priors), refusing to run
in strict mode on any row that isn't sourced. Never fills a value from
memory -- see CONTEXT.md hard rule 1 and SOURCING.md.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from pharmashed.contracts import ProvenanceEntry

Mode = Literal["dev", "strict"]
DistKind = Literal["fixed", "uniform", "loguniform", "triangular"]

DRUGS = ["carbamazepine", "atenolol", "losartan", "irbesartan", "paracetamol", "citalopram"]
NUMERIC_PARAMS = ["ddd_g", "fe", "R", "k_per_h", "pnec_ng_l", "lod_ng_l"]
PARAMS = ["atc", *NUMERIC_PARAMS]

FRACTION_PARAMS = {"fe", "R"}
POSITIVE_PARAMS = {"ddd_g", "pnec_ng_l", "lod_ng_l"}

DEV_PLACEHOLDERS_PATH = (
    Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "dev_placeholders.yaml"
)


class UnsourcedParameterError(Exception):
    """Raised in strict mode when required rows are still `status=todo`."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("unsourced parameters: " + ", ".join(missing))


class ParamRow(BaseModel):
    """One row of drug_parameters.csv."""

    model_config = ConfigDict(extra="forbid")

    drug: str
    param: str
    distribution: DistKind | None = None
    value: str | None = None  # numeric params: a float string; atc: a code
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    source_note: str | None = None
    evidence_quote: str | None = None
    retrieved_at: str | None = None
    verified: Literal["none", "agent", "human", "failed"] = "none"
    verify_note: str | None = None
    status: Literal["sourced", "illustrative", "todo"] = "todo"

    @model_validator(mode="before")
    @classmethod
    def _blank_strings_to_absent(cls, data):
        """Empty-string CSV/kwargs fields fall back to the field default."""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v != ""}
        return data

    @field_validator("drug")
    @classmethod
    def _drug_known(cls, v: str) -> str:
        if v not in DRUGS:
            raise ValueError(f"unknown drug {v!r}, expected one of {DRUGS}")
        return v

    @field_validator("param")
    @classmethod
    def _param_known(cls, v: str) -> str:
        if v not in PARAMS:
            raise ValueError(f"unknown param {v!r}, expected one of {PARAMS}")
        return v

    @model_validator(mode="after")
    def _check_sourced_rules(self) -> ParamRow:
        if self.status == "todo":
            return self

        if self.status == "sourced":
            if not self.source_url or not self.source_note:
                raise ValueError(
                    f"{self.drug}:{self.param} is status=sourced but missing "
                    "source_url and/or source_note"
                )
        else:
            # illustrative (D33): a declared placeholder. It must say so, and it must never carry
            # a citation, or it could be mistaken for a sourced value (CONTEXT hard rule 1).
            if not (self.source_note or "").lower().startswith("illustrative"):
                raise ValueError(
                    f"{self.drug}:{self.param} is status=illustrative but source_note does not "
                    "start with 'illustrative'"
                )
            if self.source_url or self.source_title or self.evidence_quote:
                raise ValueError(
                    f"{self.drug}:{self.param} is status=illustrative and must not carry "
                    "source_url, source_title or evidence_quote"
                )

        if self.param == "atc":
            if not self.value:
                raise ValueError(f"{self.drug}:atc is sourced but has no value")
            return self

        numeric_value = self._numeric_value()
        if self.distribution in ("fixed", "triangular") and numeric_value is None:
            raise ValueError(f"{self.drug}:{self.param} ({self.distribution}) needs a value")
        if self.distribution in ("uniform", "loguniform", "triangular"):
            if self.min is None or self.max is None:
                raise ValueError(f"{self.drug}:{self.param} ({self.distribution}) needs min/max")
            if self.min >= self.max:
                raise ValueError(f"{self.drug}:{self.param}: min must be < max")

        for bound_name, bound in (("value", numeric_value), ("min", self.min), ("max", self.max)):
            if bound is None:
                continue
            if self.param in FRACTION_PARAMS and not (0.0 <= bound <= 1.0):
                raise ValueError(f"{self.drug}:{self.param} {bound_name}={bound} outside [0,1]")
            if self.param in POSITIVE_PARAMS and bound <= 0:
                raise ValueError(f"{self.drug}:{self.param} {bound_name}={bound} must be > 0")

        return self

    def _numeric_value(self) -> float | None:
        if self.param == "atc" or self.value in (None, ""):
            return None
        return float(self.value)


# Rows whose value the model may use: sourced, or declared illustrative (D33/D36).
USABLE_STATUSES = ("sourced", "illustrative")


class Dist(BaseModel):
    """A resolved distribution for one numeric parameter."""

    model_config = ConfigDict(extra="forbid")

    kind: DistKind
    value: float | None = None
    min: float | None = None
    max: float | None = None

    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        if self.kind == "fixed":
            assert self.value is not None
            return np.full(n, self.value, dtype=float)
        if self.kind == "uniform":
            assert self.min is not None and self.max is not None
            return rng.uniform(self.min, self.max, n)
        if self.kind == "loguniform":
            assert self.min is not None and self.max is not None
            return np.exp(rng.uniform(np.log(self.min), np.log(self.max), n))
        if self.kind == "triangular":
            assert self.min is not None and self.max is not None and self.value is not None
            return rng.triangular(self.min, self.value, self.max, n)
        raise ValueError(f"unknown distribution kind {self.kind!r}")


class DrugParams(BaseModel):
    """Resolved, sample-ready parameters for one drug."""

    model_config = ConfigDict(extra="forbid")

    drug: str
    atc: str
    ddd_g: Dist
    fe: Dist
    R: Dist
    k_per_h: Dist
    pnec_ng_l: Dist
    lod_ng_l: Dist


def load_rows(path: str | Path) -> list[ParamRow]:
    """Load and validate every row of drug_parameters.csv (no strict-mode gate)."""
    path = Path(path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = [ParamRow(**row) for row in reader]

    seen = set()
    for row in rows:
        key = (row.drug, row.param)
        if key in seen:
            raise ValueError(f"duplicate row for {row.drug}:{row.param}")
        seen.add(key)

    return rows


def _row_to_dist(row: ParamRow) -> Dist:
    return Dist(
        kind=row.distribution or "fixed",
        value=row._numeric_value(),
        min=row.min,
        max=row.max,
    )


def _dev_placeholder_dist(param: str, placeholders: dict) -> Dist:
    entry = placeholders["drug_parameters"][param]
    return Dist(
        kind=entry["distribution"],
        value=entry.get("value"),
        min=entry.get("min"),
        max=entry.get("max"),
    )


def load_drug_params(path: str | Path, mode: Mode = "strict") -> tuple[dict[str, DrugParams], bool]:
    """Load drug_parameters.csv into one DrugParams per drug.

    Returns (params_by_drug, dev_placeholders_used). In strict mode, raises
    UnsourcedParameterError listing every row still `status=todo` (except
    `R`, which is optional -- CONTEXT D27, all MVP sites have w=0).
    """
    path = Path(path)
    rows = load_rows(path)

    todo = [r for r in rows if r.status == "todo" and r.param != "R"]
    if mode == "strict" and todo:
        raise UnsourcedParameterError([f"{r.drug}:{r.param}" for r in todo])

    placeholders = None
    dev_placeholders_used = False
    # R is optional (w=0 everywhere), so a todo R row alone does not mean placeholders are in use.
    if mode == "dev" and any(r.status == "todo" and r.param != "R" for r in rows):
        with open(DEV_PLACEHOLDERS_PATH) as f:
            placeholders = yaml.safe_load(f)
        dev_placeholders_used = True

    by_drug: dict[str, dict[str, ParamRow]] = {d: {} for d in DRUGS}
    for row in rows:
        by_drug[row.drug][row.param] = row

    result: dict[str, DrugParams] = {}
    for drug, row_by_param in by_drug.items():
        kwargs: dict = {"drug": drug}

        atc_row = row_by_param.get("atc")
        if atc_row and atc_row.status in USABLE_STATUSES:
            kwargs["atc"] = atc_row.value
        elif placeholders is not None:
            kwargs["atc"] = placeholders["drug_parameters"]["atc"]
        else:
            kwargs["atc"] = ""

        for param in NUMERIC_PARAMS:
            row = row_by_param.get(param)
            if row and row.status in USABLE_STATUSES:
                kwargs[param] = _row_to_dist(row)
            elif placeholders is not None:
                kwargs[param] = _dev_placeholder_dist(param, placeholders)
            else:
                # dev mode but no todo rows for this param, or R left todo
                # in strict mode: fall back to an inert zero-width dist.
                kwargs[param] = Dist(kind="fixed", value=0.0)

        result[drug] = DrugParams(**kwargs)

    return result, dev_placeholders_used


class DistSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distribution: DistKind
    value: float | None = None
    min: float | None = None
    max: float | None = None

    def to_dist(self) -> Dist:
        return Dist(kind=self.distribution, value=self.value, min=self.min, max=self.max)


class QBySizeClass(BaseModel):
    model_config = ConfigDict(extra="forbid")

    S: DistSpec
    M: DistSpec
    L: DistSpec
    status: str
    note: str


class LambdaPrior(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distribution: DistKind
    min: float
    max: float
    status: str
    sources: list[str]
    note: str

    def to_dist(self) -> Dist:
        return Dist(kind=self.distribution, min=self.min, max=self.max)


class ScalarPrior(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distribution: DistKind
    min: float
    max: float
    status: str
    note: str

    def to_dist(self) -> Dist:
        return Dist(kind=self.distribution, min=self.min, max=self.max)


class Priors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lambda_: LambdaPrior
    Q_by_size_class: QBySizeClass
    tau_h: ScalarPrior
    consumption_multiplier: ScalarPrior
    scenario_presets: dict[str, dict[str, float]]
    tiers: dict[str, float]


def load_priors(path: str | Path) -> Priors:
    with open(path) as f:
        raw = yaml.safe_load(f)
    raw["lambda_"] = raw.pop("lambda")
    return Priors(**raw)


def provenance_entries(rows: Iterable[ParamRow], priors: Priors) -> dict[str, ProvenanceEntry]:
    """Build the provenance lookup keyed like results.json's provenance_keys
    (e.g. "param:irbesartan:fe", "prior:lambda")."""
    entries: dict[str, ProvenanceEntry] = {}

    for row in rows:
        key = f"param:{row.drug}:{row.param}"
        entries[key] = ProvenanceEntry(
            label=f"{row.drug} {row.param}",
            value=row.value,
            unit=row.unit,
            distribution=row.distribution,
            source_title=row.source_title,
            source_url=row.source_url,
            source_note=row.source_note,
            status=row.status,
        )

    entries["prior:lambda"] = ProvenanceEntry(
        label="leakage (lambda)",
        value=None,
        unit="fraction",
        distribution=priors.lambda_.distribution,
        source_title=None,
        source_url=None,
        source_note=priors.lambda_.note,
        status="assumption",
    )
    entries["prior:Q"] = ProvenanceEntry(
        label="stream flow (Q) by size class",
        value=None,
        unit="m3/s",
        distribution=priors.Q_by_size_class.S.distribution,
        source_title=None,
        source_url=None,
        source_note=priors.Q_by_size_class.note,
        status="assumption",
    )
    entries["prior:tau_h"] = ProvenanceEntry(
        label="travel time (tau)",
        value=None,
        unit="h",
        distribution=priors.tau_h.distribution,
        source_title=None,
        source_url=None,
        source_note=priors.tau_h.note,
        status="assumption",
    )

    return entries
