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

# api/src/pharmashed_api/data.py -> parents[3] is the repo root (parents[4] is the folder above it).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUILD = _REPO_ROOT / "data" / "build"      # regenerated locally, git-ignored
_RELEASE = _REPO_ROOT / "data" / "release"  # committed snapshot (scripts/make_release.py) for deployment


def _default_data_dir() -> Path:
    """data/build when it has been generated (local development), else the committed data/release.

    A deployed server has no data/build (it is git-ignored), so it falls through to the snapshot.
    """
    return _BUILD if (_BUILD / "results.json").exists() else _RELEASE


def _data_dir() -> Path:
    override = os.environ.get("PHARMASHED_DATA")
    return Path(override) if override else _default_data_dir()


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
        _data_dir() / f"{name}.json",                              # flat next to fixtures
        _data_dir() / "fhir" / "out" / f"{name}.json",            # fixtures/fhir/out/<name>.json
        _data_dir().parent.parent / "fhir" / "out" / f"{name}.json",  # data/fhir/out/<name>.json
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
