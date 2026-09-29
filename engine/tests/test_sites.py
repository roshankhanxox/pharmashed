"""M04 acceptance tests for the sites registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharmashed.contracts import City, Site
from pharmashed.sites import cities, load_sites

REPO_ROOT = Path(__file__).resolve().parents[2]
SITES_GEOJSON = REPO_ROOT / "data" / "sites" / "sites.geojson"
EXPECTED_CITIES = {"TLS", "GNT", "BNV", "CBR", "OSL"}


# ---------------------------------------------------------------------------
# cities()
# ---------------------------------------------------------------------------


def test_cities_returns_five():
    result = cities()
    assert len(result) == 5


def test_cities_ids():
    ids = {c.id for c in cities()}
    assert ids == EXPECTED_CITIES


def test_cities_types():
    for c in cities():
        assert isinstance(c, City)
        assert len(c.center) == 2
        assert 0 < c.zoom <= 22


# ---------------------------------------------------------------------------
# load_sites()
# ---------------------------------------------------------------------------


def test_sites_geojson_exists():
    assert SITES_GEOJSON.exists(), f"Missing {SITES_GEOJSON}"


def test_load_sites_count():
    sites = load_sites(SITES_GEOJSON)
    assert 100 <= len(sites) <= 110, f"Expected 100–110 sites (D41), got {len(sites)}"


def test_load_sites_types():
    sites = load_sites(SITES_GEOJSON)
    for s in sites:
        assert isinstance(s, Site)


def test_load_sites_all_cities_present():
    sites = load_sites(SITES_GEOJSON)
    city_ids = {s.city for s in sites}
    assert city_ids == EXPECTED_CITIES


def test_load_sites_per_city_count():
    sites = load_sites(SITES_GEOJSON)
    from collections import Counter
    counts = Counter(s.city for s in sites)
    for city, count in counts.items():
        assert 20 <= count <= 22, f"{city}: expected 20–22 sites (D41), got {count}"


def test_load_sites_ids_unique():
    sites = load_sites(SITES_GEOJSON)
    ids = [s.id for s in sites]
    assert len(ids) == len(set(ids))


def test_load_sites_id_pattern():
    import re
    sites = load_sites(SITES_GEOJSON)
    pattern = re.compile(r"^[A-Z]{3}-\d{2}$")
    for s in sites:
        assert pattern.match(s.id), f"Bad id: {s.id!r}"


def test_load_sites_size_class():
    sites = load_sites(SITES_GEOJSON)
    for s in sites:
        assert s.size_class in ("S", "M", "L"), f"{s.id}: bad size_class {s.size_class!r}"


def test_load_sites_w_zero():
    sites = load_sites(SITES_GEOJSON)
    for s in sites:
        assert s.w == 0, f"{s.id}: w should be 0 (no WWTP)"


def test_load_sites_all_valid():
    sites = load_sites(SITES_GEOJSON)
    for s in sites:
        assert s.valid is True, f"{s.id}: valid should be True"


def test_load_sites_population_buffer_non_negative():
    sites = load_sites(SITES_GEOJSON)
    for s in sites:
        assert s.population_buffer >= 0


def test_load_sites_synthetic_true():
    sites = load_sites(SITES_GEOJSON)
    for s in sites:
        assert s.synthetic is True


# ---------------------------------------------------------------------------
# Validation error cases
# ---------------------------------------------------------------------------


def _make_geojson(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _site_feature(
    site_id: str = "TLS-01",
    city: str = "TLS",
    lon: float = 1.432,
    lat: float = 43.608,
    size_class: str = "S",
) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "id": site_id, "city": city,
            "name": "test site",
            "synthetic": True, "size_class": size_class,
            "w": 0, "valid": True,
            "population_buffer": 0,
            "population_source_key": "pop:test",
        },
    }


def test_load_sites_raises_on_duplicate_id(tmp_path: Path):
    f = _site_feature("TLS-01")
    gj = _make_geojson([f, f])
    p = tmp_path / "sites.geojson"
    p.write_text(json.dumps(gj))
    with pytest.raises(ValueError, match="Duplicate"):
        load_sites(p)


def test_load_sites_raises_on_wrong_city_prefix(tmp_path: Path):
    f = _site_feature("GNT-01", city="TLS")
    gj = _make_geojson([f])
    p = tmp_path / "sites.geojson"
    p.write_text(json.dumps(gj))
    with pytest.raises(ValueError, match="prefix"):
        load_sites(p)


def test_load_sites_raises_on_unknown_city(tmp_path: Path):
    f = _site_feature("XYZ-01", city="XYZ")
    gj = _make_geojson([f])
    p = tmp_path / "sites.geojson"
    p.write_text(json.dumps(gj))
    with pytest.raises(ValueError, match="unknown city"):
        load_sites(p)


def test_load_sites_raises_outside_bbox(tmp_path: Path):
    f = _site_feature("TLS-01", city="TLS", lon=10.0, lat=55.0)
    gj = _make_geojson([f])
    p = tmp_path / "sites.geojson"
    p.write_text(json.dumps(gj))
    with pytest.raises(ValueError, match="bbox"):
        load_sites(p)


def test_load_sites_raises_bad_size_class(tmp_path: Path):
    f = _site_feature("TLS-01", size_class="X")
    gj = _make_geojson([f])
    p = tmp_path / "sites.geojson"
    p.write_text(json.dumps(gj))
    with pytest.raises(ValueError, match="size_class"):
        load_sites(p)


def test_load_sites_raises_not_feature_collection(tmp_path: Path):
    p = tmp_path / "sites.geojson"
    p.write_text(json.dumps({"type": "Feature"}))
    with pytest.raises(ValueError, match="FeatureCollection"):
        load_sites(p)
