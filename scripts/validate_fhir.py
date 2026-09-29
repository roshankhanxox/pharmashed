"""Validate the FHIR bundles in fhir/out/ against the OneAquaHealth IG with the official HL7 validator.

What it does, in order (each step is skipped if already done):
  1. downloads the HL7 validator CLI into fhir/validator/ (git-ignored, about 200 MB)
  2. downloads the OneAquaHealth IG source at a pinned commit into fhir/ig/oah/ (git-ignored)
  3. compiles the IG's FSH source into profiles with SUSHI (npx, pinned version)
  4. validates every bundle with those profiles plus our own terminology (fhir/terminology/)
  5. writes a summary and records the result in fhir/out/fhir_index.json (`validation`)

The IG is published only as FSH source, not as a package, so the profiles are compiled locally.
Requires: Java (11+), Node/npm, network for the first run. Re-run `make release` afterwards so the
committed snapshot the deployed API serves carries the result.

    uv run python scripts/validate_fhir.py
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine" / "src"))

from pharmashed.fhir.validation import record, summarize, validation_block  # noqa: E402

FHIR_OUT = ROOT / "fhir" / "out"
TERMINOLOGY = ROOT / "fhir" / "terminology"
VALIDATOR_DIR = ROOT / "fhir" / "validator"
JAR = VALIDATOR_DIR / "validator_cli.jar"
IG_DIR = ROOT / "fhir" / "ig"
IG_SRC = IG_DIR / "oah"
RESULTS = IG_DIR / "results"

JAR_URL = "https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar"
# The OneAquaHealth IG has no published package; pin the source so the check is reproducible.
OAH_COMMIT = "b907cf0869b59d82d9138b3d147fca66f333d911"  # hl7-eu/oah master, 2026-06-11
SUSHI = "fsh-sushi@3.20.1"
FHIR_VERSION = "4.0.1"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url.split('?')[0]} ...")
    with urllib.request.urlopen(url, timeout=600) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def ensure_validator() -> None:
    if not JAR.exists():
        _download(JAR_URL, JAR)
    digest = hashlib.sha256(JAR.read_bytes()).hexdigest()
    print(f"validator jar: {JAR.stat().st_size / 1e6:.0f} MB, sha256 {digest[:16]}...")


def ensure_ig_profiles() -> Path:
    """Fetch the pinned IG source and compile it with SUSHI; return the compiled resources dir."""
    compiled = IG_SRC / "fsh-generated" / "resources"
    marker = IG_SRC / ".commit"
    if compiled.exists() and marker.exists() and marker.read_text().strip() == OAH_COMMIT:
        return compiled
    if IG_SRC.exists():
        shutil.rmtree(IG_SRC)
    print(f"fetching hl7-eu/oah@{OAH_COMMIT[:8]} ...")
    url = f"https://codeload.github.com/hl7-eu/oah/tar.gz/{OAH_COMMIT}"
    with urllib.request.urlopen(url, timeout=300) as resp:
        data = resp.read()
    IG_SRC.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            member.name = member.name.split("/", 1)[1] if "/" in member.name else ""
            if member.name:
                tar.extract(member, IG_SRC, filter="data")
    print(f"compiling the IG with {SUSHI} ...")
    subprocess.run(["npx", "--yes", SUSHI, str(IG_SRC)], check=True)
    (IG_SRC / ".commit").write_text(OAH_COMMIT + "\n")
    return compiled


def bundle_files() -> list[Path]:
    index = json.loads((FHIR_OUT / "fhir_index.json").read_text())
    return [FHIR_OUT / f"{b['name']}.json" for b in index["bundles"]]


def run_validator(files: list[Path], profiles: Path) -> tuple[dict, str | None]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / "validation.json"
    log = RESULTS / "validation.log"
    cmd = [
        "java", "-jar", str(JAR), *map(str, files),
        "-version", FHIR_VERSION, "-ig", str(profiles), "-ig", str(TERMINOLOGY),
        "-output", str(output), "-level", "warnings",
    ]
    print(f"validating {len(files)} bundles ...")
    with open(log, "w") as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=False)
    if not output.exists():
        raise SystemExit(f"the validator produced no output; see {log}")
    match = re.search(r"FHIR Validation tool Version ([\d.]+)", log.read_text())
    return json.loads(output.read_text()), match.group(1) if match else None


def main() -> None:
    if not (FHIR_OUT / "fhir_index.json").exists():
        raise SystemExit("fhir/out/fhir_index.json not found. Run `uv run pharmashed fhir` first.")
    ensure_validator()
    profiles = ensure_ig_profiles()
    files = bundle_files()
    outcome, version = run_validator(files, profiles)
    summary = summarize(outcome, [f.stem for f in files])

    print(f"\n{'bundle':28s} {'errors':>7s} {'warnings':>9s}")
    for name, counts in summary["per_bundle"].items():
        print(f"{name:28s} {counts['errors']:7d} {counts['warnings']:9d}")
    print(f"{'TOTAL':28s} {summary['errors']:7d} {summary['warnings']:9d}")
    for label, key in (("errors", "top_errors"), ("warnings", "top_warnings")):
        if summary[key]:
            print(f"\nmost common {label}:")
            for message, count in summary[key][:5]:
                print(f"  {count:5d}  {message}")

    block = validation_block(summary, version)
    record(FHIR_OUT / "fhir_index.json", block)
    print(f"\nrecorded in fhir/out/fhir_index.json: {block['status']} "
          f"({block['errors']} errors, {block['warnings']} warnings, validator {version})")
    raise SystemExit(0 if block["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
