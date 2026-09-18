"""Pydantic v2 models mirroring contracts/schemas/*.schema.json (M01).

Hand-written to match the schemas; keep in sync by hand. The schemas
(not these models) are the source of truth -- `tests/test_contracts.py`
validates the JSON fixtures against the schemas directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["high", "medium", "low"]
Variant = Literal["full", "pop_only", "wwtp_only"]
SizeClass = Literal["S", "M", "L"]
ParamStatus = Literal["sourced", "assumption", "illustrative", "todo"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- sites.json -------------------------------------------------------


class City(Strict):
    id: str
    name: str
    country: str
    center: tuple[float, float]
    zoom: float


class Site(Strict):
    id: str
    city: str
    name: str
    lonlat: tuple[float, float]
    synthetic: Literal[True]
    size_class: SizeClass
    w: Literal[0, 1]
    valid: bool
    population_buffer: float
    population_source_key: str


class SitesMeta(Strict):
    generated_at: datetime
    synthetic: Literal[True]


class Sites(Strict):
    meta: SitesMeta
    cities: list[City]
    sites: list[Site]


# --- results.json -------------------------------------------------------


class PercentileTriplet(Strict):
    p5: float
    p50: float
    p95: float


class Driver(Strict):
    param: str
    rho: float = Field(ge=-1, le=1)


class FlipStep(Strict):
    param: str
    multiplier: float = Field(gt=0)
    to_tier: Tier


class Flip(Strict):
    up: FlipStep | None
    down: FlipStep | None


class Histogram(Strict):
    log10_edges: list[float]
    counts: list[int]


class DrawsRef(Strict):
    offset: int = Field(ge=0)
    count: int = Field(ge=1)


class FhirIds(Strict):
    prediction: str


class ResultEntry(Strict):
    site_id: str
    drug: str
    pec_ng_l: PercentileTriplet
    rq: PercentileTriplet
    pnec_ng_l: float = Field(gt=0)
    lod_ng_l: float = Field(gt=0)
    score: float = Field(ge=0, le=1)
    tier: Tier
    lod_share: float = Field(ge=0, le=1)
    rank_in_city: int = Field(ge=1)
    n_in_city: int = Field(ge=1)
    drivers: list[Driver]
    driver_sentence: str
    flip: Flip
    histogram: Histogram
    draws: DrawsRef
    provenance_keys: list[str]
    fhir_ids: FhirIds


class SiteOverall(Strict):
    site_id: str
    score: float = Field(ge=0, le=1)
    top_drug: str
    rank_in_city: int = Field(ge=1)


class CitySummary(Strict):
    city: str
    high: int = Field(ge=0)
    medium: int = Field(ge=0)
    low: int = Field(ge=0)


class ResultsMeta(Strict):
    engine_version: str
    generated_at: datetime
    seed: int
    n_draws: int = Field(ge=1)
    n_stored: int = Field(ge=1)
    variant: Variant
    dev_placeholders: bool
    frozen_tag: str | None
    param_count: int = Field(ge=0)
    all_params_cited: bool


class Results(Strict):
    meta: ResultsMeta
    drugs: list[str]
    results: list[ResultEntry]
    site_overall: list[SiteOverall]
    city_summary: list[CitySummary]


# --- draws_index.json -------------------------------------------------------


class DrawsIndexEntry(Strict):
    site_id: str
    drug: str
    offset: int = Field(ge=0)
    count: int = Field(ge=1)


class DrawsIndex(Strict):
    dtype: Literal["float32"]
    endianness: Literal["little"]
    n_stored: int = Field(ge=1)
    entries: list[DrawsIndexEntry]


# --- checks.json -------------------------------------------------------


class CheckEntry(Strict):
    id: Literal["C1", "C2", "C3", "C4", "C5"]
    status: Literal["pass", "fail", "unavailable"]
    reason: str | None
    data: dict


class ChecksMeta(Strict):
    frozen_tag: str
    frozen_sha256: str
    generated_at: datetime


class Checks(Strict):
    meta: ChecksMeta
    circularity_statement: str
    checks: list[CheckEntry]


# --- methodology.json -------------------------------------------------------


class Stage(Strict):
    id: str
    name: str
    symbol: str
    prior_summary: str
    provenance_key: str


class PriorRow(Strict):
    param: str
    distribution: str
    range: str
    unit: str
    status: Literal["sourced", "assumption"]
    source_url: str | None
    shape: str


class AblationRanking(Strict):
    city: str
    variant: Variant
    ranking: list[str]


class Ablations(Strict):
    variants: list[Variant]
    per_city: list[AblationRanking]


class MethodologyMeta(Strict):
    generated_at: datetime


class Methodology(Strict):
    meta: MethodologyMeta
    stages: list[Stage]
    priors_table: list[PriorRow]
    identifiability_text: str
    ablations: Ablations


# --- provenance.json -------------------------------------------------------


class ProvenanceEntry(Strict):
    label: str
    value: float | str | None
    unit: str | None
    distribution: str | None
    source_title: str | None
    source_url: str | None
    source_note: str | None
    status: ParamStatus


Provenance = dict[str, ProvenanceEntry]


# --- fhir_index.json -------------------------------------------------------


class FhirBundle(Strict):
    name: str
    path: str
    resource_type: str
    count: int = Field(ge=0)


class FhirValidation(Strict):
    status: Literal["pass", "fail", "unknown"]
    errors: int = Field(ge=0)
    warnings: int = Field(ge=0)
    validator_version: str | None
    ran_at: datetime | None
    ci_log_url: str | None


class QueryResult(Strict):
    query: str
    count: int = Field(ge=0)


class QueryDemo(Strict):
    laboratory: QueryResult
    model_prediction: QueryResult


class FhirIndexMeta(Strict):
    generated_at: datetime


class FhirIndex(Strict):
    meta: FhirIndexMeta
    resource_counts: dict[str, int]
    bundles: list[FhirBundle]
    validation: FhirValidation
    query_demo: QueryDemo
