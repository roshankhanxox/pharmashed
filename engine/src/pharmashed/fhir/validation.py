"""Turn HL7 validator output into a summary and the fhir_index.json validation record.

The validator (scripts/validate_fhir.py runs it) writes one OperationOutcome per input file, wrapped
in a collection Bundle in the same order as the files were passed. This module is pure so it can be
tested without Java: summarize() counts issues, validation_block() builds the record the FHIR tab
badge reads, and record() writes it into fhir_index.json.

The record is only ever written by a real validator run. Rebuilding the bundles rewrites the index
with status "unknown" (see builder._build_fhir_index), so a stale pass can never outlive a rebuild.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _normalise(text: str) -> str:
    """Group messages that differ only by resource ids or indexes."""
    text = re.sub(r"\[\d+\]", "[n]", text)
    return re.sub(r"\b[A-Za-z]+-[A-Za-z0-9-]*\d+\b", "<id>", text)[:170]


def summarize(outcome_bundle: dict, bundle_names: list[str]) -> dict:
    """Count errors and warnings per bundle and overall.

    Args:
        outcome_bundle: the validator's output Bundle (one OperationOutcome per entry).
        bundle_names: names of the validated files, in the order they were passed to the validator.

    Returns:
        {"per_bundle": {name: {"errors", "warnings"}}, "errors", "warnings",
         "top_errors": [(message, count)], "top_warnings": [(message, count)]}
    """
    entries = outcome_bundle.get("entry", [])
    if len(entries) != len(bundle_names):
        raise ValueError(
            f"validator returned {len(entries)} result(s) for {len(bundle_names)} file(s); "
            "refusing to attribute results to the wrong bundle"
        )

    per_bundle: dict[str, dict[str, int]] = {}
    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    for name, entry in zip(bundle_names, entries):
        issues = entry["resource"].get("issue", [])
        n_err = n_warn = 0
        for issue in issues:
            message = _normalise(issue.get("details", {}).get("text", ""))
            if issue["severity"] in ("error", "fatal"):
                n_err += 1
                errors[message] += 1
            elif issue["severity"] == "warning":
                n_warn += 1
                warnings[message] += 1
        per_bundle[name] = {"errors": n_err, "warnings": n_warn}

    return {
        "per_bundle": per_bundle,
        "errors": sum(errors.values()),
        "warnings": sum(warnings.values()),
        "top_errors": errors.most_common(10),
        "top_warnings": warnings.most_common(10),
    }


def validation_block(summary: dict, validator_version: str | None, now: datetime | None = None) -> dict:
    """The fhir_index.json `validation` object for a finished run."""
    now = now or datetime.now(timezone.utc)
    return {
        "status": "pass" if summary["errors"] == 0 else "fail",
        "errors": summary["errors"],
        "warnings": summary["warnings"],
        "validator_version": validator_version,
        "ran_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ci_log_url": None,
    }


def record(index_path: Path, block: dict) -> None:
    """Write the validation record into fhir_index.json, leaving everything else untouched."""
    index_path = Path(index_path)
    index = json.loads(index_path.read_text())
    index["validation"] = block
    index_path.write_text(json.dumps(index, indent=2, default=str))
