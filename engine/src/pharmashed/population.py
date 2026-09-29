"""GHS-POP population-in-buffer computation (M05).

Computes P[s] = sum of GHS-POP 100 m grid cells whose centres fall within
``radius_m`` metres of each site point.

The GHS-POP raster uses Mollweide projection (ESRI:54009). Buffering is done
in that metric CRS so distances are in metres, not degrees.

Typical usage::

    from pharmashed.population import population_in_buffer
    from pharmashed.sites import load_sites

    sites = load_sites()
    for site in sites:
        pop = population_in_buffer(site, raster_paths=[Path("data/raw/GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0.tif")])
        print(site.id, pop)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
import rasterio.mask
from rasterio.windows import Window
from pyproj import Transformer
from shapely.geometry import Point, mapping
from shapely.ops import transform as shapely_transform

from pharmashed.contracts import Site

log = logging.getLogger(__name__)

# GHS-POP Mollweide CRS
_GHS_CRS = "ESRI:54009"
_WGS84 = "EPSG:4326"

# Transformer: WGS84 → Mollweide (always-xy convention)
_to_mollweide = Transformer.from_crs(_WGS84, _GHS_CRS, always_xy=True)


def _site_buffer_mollweide(site: Site, radius_m: float):
    """Return a Shapely geometry: the site point buffered in Mollweide CRS."""
    lon, lat = site.lonlat
    mx, my = _to_mollweide.transform(lon, lat)
    return Point(mx, my).buffer(radius_m)


def population_in_buffer(
    site: Site,
    raster_paths: list[Path],
    radius_m: float = 500.0,
) -> float:
    """Sum GHS-POP cell values within ``radius_m`` metres of ``site``.

    Args:
        site: a Site object with a ``lonlat`` attribute.
        raster_paths: one or more GHS-POP GeoTIFF paths (merged on the fly
            when multiple tiles are needed).
        radius_m: buffer radius in metres (default 500, per D14).

    Returns:
        Population estimate (float ≥ 0). Returns 0.0 if the buffer falls
        entirely outside the rasters or contains only nodata.

    Raises:
        FileNotFoundError: if any raster_path does not exist.
    """
    for p in raster_paths:
        if not Path(p).exists():
            raise FileNotFoundError(f"GHS-POP raster not found: {p}")

    buf = _site_buffer_mollweide(site, radius_m)
    minx, miny, maxx, maxy = buf.bounds

    # A 500 m circle almost always sits inside one 1,000 km tile, and only occasionally straddles
    # two. So read just the tiles the circle touches (windowed by rasterio.mask) and add the pieces:
    # tiles never overlap, so no cell is counted twice. Stitching every tile into one in-memory
    # mosaic per site (as this once did) needs gigabytes and minutes for 105 sites.
    total = 0.0
    for path in raster_paths:
        with rasterio.open(path) as src:
            left, bottom, right, top = src.bounds
            if maxx < left or minx > right or maxy < bottom or miny > top:
                continue
            nodata = src.nodata if src.nodata is not None else -1
            try:
                masked, _ = rasterio.mask.mask(
                    src,
                    shapes=[mapping(buf)],
                    crop=True,
                    all_touched=False,
                    filled=True,
                    nodata=nodata,
                )
            except ValueError:
                # buffer's bounding box overlaps the tile but no cell centre falls inside it
                continue
            data = masked[0].astype(np.float64)
            data[data == nodata] = 0.0
            data[data < 0] = 0.0
            total += float(data.sum())
    return total


def density_at(lon: float, lat: float, raster_paths: list[Path] | None = None) -> float:
    """Return GHS-POP cell value at the given WGS84 point (used by auto_place_sites).

    Returns 0.0 if raster_paths is None or empty (M05 not yet run).
    """
    if not raster_paths:
        return 0.0

    mx, my = _to_mollweide.transform(lon, lat)
    pt = Point(mx, my)

    for p in raster_paths:
        if not Path(p).exists():
            continue
        with rasterio.open(p) as src:
            try:
                row, col = src.index(mx, my)
                val = src.read(1, window=Window(col, row, 1, 1))[0, 0]
                nodata = src.nodata if src.nodata is not None else -1
                return max(0.0, float(val)) if val != nodata else 0.0
            except Exception:
                continue
    return 0.0
