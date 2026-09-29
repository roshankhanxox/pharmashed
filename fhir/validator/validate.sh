#!/usr/bin/env bash
# Validate fhir/out/ against the OneAquaHealth IG with the HL7 validator (M15).
# Thin wrapper: the work is in scripts/validate_fhir.py (downloads the validator, fetches and compiles the
# IG at a pinned commit, validates every bundle, records the result in fhir/out/fhir_index.json).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
exec uv run python scripts/validate_fhir.py "$@"
