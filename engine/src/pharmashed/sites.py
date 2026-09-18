"""Site registry loader (M04).

Loads ``data/sites/sites.geojson`` and returns typed Site and City objects.
The GeoJSON is the authoritative file; ``contracts/fixtures/sites.json`` is
the fixture used by contract tests and web development.
"""

from __future__ import annotations

import json
from pathlib import Path

from pharmashed.contracts import City, Site

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SITES = _REPO_ROOT / "data" / "sites" / "sites.geojson"

# Static city definitions (D02) — source of truth for IDs and display names
_CITIES: list[City] = [
    City(id="TLS", name="Toulouse",   country="FR", center=(1.4442,  43.6047), zoom=12),
    City(id="GNT", name="Ghent",      country="BE", center=(3.7174,  51.0543), zoom=12),
    City(id="BNV", name="Benevento",  country="IT", center=(14.7839, 41.1290), zoom=13),
    City(id="CBR", name="Coimbra",    country="PT", center=(-8.4191, 40.2033), zoom=13),
    City(id="OSL", name="Oslo",       country="NO", center=(10.7522, 59.9139), zoom=12),
]

# Approximate bboxes [lon_min, lat_min, lon_max, lat_max] used for validation
_CITY_BBOX: dict[str, tuple[float, float, float, float]] = {
    "TLS": (1.30,  43.54, 1.56,  43.68),
    "GNT": (3.64,  51.00, 3.81,  51.12),
    "BNV": (14.72, 41.09, 14.86, 41.18),
    "CBR": (-8.51, 40.17, -8.34, 40.25),
    "OSL": (10.58, 59.87, 10.89, 59.99),
}

_VALID_CITY_IDS = {c.id for c in _CITIES}
_VALID_SIZE_CLASSES = {"S", "M", "L"}


def cities() -> list[City]:
    """Return the five static city definitions (D02)."""
    return list(_CITIES)


def load_sites(path: Path | None = None) -> list[Site]:
    """Load and validate sites from a GeoJSON FeatureCollection.

    Args:
        path: path to sites.geojson; defaults to ``data/sites/sites.geojson``.

    Returns:
        List of validated Site objects (valid=True sites only by convention;
        all sites are returned so callers can filter themselves).

    Raises:
        ValueError: if any site fails validation.
    """
    src = path or _DEFAULT_SITES
    raw = json.loads(Path(src).read_text())

    if raw.get("type") != "FeatureCollection":
        raise ValueError(f"{src}: expected a GeoJSON FeatureCollection, got {raw.get('type')!r}")

    sites: list[Site] = []
    seen_ids: set[str] = set()

    for feat in raw["features"]:
        p = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"][:2]

        site_id: str = p["id"]
        city_id: str = p["city"]

        # --- id uniqueness ---
        if site_id in seen_ids:
            raise ValueError(f"Duplicate site id: {site_id!r}")
        seen_ids.add(site_id)

        # --- id prefix matches city ---
        if not site_id.startswith(city_id + "-"):
            raise ValueError(f"Site {site_id!r}: id prefix does not match city {city_id!r}")

        # --- known city ---
        if city_id not in _VALID_CITY_IDS:
            raise ValueError(f"Site {site_id!r}: unknown city {city_id!r}")

        # --- point inside city bbox ---
        lon_min, lat_min, lon_max, lat_max = _CITY_BBOX[city_id]
        if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
            raise ValueError(
                f"Site {site_id!r}: ({lon}, {lat}) outside bbox for {city_id}"
            )

        # --- size_class ---
        if p["size_class"] not in _VALID_SIZE_CLASSES:
            raise ValueError(f"Site {site_id!r}: invalid size_class {p['size_class']!r}")

        sites.append(
            Site(
                id=site_id,
                city=city_id,
                name=p["name"],
                lonlat=(lon, lat),
                synthetic=True,
                size_class=p["size_class"],
                w=p["w"],
                valid=p["valid"],
                population_buffer=p["population_buffer"],
                population_source_key=p["population_source_key"],
            )
        )

    return sites
