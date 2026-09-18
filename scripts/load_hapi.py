"""Load PharmaShed FHIR bundles into a local HAPI server (M15).

Converts collection bundles to transaction bundles and POSTs them.
Usage: python scripts/load_hapi.py [--fhir-out fhir/out] [--hapi http://localhost:8080/fhir]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FHIR_OUT = _REPO_ROOT / "fhir" / "out"
_DEFAULT_HAPI = "http://localhost:8080/fhir"

_LOAD_ORDER = [
    "terminology.json",
    "locations.json",
    "consumption.json",
    "reference-measurements.json",
]


def _collection_to_transaction(bundle: dict) -> dict:
    """Convert a collection bundle to a transaction bundle with PUT by id."""
    entries = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rt = resource.get("resourceType", "")
        rid = resource.get("id", "")
        entries.append({
            "resource": resource,
            "request": {
                "method": "PUT",
                "url": f"{rt}/{rid}" if rid else rt,
            },
        })
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries,
    }


def load_bundle(path: Path, hapi_base: str) -> int:
    bundle = json.loads(path.read_text())
    tx = _collection_to_transaction(bundle)
    resp = requests.post(
        f"{hapi_base}/",
        json=tx,
        headers={"Content-Type": "application/fhir+json"},
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    loaded = len(result.get("entry", []))
    print(f"  [{path.name}] loaded {loaded} resources → HTTP {resp.status_code}")
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fhir-out", default=str(_DEFAULT_FHIR_OUT))
    parser.add_argument("--hapi", default=_DEFAULT_HAPI)
    args = parser.parse_args()

    fhir_out = Path(args.fhir_out)
    hapi = args.hapi.rstrip("/")

    if not fhir_out.exists():
        print(f"ERROR: {fhir_out} does not exist — run `make fhir-build` first")
        sys.exit(1)

    total = 0
    # Load in order, then any city prediction bundles
    for name in _LOAD_ORDER:
        p = fhir_out / name
        if p.exists():
            total += load_bundle(p, hapi)

    for p in sorted(fhir_out.glob("predictions-*.json")):
        total += load_bundle(p, hapi)

    print(f"Done. Total resources loaded: {total}")


if __name__ == "__main__":
    main()
