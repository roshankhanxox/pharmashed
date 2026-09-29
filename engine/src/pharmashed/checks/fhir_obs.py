"""Build FHIR reference-measurement Observations from observed_rodrigues2025.csv (M14/M15).

Lives in checks/ because it is the only package permitted to read data/observed/.
Call build_reference_observations() and pass the result to fhir.builder.build_all().
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pharmashed.checks.observed import load_observed

_ATC_SYSTEM = "http://www.whocc.no/atc"
_HL7_OBS_CAT = "http://terminology.hl7.org/CodeSystem/observation-category"

_SCOPE_CITY: dict[str, str] = {
    "Toulouse": "TLS", "Ghent": "GNT", "Benevento": "BNV",
    "Coimbra": "CBR", "Oslo": "OSL",
}

_COMPOUND_DRUG: dict[str, str] = {
    "acetaminophen": "paracetamol",
    "carbamazepine": "carbamazepine",
    "irbesartan": "irbesartan",
    "atenolol": "atenolol",
    "losartan": "losartan",
    "citalopram": "citalopram",
}

_METRIC_DISPLAY: dict[str, str] = {
    "max_concentration": "Maximum observed concentration",
    "median_concentration": "Median observed concentration",
    "detection_frequency": "Detection frequency",
}

_DRUG_ATC: dict[str, str] = {
    "carbamazepine": "N03AF01",
    "atenolol":      "C07AB03",
    "losartan":      "C09CA01",
    "irbesartan":    "C09CA04",
    "paracetamol":   "N02BE01",
    "citalopram":    "N06AB04",
}

_REF_TAG = "external-reference-R1"
_REF_DISPLAY = "Rodrigues et al. 2025, J. Hazard. Mater. 499:139946"


def build_reference_observations(path: Path | None = None) -> list[dict]:
    """Build FHIR Observation resources from the observed CSV.

    Args:
        path: override path to the observed CSV (default: data/observed/).

    Returns:
        List of FHIR Observation dicts with category=laboratory.
    """
    rows = load_observed(path)
    obs_list: list[dict[str, Any]] = []

    for row in rows:
        compound = row.get("compound", "")
        metric = row.get("metric", "")
        scope = row.get("scope", "")
        raw_value = row.get("value", "")
        unit = row.get("unit", "")

        if compound not in _COMPOUND_DRUG:
            continue
        if metric not in _METRIC_DISPLAY:
            continue
        if scope not in _SCOPE_CITY:
            continue

        try:
            value = float(raw_value)
        except (ValueError, TypeError):
            continue

        drug = _COMPOUND_DRUG[compound]
        city = _SCOPE_CITY[scope]
        atc = _DRUG_ATC.get(drug, "unknown")
        obs_id = f"ref-{city}-{drug}-{metric.replace('_', '-')}"  # FHIR ids allow letters, digits, - and .
        ucum_unit = "ng/L" if "ng" in unit else ("%" if "percent" in unit else "1")

        obs: dict[str, Any] = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": {"tag": [{"system": "https://pharmashed.example/fhir/CodeSystem/pharmashed-tags", "code": _REF_TAG, "display": "External reference measurement (R1)"}]},
            "status": "final",
            "category": [
                {"coding": [{"system": _HL7_OBS_CAT, "code": "laboratory"}]}
            ],
            "code": {
                "coding": [{"system": _ATC_SYSTEM, "code": atc, "display": drug}],
                "text": f"{drug} {_METRIC_DISPLAY[metric]}",
            },
            "subject": {"reference": f"Location/site-{city}-ref"},
            "valueQuantity": {
                "value": value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": ucum_unit,
            },
        }
        # Keep the source citation with the value now that the tag's display must match its code system.
        notes = [{"text": _REF_DISPLAY}]
        note = row.get("note", "")
        if note:
            notes.append({"text": note})
        obs["note"] = notes
        obs_list.append(obs)

    return obs_list
