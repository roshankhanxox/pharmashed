"""FHIR bundle serving routes (M16)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pharmashed_api import data as _data

router = APIRouter(prefix="/fhir")


@router.get("/index")
def fhir_index():
    idx = _data.fhir_index()
    if not idx:
        raise HTTPException(404, "fhir_index.json not found — run `make fhir-build` first")
    return idx


@router.get("/bundle/{name}")
def fhir_bundle(name: str):
    bundle = _data.fhir_bundle(name)
    if bundle is None:
        raise HTTPException(404, f"bundle {name!r} not found")
    return bundle
