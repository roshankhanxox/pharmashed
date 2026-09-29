"""Copy the built data into data/release/, the committed snapshot the deployed API serves.

data/build/ and fhir/out/ are git-ignored (they are regenerated), so a deployed server has nothing to
read. data/release/ is the small, committed copy of exactly what the app needs. JSON is written
compactly (one line per file) so the snapshot does not add hundreds of thousands of lines to a diff.

Layout (what pharmashed_api.data expects when PHARMASHED_DATA=data/release):
    results.json sites.json provenance.json methodology.json glossary.json checks.json
    draws_index.json draws.bin fhir_index.json RELEASE.json
    fhir/out/<bundle>.json

Run after: pharmashed build, pharmashed freeze, pharmashed checks.
    uv run python scripts/make_release.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "data" / "build"
FHIR_OUT = ROOT / "fhir" / "out"
RELEASE = ROOT / "data" / "release"

JSON_FILES = [
    "results.json", "sites.json", "provenance.json", "methodology.json",
    "glossary.json", "checks.json", "draws_index.json",
]


def _compact(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(json.loads(src.read_text()), separators=(",", ":"), ensure_ascii=False))


def main() -> None:
    missing = [n for n in [*JSON_FILES, "draws.bin"] if not (BUILD / n).exists()]
    if missing or not (FHIR_OUT / "fhir_index.json").exists():
        raise SystemExit(
            f"missing build output: {missing or ['fhir/out/fhir_index.json']}. "
            "Run `pharmashed build`, `pharmashed freeze` and `pharmashed checks` first."
        )

    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True)

    for name in JSON_FILES:
        _compact(BUILD / name, RELEASE / name)
    shutil.copy2(BUILD / "draws.bin", RELEASE / "draws.bin")
    _compact(FHIR_OUT / "fhir_index.json", RELEASE / "fhir_index.json")
    for bundle in sorted(FHIR_OUT.glob("*.json")):
        if bundle.name != "fhir_index.json":
            _compact(bundle, RELEASE / "fhir" / "out" / bundle.name)

    meta = json.loads((RELEASE / "results.json").read_text())["meta"]
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    (RELEASE / "RELEASE.json").write_text(json.dumps({
        "frozen_tag": meta.get("frozen_tag"),
        "n_draws": meta.get("n_draws"),
        "all_params_cited": meta.get("all_params_cited"),
        "built_from_commit": commit,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n")

    total = sum(f.stat().st_size for f in RELEASE.rglob("*") if f.is_file())
    print(f"wrote {RELEASE} ({total / 1e6:.1f} MB, frozen_tag={meta.get('frozen_tag')})")


if __name__ == "__main__":
    main()
