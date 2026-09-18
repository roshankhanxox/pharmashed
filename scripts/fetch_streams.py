"""Fetch urban waterway geometries via the Overpass API (M04).

Queries OSM for stream, ditch, canal, and river features within each city
bbox and writes ``data/sites/streams.geojson`` (< 3 MB, simplified to
0.0001-degree tolerance, with ODbL attribution in feature properties).

Usage::

    uv run python scripts/fetch_streams.py [--out data/sites/streams.geojson]

Requires: requests, shapely
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import requests
from shapely.geometry import LineString, mapping, shape
from shapely.ops import unary_union

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SIMPLIFY_TOLERANCE = 0.0001  # degrees (~10 m at mid-latitudes)
ATTRIBUTION = "© OpenStreetMap contributors, ODbL"

# City bboxes: (south, west, north, east) — Overpass convention
CITIES = {
    "TLS": {"name": "Toulouse",  "bbox": (43.54, 1.30,  43.68, 1.56)},
    "GNT": {"name": "Ghent",     "bbox": (51.00, 3.64,  51.12, 3.81)},
    "BNV": {"name": "Benevento", "bbox": (41.09, 14.72, 41.18, 14.86)},
    "CBR": {"name": "Coimbra",   "bbox": (40.17, -8.51, 40.25, -8.34)},
    "OSL": {"name": "Oslo",      "bbox": (59.87, 10.58, 59.99, 10.89)},
}

WATERWAY_TYPES = ["stream", "ditch", "canal", "river"]


def _overpass_query(city_id: str, bbox: tuple[float, float, float, float]) -> list[dict]:
    s, w, n, e = bbox
    bbox_str = f"{s},{w},{n},{e}"
    type_filter = "|".join(WATERWAY_TYPES)
    query = f"""
[out:json][timeout:60];
(
  way["waterway"~"{type_filter}"][!"tunnel"]({bbox_str});
  way["waterway"~"{type_filter}"]["tunnel"!="culvert"]({bbox_str});
);
out geom;
""".strip()

    log.info("Querying Overpass for %s (%s)…", city_id, bbox_str)
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
    resp.raise_for_status()
    elements = resp.json().get("elements", [])
    log.info("  %d ways returned", len(elements))
    return elements


def _element_to_feature(el: dict, city_id: str) -> dict | None:
    """Convert an Overpass way element to a simplified GeoJSON feature."""
    geom_nodes = el.get("geometry", [])
    if len(geom_nodes) < 2:
        return None

    coords = [(n["lon"], n["lat"]) for n in geom_nodes]
    try:
        line = LineString(coords).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    except Exception:
        return None

    if line.is_empty or line.length == 0:
        return None

    tags = el.get("tags", {})
    return {
        "type": "Feature",
        "geometry": mapping(line),
        "properties": {
            "osm_id": el.get("id"),
            "waterway": tags.get("waterway", ""),
            "name": tags.get("name", ""),
            "width": tags.get("width", ""),
            "city": city_id,
            "attribution": ATTRIBUTION,
        },
    }


def fetch_streams(out_path: Path) -> None:
    features: list[dict] = []

    for city_id, meta in CITIES.items():
        try:
            elements = _overpass_query(city_id, meta["bbox"])
        except Exception as exc:
            log.warning("Overpass failed for %s: %s — skipping", city_id, exc)
            time.sleep(5)
            continue

        for el in elements:
            feat = _element_to_feature(el, city_id)
            if feat is not None:
                features.append(feat)

        # polite rate-limiting between cities
        time.sleep(3)

    geojson = {
        "type": "FeatureCollection",
        "name": "PharmaShed stream network",
        "attribution": ATTRIBUTION,
        "features": features,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(geojson, separators=(",", ":"))
    size_mb = len(text.encode()) / 1_048_576
    log.info("Writing %d features (%.2f MB) to %s", len(features), size_mb, out_path)
    if size_mb > 3.0:
        log.warning("Output exceeds 3 MB target (%.2f MB); consider increasing SIMPLIFY_TOLERANCE", size_mb)
    out_path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/sites/streams.geojson")
    args = parser.parse_args()

    out = Path(args.out)
    fetch_streams(out)
    log.info("Done.")


if __name__ == "__main__":
    main()
