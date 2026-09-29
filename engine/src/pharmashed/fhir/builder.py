"""FHIR resource builder (M14).

Converts build artifacts (results.json, sites.json, consumption.csv)
into FHIR R4 bundles and writes them to fhir/out/.

D17: Prediction Observations use the OAH IG profile.
D37: Locations apply the OAH IG Location profile.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]

# FHIR system constants
_ATC_SYSTEM = "http://www.whocc.no/atc"
_CAT_CS = "https://pharmashed.example/fhir/CodeSystem/observation-category"
_COMP_CS = "https://pharmashed.example/fhir/CodeSystem/components"
_CONS_CS = "https://pharmashed.example/fhir/CodeSystem/consumption"
_HL7_OBS_CAT = "http://terminology.hl7.org/CodeSystem/observation-category"

# OAH IG profiles (D17, D37)
_OAH_PREDICTION_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-with-component-oah"
_OAH_LOCATION_PROFILE   = "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"

# Identity and provenance of our own resources
_BASE = "https://pharmashed.example/fhir"
_SITE_ID_SYSTEM = f"{_BASE}/site-id"
_TAG_CS = f"{_BASE}/CodeSystem/pharmashed-tags"
_ORG_ID = "pharmashed"

# Drug → ATC (illustrative codes; A1-A6 will source real codes)
_DRUG_ATC: dict[str, str] = {
    "carbamazepine": "N03AF01",
    "atenolol":      "C07AB03",
    "losartan":      "C09CA01",
    "irbesartan":    "C09CA04",
    "paracetamol":   "N02BE01",
    "citalopram":    "N06AB04",
}

_COUNTRY_ISO: dict[str, str] = {
    "FR": "FR", "BE": "BE", "IT": "IT", "PT": "PT", "NO": "NO",
}

_CITY_COUNTRY: dict[str, str] = {
    "TLS": "FR", "GNT": "BE", "BNV": "IT", "CBR": "PT", "OSL": "NO",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ref(resource_type: str, id_: str) -> dict:
    return {"reference": f"{resource_type}/{id_}"}


# --- Location resources ---

def _build_location(site: dict) -> dict:
    lon, lat = site["lonlat"]
    return {
        "resourceType": "Location",
        "id": f"site-{site['id']}",
        "meta": {
            "profile": [_OAH_LOCATION_PROFILE],
            "tag": [{"system": _TAG_CS, "code": "synthetic", "display": "Synthetic placement"}],
        },
        "identifier": [{"system": _SITE_ID_SYSTEM, "value": site["id"]}],
        "status": "active",
        "name": site.get("name", site["id"]),
        "mode": "instance",
        "description": (
            f"Synthetic monitoring site on {site['city']} urban waterway. "
            f"Size class {site['size_class']}. Population buffer: {site.get('population_buffer', 0):.0f} inhabitants."
        ),
        "position": {"longitude": lon, "latitude": lat},
        "extension": [
            {
                "url": "https://pharmashed.example/fhir/StructureDefinition/site-size-class",
                "valueCode": site["size_class"],
            }
        ],
    }


def build_locations(sites_json: dict) -> list[dict]:
    return [_build_location(s) for s in sites_json.get("sites", [])]


# --- Group (population) resources ---

def _build_group(country: str) -> dict:
    return {
        "resourceType": "Group",
        "id": f"pop-{country}",
        "type": "person",
        "actual": False,
        "name": f"Population in {country}",
        "characteristic": [
            {
                "code": {"text": "country"},
                "valueCodeableConcept": {
                    "coding": [{"system": "urn:iso:std:iso:3166", "code": country}]
                },
                "exclude": False,
            }
        ],
    }


def build_groups(countries: list[str]) -> list[dict]:
    return [_build_group(c) for c in sorted(set(countries))]


# --- Consumption Observations ---

def _build_consumption_obs(country: str, drug: str, row: dict) -> dict:
    atc = _DRUG_ATC.get(drug, "unknown")
    value = row.get("ddd_per_1000_per_day") or (
        (row.get("group_value") or 0) * (row.get("molecule_share") or 1)
    )
    components = [
        {
            "code": {"coding": [{"system": _CONS_CS, "code": "ddd-per-1000-per-day"}]},
            "valueQuantity": {
                "value": round(float(value or 0), 6),
                "unit": "DDD/1000 inhabitants/day",
                "system": "https://pharmashed.example/fhir/units",
                "code": "DDD/1000/day",
            },
        }
    ]
    granularity = row.get("granularity") or "unknown"
    gran_code = "granularity-molecule" if granularity == "molecule" else "granularity-group-downscaled"
    components.append({
        "code": {"coding": [{"system": _CONS_CS, "code": gran_code}]},
        "valueString": granularity,
    })

    obs: dict[str, Any] = {
        "resourceType": "Observation",
        "id": f"cons-{country}-{drug}",
        "status": "final",
        "category": [
            {"coding": [{"system": _HL7_OBS_CAT, "code": "survey", "display": "Survey"}]}
        ],
        "code": {
            "coding": [{"system": _ATC_SYSTEM, "code": atc, "display": drug}],
            "text": f"{drug} consumption",
        },
        "subject": _ref("Group", f"pop-{country}"),
        "component": components,
    }
    source_url = row.get("source_url")
    if source_url:
        obs["extension"] = [
            {
                "url": "https://pharmashed.example/fhir/StructureDefinition/source-url",
                "valueUrl": source_url,
            }
        ]
    return obs


def build_consumption_observations(consumption_csv_path: Path) -> list[dict]:
    import csv  # noqa: PLC0415

    obs_list = []
    with open(consumption_csv_path, newline="") as f:
        for row in csv.DictReader(f):
            country = row.get("country", "")
            drug = row.get("drug", "")
            if not country or not drug:
                continue
            obs_list.append(_build_consumption_obs(country, drug, row))
    return obs_list


# --- Prediction Observations ---

def _build_prediction_obs(entry: dict, engine_version: str, generated_at: str) -> dict:
    drug = entry["drug"]
    site_id = entry["site_id"]
    atc = _DRUG_ATC.get(drug, "unknown")

    def qty(value: float, unit: str = "ng/L") -> dict:
        return {
            "value": round(value, 6),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": "ng/L" if unit == "ng/L" else unit,
        }

    components = [
        {
            "code": {"coding": [{"system": _COMP_CS, "code": "pec-p05"}]},
            "valueQuantity": qty(entry["pec_ng_l"]["p5"]),
        },
        {
            "code": {"coding": [{"system": _COMP_CS, "code": "pec-p50"}]},
            "valueQuantity": qty(entry["pec_ng_l"]["p50"]),
        },
        {
            "code": {"coding": [{"system": _COMP_CS, "code": "pec-p95"}]},
            "valueQuantity": qty(entry["pec_ng_l"]["p95"]),
        },
        {
            "code": {"coding": [{"system": _COMP_CS, "code": "rq-p50"}]},
            "valueQuantity": qty(entry["rq"]["p50"], "1"),
        },
        {
            "code": {"coding": [{"system": _COMP_CS, "code": "priority-score"}]},
            "valueQuantity": qty(entry["score"], "1"),
        },
        {
            "code": {"coding": [{"system": _COMP_CS, "code": "lod-share"}]},
            "valueQuantity": qty(entry["lod_share"], "1"),
        },
    ]

    country = _CITY_COUNTRY.get(site_id[:3], "")
    derived_from = [_ref("Observation", f"cons-{country}-{drug}")] if country else []

    meta_tags = [{"system": _TAG_CS, "code": "model-output"}]
    all_cited = entry.get("all_params_cited", True)
    if not all_cited:
        meta_tags.append({"system": _TAG_CS, "code": "illustrative-parameter",
                          "display": "Illustrative parameters"})

    return {
        "resourceType": "Observation",
        "id": f"pred-{site_id}-{drug}",
        "meta": {
            "profile": [_OAH_PREDICTION_PROFILE],
            "tag": meta_tags,
        },
        "status": "final",
        "category": [
            {
                "coding": [{"system": _CAT_CS, "code": "model-prediction",
                            "display": "Model prediction"}]
            }
        ],
        "code": {
            "coding": [{"system": _ATC_SYSTEM, "code": atc, "display": drug}],
            "text": f"{drug} predicted concentration",
        },
        "subject": _ref("Location", f"site-{site_id}"),
        "effectiveDateTime": generated_at,
        "performer": [_ref("Organization", _ORG_ID)],
        "method": {"text": f"PharmaShed PEC {engine_version}, variant full"},
        "component": components,
        "derivedFrom": derived_from,
    }


def build_prediction_observations(results_json: dict) -> list[dict]:
    engine_version = results_json.get("meta", {}).get("engine_version", "0.0.0")
    all_cited = results_json.get("meta", {}).get("all_params_cited", True)
    generated_at = results_json.get("meta", {}).get("generated_at") or _now()
    obs_list = []
    for entry in results_json.get("results", []):
        entry = dict(entry)
        entry["all_params_cited"] = all_cited
        obs_list.append(_build_prediction_obs(entry, engine_version, generated_at))
    return obs_list


# --- Reference measurement Observations ---
# build_reference_observations lives in checks/fhir_obs.py (separation rule: M12).
# Call it from there and pass the list here via build_all(ref_obs=...).


# --- Bundle building ---

def build_organization() -> dict:
    """The Organization that performs (runs) the model; referenced by every prediction."""
    return {
        "resourceType": "Organization",
        "id": _ORG_ID,
        "meta": {"tag": [{"system": _TAG_CS, "code": "model-output"}]},
        "active": True,
        "name": "PharmaShed (model run)",
    }


def _collection_bundle(id_: str, resources: list[dict]) -> dict:
    """A collection bundle. Every entry gets a fullUrl (required outside transactions/batches),
    built from the resource type and id so relative references like Location/site-TLS-01 resolve."""
    return {
        "resourceType": "Bundle",
        "id": id_,
        "type": "collection",
        "entry": [
            {"fullUrl": f"{_BASE}/{r['resourceType']}/{r['id']}", "resource": r}
            for r in resources
        ],
    }


# --- FhirIndex ---

def _build_fhir_index(
    bundles_meta: list[dict],
    resource_counts: dict[str, int],
    oah_example_counts: dict | None = None,
) -> dict:
    from pharmashed.contracts import (  # noqa: PLC0415
        FhirBundle, FhirIndex, FhirIndexMeta, FhirValidation, OahExampleCounts, QueryDemo, QueryResult,
    )

    return FhirIndex(
        meta=FhirIndexMeta(generated_at=datetime.now(timezone.utc)),
        resource_counts=resource_counts,
        bundles=[FhirBundle(**b) for b in bundles_meta],
        oah_example_counts=OahExampleCounts(**oah_example_counts) if oah_example_counts else None,
        validation=FhirValidation(
            status="unknown",
            errors=0,
            warnings=0,
            validator_version=None,
            ran_at=None,
            ci_log_url=None,
        ),
        query_demo=QueryDemo(
            laboratory=QueryResult(
                query="Observation?category=laboratory",
                count=resource_counts.get("Observation:laboratory", 0),
            ),
            model_prediction=QueryResult(
                query=f"Observation?category={_CAT_CS}|model-prediction",
                count=resource_counts.get("Observation:model-prediction", 0),
            ),
        ),
    ).model_dump(mode="json")


_OAH_EXAMPLES = _REPO_ROOT / "fhir" / "examples" / "oah-examples.json"
_OAH_SOURCE = "OneAquaHealth IG (hl7-eu/oah)"
_OAH_DESCRIPTION = (
    "Unmodified OAH IG example resources: Benevento air-quality (Benzene, NO2) and Almyros "
    "water-chemistry (aluminium dissolved), demonstrating co-existence of PharmaShed predictions "
    "and consortium environmental data on one FHIR server"
)
_OAH_NOTE = (
    "Air-quality and water-chemistry observations from Benevento (IT) and Almyros (GR): "
    "unmodified IG examples, credited to the OneAquaHealth consortium"
)


def _add_oah_examples(out_dir: Path, bundles_meta: list[dict]) -> dict | None:
    """Copy the IG's example bundle into out_dir untouched and list it in the index.

    Returns the per-type counts for fhir_index.oah_example_counts, or None if the examples file
    is not present.
    """
    if not _OAH_EXAMPLES.exists():
        return None
    bundle = json.loads(_OAH_EXAMPLES.read_text())
    (out_dir / "oah-examples.json").write_text(json.dumps(bundle, indent=2))

    counts: dict[str, int] = {"Location": 0, "Organization": 0, "Observation": 0}
    for entry in bundle.get("entry", []):
        rt = entry.get("resource", {}).get("resourceType", "")
        if rt in counts:
            counts[rt] += 1
    bundles_meta.append({
        "name": "oah-examples",
        "path": "fhir/out/oah-examples.json",
        "resource_type": "Bundle",
        "count": len(bundle.get("entry", [])),
        "source": _OAH_SOURCE,
        "description": _OAH_DESCRIPTION,
    })
    return {**counts, "source": "hl7-eu/oah (OneAquaHealth IG, master branch)", "note": _OAH_NOTE}


def build_all(
    build_dir: Path,
    out_dir: Path,
    ref_obs: list[dict] | None = None,
) -> dict:
    """Build all FHIR bundles from build artifacts.

    Args:
        build_dir: directory with results.json, sites.json.
        out_dir: directory to write FHIR bundle JSON files.
        ref_obs: pre-built reference-measurement Observations (from checks/fhir_obs.py).
                 If None, the reference-measurements bundle is empty.

    Returns:
        FhirIndex dict (also written to out_dir/fhir_index.json).
    """
    build_dir = Path(build_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results_json = json.loads((build_dir / "results.json").read_text())
    sites_json = json.loads((build_dir / "sites.json").read_text())
    consumption_csv = _REPO_ROOT / "data" / "consumption" / "consumption.csv"

    # Resources
    locations = build_locations(sites_json)
    countries = list({s["id"][:3] for s in sites_json.get("sites", [])})
    # Map city codes to countries
    country_codes = list({_CITY_COUNTRY.get(c, c) for c in countries})
    groups = build_groups(country_codes)
    consumption_obs = build_consumption_observations(consumption_csv)
    prediction_obs = build_prediction_observations(results_json)
    ref_obs = ref_obs or []

    # Terminology bundle (copy terminology files)
    import shutil  # noqa: PLC0415
    term_dir = _REPO_ROOT / "fhir" / "terminology"
    term_resources = []
    for tf in sorted(term_dir.glob("*.json")):
        if tf.name == "__init__.py":
            continue
        term_resources.append(json.loads(tf.read_text()))

    # Write bundles
    bundles: list[tuple[str, list[dict]]] = [
        ("terminology", term_resources),
        ("locations", locations + groups + [build_organization()]),
        ("consumption", consumption_obs),
        ("reference-measurements", ref_obs),
    ]

    # Per-city prediction bundles
    cities = sorted({e["site_id"][:3] for e in results_json.get("results", [])})
    for city in cities:
        city_preds = [o for o in prediction_obs if f"-{city}" in o["id"]]
        bundles.append((f"predictions-{city}", city_preds))

    bundles_meta = []
    resource_counts: dict[str, int] = {}
    for bundle_name, resources in bundles:
        bundle = _collection_bundle(bundle_name, resources)
        bundle_path = out_dir / f"{bundle_name}.json"
        bundle_path.write_text(json.dumps(bundle, indent=2))

        for r in resources:
            rt = r.get("resourceType", "Unknown")
            resource_counts[rt] = resource_counts.get(rt, 0) + 1

        try:
            rel = str(bundle_path.relative_to(_REPO_ROOT))
        except ValueError:
            rel = bundle_path.name
        bundles_meta.append({
            "name": bundle_name,
            "path": rel,
            "resource_type": "Bundle",
            "count": len(resources),
        })

    # The OneAquaHealth IG's own example resources, co-hosted unmodified next to ours (D38). Counted
    # separately so resource_counts stays a count of PharmaShed's own output.
    oah_counts = _add_oah_examples(out_dir, bundles_meta)

    # Categorised Observation counts for query_demo
    lab_count = sum(
        1 for o in ref_obs
        if any(c.get("code") == "laboratory"
               for cat in o.get("category", [])
               for c in cat.get("coding", []))
    )
    pred_count = len(prediction_obs)
    resource_counts["Observation:laboratory"] = lab_count
    resource_counts["Observation:model-prediction"] = pred_count

    index = _build_fhir_index(bundles_meta, resource_counts, oah_counts)
    (out_dir / "fhir_index.json").write_text(json.dumps(index, indent=2, default=str))
    return index
