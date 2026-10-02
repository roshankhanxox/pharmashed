"""Citizen observations in FHIR: unverified by construction, anonymous, linked to a site."""

from datetime import datetime, timezone

from pharmashed.fhir.builder import build_citizen_observation, build_citizen_observations, citizen_bundle

REPORT = {
    "id": "abc", "site_id": "TLS-01", "visited_at": "2026-05-10T09:30:00Z", "is_sample": False,
    "checklist": {"water_colour": "cloudy", "animals": ["birds", "fish"], "foam": "", "smell": None},
}


def test_shape_and_status():
    obs = build_citizen_observation(REPORT)
    assert obs["resourceType"] == "Observation" and obs["id"] == "cit-abc"
    assert obs["status"] == "preliminary"                       # unverified is never "final"
    assert "profile" not in obs["meta"]                         # the OAH profile fixes status to final, so we do not claim it
    assert obs["category"][0]["coding"][0]["code"] == "citizen-observation"
    assert obs["subject"] == {"reference": "Location/site-TLS-01"}
    assert obs["effectiveDateTime"] == "2026-05-10T09:30:00Z"
    assert {t["code"] for t in obs["meta"]["tag"]} == {"citizen-report", "unverified"}


def test_components_skip_empty_answers_and_repeat_for_lists():
    comps = build_citizen_observation(REPORT)["component"]
    pairs = [(c["code"]["coding"][0]["code"], c["valueString"]) for c in comps]
    assert pairs == [("water-colour", "cloudy"), ("animals", "birds"), ("animals", "fish")]


def test_no_person_and_no_free_text_is_exported():
    obs = build_citizen_observation({**REPORT, "author": "RiverPat", "note": "call me 0612345678", "user_id": "u1"})
    text = str(obs)
    assert "RiverPat" not in text and "0612345678" not in text and "u1" not in text
    assert obs["performer"] == [{"reference": "Organization/citizen-reports"}]


def test_samples_are_tagged_and_datetimes_are_converted():
    obs = build_citizen_observation({**REPORT, "is_sample": True, "visited_at": datetime(2026, 5, 10, 11, 30, tzinfo=timezone.utc)})
    assert "sample" in {t["code"] for t in obs["meta"]["tag"]}
    assert obs["effectiveDateTime"] == "2026-05-10T11:30:00Z"


def test_reports_that_cannot_be_exported_are_dropped():
    assert build_citizen_observation({**REPORT, "site_id": None}) is None          # no Location to point at
    assert build_citizen_observation({**REPORT, "checklist": {"foam": ""}}) is None  # nothing answered
    assert len(build_citizen_observations([REPORT, {**REPORT, "site_id": None}])) == 1


def test_bundle_has_the_organization_first_and_full_urls():
    bundle = citizen_bundle([REPORT])
    assert bundle["type"] == "collection" and bundle["id"] == "citizen-observations"
    assert [e["resource"]["resourceType"] for e in bundle["entry"]] == ["Organization", "Observation"]
    assert all(e["fullUrl"].startswith("https://pharmashed.example/fhir/") for e in bundle["entry"])
