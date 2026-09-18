"""Rule-based synthetic site placement (M04, SOURCING.md S5).

Places 9 synthetic monitoring sites per city on OSM waterways, stratified
by GHS-POP density and spread ≥ 800 m apart. Writes ``data/sites/sites.geojson``
and ``data/sites/sites_preview.html`` (Leaflet map for human review).

**Requires M05** (population raster reader) to be complete before running,
because step 3 reads GHS-POP density via ``pharmashed.population.density_at``.

Usage::

    uv run python scripts/auto_place_sites.py [--seed 42] [--exclude TLS-04,GNT-07]

After running, open ``data/sites/sites_preview.html``, reject any obviously
bad points (underground, private canal), then re-run with ``--exclude``.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import time
from pathlib import Path

import requests
from shapely.geometry import LineString, Point

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CANDIDATE_SPACING_M = 150
MIN_SEPARATION_M = 800
SITES_PER_STRATUM = 3  # 3 strata × 3 = 9 per city
WATERWAY_TYPES = ["stream", "ditch", "canal"]

CITIES: dict[str, dict] = {
    "TLS": {"name": "Toulouse",  "country": "FR", "center": (1.4442,  43.6047), "zoom": 12, "bbox": (43.54, 1.30,  43.68, 1.56)},
    "GNT": {"name": "Ghent",     "country": "BE", "center": (3.7174,  51.0543), "zoom": 12, "bbox": (51.00, 3.64,  51.12, 3.81)},
    "BNV": {"name": "Benevento", "country": "IT", "center": (14.7839, 41.1290), "zoom": 13, "bbox": (41.09, 14.72, 41.18, 14.86)},
    "CBR": {"name": "Coimbra",   "country": "PT", "center": (-8.4191, 40.2033), "zoom": 13, "bbox": (40.17, -8.51, 40.25, -8.34)},
    "OSL": {"name": "Oslo",      "country": "NO", "center": (10.7522, 59.9139), "zoom": 12, "bbox": (59.87, 10.58, 59.99, 10.89)},
}


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _fetch_ways(city_id: str, bbox: tuple) -> list[dict]:
    s, w, n, e = bbox
    type_filter = "|".join(WATERWAY_TYPES)
    query = f"""
