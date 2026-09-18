"""Build-artifact loader (M16).

Loads JSON files from PHARMASHED_DATA once at startup.
Draws are memory-mapped for efficient access.
"""

from __future__ import annotations

import json
import os
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

_DEFAULT_DATA = Path(__file__).resolve().parents[4] / "data" / "build"


def _data_dir() -> Path:
    return Path(os.environ.get("PHARMASHED_DATA", str(_DEFAULT_DATA)))


@lru_cache(maxsize=1)
def _load_json(name: str) -> Any:
    path = _data_dir() / name
    return json.loads(path.read_text()) if path.exists() else {}


def results() -> dict:
    return _load_json("results.json")


def sites() -> dict:
    return _load_json("sites.json")


def checks() -> dict:
    return _load_json("checks.json")


def methodology() -> dict:
    return _load_json("methodology.json")


def glossary() -> dict:
    return _load_json("glossary.json")


def provenance() -> dict:
    return _load_json("provenance.json")


def fhir_index() -> dict:
    fhir_out = _data_dir().parent / "build"  # fhir/out may differ; try both
    candidates = [
        _data_dir() / "fhir_index.json",
        _data_dir().parent.parent / "fhir" / "out" / "fhir_index.json",
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text())
    return {}


def fhir_bundle(name: str) -> dict | None:
    candidates = [
        _data_dir() / f"{name}.json",
        _data_dir().parent.parent / "fhir" / "out" / f"{name}.json",
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text())
    return None


def draws_for(site_id: str, drug: str) -> list[float] | None:
    """Return stored RQ draws for a (site, drug) pair from draws.bin."""
    index = _load_json("draws_index.json")
    if not index:
        return None
    entries = index.get("entries", [])
    match = next(
        (e for e in entries if e["site_id"] == site_id and e["drug"] == drug),
        None,
    )
    if match is None:
        return None

    bin_path = _data_dir() / "draws.bin"
    if not bin_path.exists():
        return None

    offset_bytes = match["offset"] * 4  # float32
    count = match["count"]
    with open(bin_path, "rb") as f:
        f.seek(offset_bytes)
        raw = f.read(count * 4)
    return list(struct.unpack(f"<{count}f", raw))
