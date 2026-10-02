"""Geometry for citizen reports: which model site and which city a pin belongs to."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping

EARTH_RADIUS_M = 6_371_000.0
SITE_LINK_RADIUS_M = 1_000      # a pin within 1 km of a model site is linked to it
CITY_RADIUS_M = 30_000          # a pin within 30 km of a city centre belongs to that city


@dataclass(frozen=True)
class Placement:
    """Where a pin falls in the project's coverage."""

    site_id: str | None
    city: str | None
    distance_m: int | None  # distance to site_id, when linked


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def place_pin(
    lat: float,
    lon: float,
    sites: Iterable[Mapping],
    cities: Iterable[Mapping],
) -> Placement:
    """Link a pin to the nearest site within 1 km, and to a city (the site's, else the nearest within 30 km).

    `sites` entries have `id`, `city` and `lonlat` ([lon, lat]); `cities` entries have `id` and `center` ([lon, lat]).
    """
    best_site: Mapping | None = None
    best_d = float("inf")
    for site in sites:
        s_lon, s_lat = site["lonlat"]
        d = haversine_m(lat, lon, s_lat, s_lon)
        if d < best_d:
            best_site, best_d = site, d

    if best_site is not None and best_d <= SITE_LINK_RADIUS_M:
        return Placement(site_id=best_site["id"], city=best_site["city"], distance_m=round(best_d))

    nearest_city: str | None = None
    nearest_d = float("inf")
    for city in cities:
        c_lon, c_lat = city["center"]
        d = haversine_m(lat, lon, c_lat, c_lon)
        if d < nearest_d:
            nearest_city, nearest_d = city["id"], d
    return Placement(site_id=None, city=nearest_city if nearest_d <= CITY_RADIUS_M else None, distance_m=None)
