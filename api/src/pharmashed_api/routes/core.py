"""Core read-only API routes (M16)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from pharmashed_api import data as _data

router = APIRouter()


@router.get("/health")
def health():
    meta = _data.results().get("meta", {})
    return {"ok": True, "engine_version": meta.get("engine_version", "unknown")}


@router.get("/meta")
def meta():
    return _data.results().get("meta", {})


@router.get("/sites")
def sites():
    return _data.sites()


@router.get("/results")
def results():
    return _data.results()


@router.get("/checks")
def checks():
    d = _data.checks()
    if not d:
        raise HTTPException(404, "checks.json not found — run consistency checks first")
    return d


@router.get("/methodology")
def methodology():
    return _data.methodology()


@router.get("/glossary")
def glossary():
    return _data.glossary()


@router.get("/provenance/{key:path}")
def provenance(key: str):
    prov = _data.provenance()
    if key not in prov:
        raise HTTPException(404, f"provenance key {key!r} not found")
    return prov[key]


@router.get("/draws.bin", response_class=FileResponse)
def draws_bin():
    import os  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    path = Path(os.environ.get("PHARMASHED_DATA", "data/build")) / "draws.bin"
    if not path.exists():
        raise HTTPException(404, "draws.bin not found")
    return FileResponse(str(path), media_type="application/octet-stream")