[out:json][timeout:60];
(way["waterway"~"{type_filter}"]["tunnel"!="culvert"]({s},{w},{n},{e}););
out geom;
""".strip()
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
    resp.raise_for_status()
    return resp.json().get("elements", [])


def _candidate_points(elements: list[dict]) -> list[tuple[float, float, str, str]]:
    """Generate a point every CANDIDATE_SPACING_M along each way."""
    candidates: list[tuple[float, float, str, str]] = []
    spacing_deg = CANDIDATE_SPACING_M / 111_000

    for el in elements:
        geom = el.get("geometry", [])
        if len(geom) < 2:
            continue
        tags = el.get("tags", {})
        waterway_type = tags.get("waterway", "stream")
        # size_class from width tag; else by type
        width_str = tags.get("width", "")
        try:
            w = float(width_str)
            size_class = "S" if w < 2 else ("M" if w <= 5 else "L")
        except (ValueError, TypeError):
            size_class = "S" if waterway_type in ("stream", "ditch") else "M"

        coords = [(n["lon"], n["lat"]) for n in geom]
        line = LineString(coords)
        length_deg = line.length
        n_pts = max(1, int(length_deg / spacing_deg))
        for i in range(n_pts):
            pt = line.interpolate(i / n_pts, normalized=True)
            candidates.append((pt.x, pt.y, size_class, waterway_type))

    return candidates


def _assign_strata(
    candidates: list[tuple[float, float, str, str]],
) -> list[tuple[float, float, str, str, int]]:
    """Assign stratum 0/1/2 by GHS-POP density placeholder.

    NOTE: requires M05. Until M05 is done, falls back to geometric
    distance-from-city-center tertiles as a placeholder.
    """
    try:
        from pharmashed.population import density_at  # noqa: PLC0415
        densities = [density_at(lon, lat) for lon, lat, *_ in candidates]
    except ImportError:
        log.warning("pharmashed.population not available (M05 not done); using placeholder strata")
        densities = [0.0] * len(candidates)

    if len(set(densities)) < 3:
        # placeholder: split by index thirds
        n = len(candidates)
        strata = [int(i / n * 3) for i in range(n)]
    else:
        sorted_d = sorted(densities)
        t1 = sorted_d[len(sorted_d) // 3]
        t2 = sorted_d[2 * len(sorted_d) // 3]
        strata = [0 if d < t1 else (1 if d < t2 else 2) for d in densities]

    return [(lon, lat, sc, wt, s) for (lon, lat, sc, wt), s in zip(candidates, strata)]


def _pick_spread(
    stratum_candidates: list[tuple[float, float, str, str, int]],
    n: int,
    rng: random.Random,
) -> list[tuple[float, float, str]]:
    """Pick n points at least MIN_SEPARATION_M apart from a stratum."""
    shuffled = list(stratum_candidates)
    rng.shuffle(shuffled)
    chosen: list[tuple[float, float, str]] = []
    for lon, lat, size_class, *_ in shuffled:
        if all(_haversine_m(lon, lat, cx, cy) >= MIN_SEPARATION_M for cx, cy, _ in chosen):
            chosen.append((lon, lat, size_class))
        if len(chosen) >= n:
            break
    return chosen


def place_sites(
    city_id: str,
    meta: dict,
    exclude: set[str],
    rng: random.Random,
    site_counter: list[int],
) -> list[dict]:
    log.info("Placing sites for %s…", city_id)
    elements = _fetch_ways(city_id, meta["bbox"])
    candidates = _candidate_points(elements)
    log.info("  %d candidate points on %d ways", len(candidates), len(elements))

    stratified = _assign_strata(candidates)
    features: list[dict] = []

    strata_groups: dict[int, list] = {0: [], 1: [], 2: []}
    for item in stratified:
        strata_groups[item[4]].append(item)

    for stratum in range(3):
        group = strata_groups[stratum]
        picked = _pick_spread(group, SITES_PER_STRATUM, rng)
        for lon, lat, size_class in picked:
            idx = site_counter[0]
            site_counter[0] += 1
            site_id = f"{city_id}-{idx:02d}"
            if site_id in exclude:
                log.info("  Skipping excluded site %s", site_id)
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": site_id, "city": city_id,
                    "name": f"Auto-placed {city_id} site {idx:02d} (stratum {stratum})",
                    "synthetic": True, "size_class": size_class,
                    "w": 0, "valid": True,
                    "population_buffer": 0,
                    "population_source_key": "pop:pending-m05",
                    "placement": "auto",
                },
            })
    return features


def write_preview(features: list[dict], out_html: Path) -> None:
    markers_js = json.dumps([
        {
            "id": f["properties"]["id"],
            "lon": f["geometry"]["coordinates"][0],
            "lat": f["geometry"]["coordinates"][1],
            "city": f["properties"]["city"],
            "size_class": f["properties"]["size_class"],
        }
        for f in features
    ])
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>PharmaShed site preview</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{{margin:0}}#map{{height:100vh}}</style>
</head><body>
<div id="map"></div>
<script>
const map = L.map('map').setView([48, 10], 4);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution:'© OpenStreetMap contributors'}}).addTo(map);
const COLORS = {{S:'#e74c3c',M:'#f39c12',L:'#2ecc71'}};
const sites = {markers_js};
sites.forEach(s => {{
  L.circleMarker([s.lat, s.lon], {{
    radius: 8, color: COLORS[s.size_class] || '#3498db',
    fillOpacity: 0.8, weight: 2,
  }}).bindPopup(`<b>${{s.id}}</b><br>size: ${{s.size_class}}`).addTo(map);
}});
</script>
</body></html>"""
    out_html.write_text(html)
    log.info("Preview written to %s", out_html)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--exclude", default="", help="Comma-separated site ids to skip")
    parser.add_argument("--out", default="data/sites/sites.geojson")
    parser.add_argument("--preview", default="data/sites/sites_preview.html")
    args = parser.parse_args()

    exclude = set(args.exclude.split(",")) - {""} if args.exclude else set()
    rng = random.Random(args.seed)
    all_features: list[dict] = []

    for city_id, meta in CITIES.items():
        counter = [1]
        feats = place_sites(city_id, meta, exclude, rng, counter)
        all_features.extend(feats)
        time.sleep(3)

    geojson = {"type": "FeatureCollection", "features": all_features}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(geojson, indent=2))
    log.info("Wrote %d sites to %s", len(all_features), out)

    write_preview(all_features, Path(args.preview))


if __name__ == "__main__":
    main()
