"""The logic that turns HL7 validator output into a pass/fail record (no Java needed)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pharmashed.fhir.validation import record, summarize, validation_block


def _outcome(*per_file: list[tuple[str, str]]) -> dict:
    """A validator output bundle: one OperationOutcome per file, issues given as (severity, text)."""
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "OperationOutcome",
                          "issue": [{"severity": s, "details": {"text": t}} for s, t in issues]}}
            for issues in per_file
        ],
    }


def test_counts_errors_and_warnings_per_bundle_and_overall():
    s = summarize(
        _outcome([("warning", "narrative"), ("warning", "narrative")], [("error", "bad"), ("information", "fyi")]),
        ["locations", "predictions-TLS"],
    )
    assert s["per_bundle"] == {"locations": {"errors": 0, "warnings": 2}, "predictions-TLS": {"errors": 1, "warnings": 0}}
    assert (s["errors"], s["warnings"]) == (1, 2)


def test_fatal_counts_as_an_error():
    assert summarize(_outcome([("fatal", "boom")]), ["x"])["errors"] == 1


def test_messages_that_differ_only_by_id_are_grouped():
    s = summarize(
        _outcome([("error", "Bundle.entry[3].resource/*Location/site-TLS-01*/ bad"),
                  ("error", "Bundle.entry[9].resource/*Location/site-GNT-07*/ bad")]),
        ["x"],
    )
    assert len(s["top_errors"]) == 1 and s["top_errors"][0][1] == 2


def test_refuses_to_attribute_results_to_the_wrong_files():
    """If the validator returned a different number of results than files, results would be mislabelled."""
    with pytest.raises(ValueError, match="refusing"):
        summarize(_outcome([], []), ["only-one"])


def test_pass_only_when_there_are_no_errors_and_warnings_do_not_fail_a_run():
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    ok = validation_block({"errors": 0, "warnings": 1513}, "6.10.4", now)
    assert ok == {"status": "pass", "errors": 0, "warnings": 1513, "validator_version": "6.10.4",
                  "ran_at": "2026-09-29T12:00:00Z", "ci_log_url": None}
    assert validation_block({"errors": 3, "warnings": 0}, "6.10.4", now)["status"] == "fail"


def test_record_replaces_only_the_validation_block(tmp_path):
    path = tmp_path / "fhir_index.json"
    path.write_text(json.dumps({"meta": {"x": 1}, "validation": {"status": "unknown"}, "bundles": [1, 2]}))
    record(path, {"status": "pass", "errors": 0})
    data = json.loads(path.read_text())
    assert data["validation"] == {"status": "pass", "errors": 0}
    assert data["meta"] == {"x": 1} and data["bundles"] == [1, 2]
