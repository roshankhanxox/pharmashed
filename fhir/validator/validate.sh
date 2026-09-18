#!/usr/bin/env bash
# FHIR validation using the HL7 validator CLI (M15).
# Downloads validator_cli.jar if absent.
# Usage: ./fhir/validator/validate.sh [--ig <package>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
JAR="$SCRIPT_DIR/validator_cli.jar"
FHIR_OUT="$REPO_ROOT/fhir/out"
TERM_DIR="$REPO_ROOT/fhir/terminology"
OAH_IG_URL="https://build.fhir.org/ig/hl7-eu/oah/package.tgz"
VALIDATION_OUT="$FHIR_OUT/validation.json"

# Download validator CLI if absent
if [ ! -f "$JAR" ]; then
    echo "[validate] Downloading HL7 validator CLI..."
    RELEASE_URL="https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar"
    curl -fsSL -o "$JAR" "$RELEASE_URL"
    echo "[validate] Downloaded validator_cli.jar"
fi

echo "[validate] Validating FHIR resources in $FHIR_OUT ..."
java -jar "$JAR" \
    "$FHIR_OUT"/*.json \
    -version 4.0.1 \
    -ig "$TERM_DIR" \
    -ig "$OAH_IG_URL" \
    -output "$VALIDATION_OUT" \
    -level warnings \
    || true  # don't exit on validator issues — we parse the output

# Parse and summarise the OperationOutcome
python3 - "$VALIDATION_OUT" <<'PYEOF'
import json, sys
path = sys.argv[1]
try:
    data = json.loads(open(path).read())
except Exception as e:
    print(f"[validate] Could not read {path}: {e}")
    sys.exit(1)

issues = data.get("issue", []) if data.get("resourceType") == "OperationOutcome" else []
errors   = [i for i in issues if i.get("severity") in ("error", "fatal")]
warnings = [i for i in issues if i.get("severity") == "warning"]

for e in errors:
    print(f"  ERROR: {e.get('diagnostics', '')}")
for w in warnings[:10]:
    print(f"  WARN:  {w.get('diagnostics', '')}")

print(f"[validate] Result: {len(errors)} error(s), {len(warnings)} warning(s)")
if errors:
    sys.exit(1)
PYEOF

echo "[validate] Done."
