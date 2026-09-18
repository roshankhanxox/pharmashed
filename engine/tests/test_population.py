"""M05 acceptance tests for population_in_buffer."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.crs import CRS

from pharmashed.contracts import Site
from pharmashed.population import _to_mollweide, population_in_buffer

# A real Toulouse site (TLS-07) placed in the Garonne area.
# We build a synthetic 3×3 100 m Mollweide raster centred on the same point
# and verify that population_in_buffer sums exactly the expected cells.

_TLS_LON, _TLS_LAT = 1.432, 43.608
_TLS_MX, _TLS_MY = _to_mollweide.transform(_TLS_LON, _TLS_LAT)

_CELL = 100.0       # 100 m GHS-POP resolution
_RADIUS = 120.0     # 120 m → should capture the 3 centre cells (at distance ~0, 100 m)


def _make_site(lon: float = _TLS_LON, lat: float = _TLS_LAT) -> Site:
    return Site(
        id="TLS-07", city="TLS", name="test",
        lonlat=(lon, lat),
        synthetic=True, size_class="L",
        w=0, valid=True,
        population_buffer=0, population_source_key="pop:test",
    )


def _write_raster(path: Path, data: np.ndarray, origin_x: float, origin_y: float) -> None:
    """Write a single-band Mollweide GeoTIFF at 100 m resolution."""
    rows, cols = data.shape
    transform = Affine.translation(origin_x, origin_y) * Affine.scale(_CELL, -_CELL)
    with rasterio.open(
        path, "w",
        driver="GTiff", height=rows, width=cols, count=1,
        dtype=data.dtype, crs=CRS.from_user_input("ESRI:54009"),
        transform=transform, nodata=-1,
    ) as dst:
        dst.write(data.astype(np.float32), 1)


# ---------------------------------------------------------------------------
# Core unit test: synthetic 3×3 raster
# ---------------------------------------------------------------------------


def test_population_3x3_exact(tmp_path: Path) -> None:
    """Buffer of 120 m around centre of a 3×3 100 m raster: captures ≥ 1 cell."""
    # Place origin so the site lands exactly at the centre of the 3×3 grid
    origin_x = _TLS_MX - 1.5 * _CELL   # left edge of 3×3
    origin_y = _TLS_MY + 1.5 * _CELL   # top edge (y decreases south)

    data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float32)
    raster = tmp_path / "ghspop.tif"
    _write_raster(raster, data, origin_x, origin_y)

    site = _make_site()
    pop = population_in_buffer(site, [raster], radius_m=_RADIUS)
    # The centre cell (row=1, col=1) has value 5. At radius 120 m the four
    # directly adjacent cells (values 2,4,6,8) are also ~100 m away; corner
    # cells are ~141 m away. Expected sum = 5 + 2 + 4 + 6 + 8 = 25
    assert pop == pytest.approx(25.0), f"Expected 25, got {pop}"


def test_population_large_radius_sums_all(tmp_path: Path) -> None:
    """Radius large enough to capture every cell sums entire raster."""
    origin_x = _TLS_MX - 1.5 * _CELL
    origin_y = _TLS_MY + 1.5 * _CELL
    data = np.ones((3, 3), dtype=np.float32) * 10
    raster = tmp_path / "ghspop.tif"
    _write_raster(raster, data, origin_x, origin_y)

    site = _make_site()
    pop = population_in_buffer(site, [raster], radius_m=300.0)
    assert pop == pytest.approx(90.0)


def test_population_nodata_excluded(tmp_path: Path) -> None:
    """Nodata cells (-1) must not contribute to the sum."""
    origin_x = _TLS_MX - 1.5 * _CELL
    origin_y = _TLS_MY + 1.5 * _CELL
    data = np.full((3, 3), -1.0, dtype=np.float32)
    data[1, 1] = 100.0  # only centre cell has real data
    raster = tmp_path / "ghspop.tif"
    _write_raster(raster, data, origin_x, origin_y)

    site = _make_site()
    pop = population_in_buffer(site, [raster], radius_m=_RADIUS)
    assert pop == pytest.approx(100.0)


def test_population_outside_raster_returns_zero(tmp_path: Path) -> None:
    """Site far from the raster extent should return 0, not raise."""
    # Place raster at Ghent (~lon 3.72) while site is at Toulouse (lon 1.43)
    gnt_mx, gnt_my = _to_mollweide.transform(3.72, 51.05)
    origin_x = gnt_mx - 150.0
    origin_y = gnt_my + 150.0
    data = np.ones((3, 3), dtype=np.float32)
    raster = tmp_path / "ghspop.tif"
    _write_raster(raster, data, origin_x, origin_y)

    site = _make_site()  # TLS site, far from GNT raster
    pop = population_in_buffer(site, [raster], radius_m=500.0)
    assert pop == 0.0


def test_population_missing_raster_raises(tmp_path: Path) -> None:
    site = _make_site()
    with pytest.raises(FileNotFoundError):
        population_in_buffer(site, [tmp_path / "nonexistent.tif"])


def test_population_returns_float(tmp_path: Path) -> None:
    origin_x = _TLS_MX - 1.5 * _CELL
    origin_y = _TLS_MY + 1.5 * _CELL
    data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float32)
    raster = tmp_path / "ghspop.tif"
    _write_raster(raster, data, origin_x, origin_y)
    site = _make_site()
    result = population_in_buffer(site, [raster], radius_m=_RADIUS)
    assert isinstance(result, float)


def test_population_non_negative(tmp_path: Path) -> None:
    """No negative values should appear even with nodata=-1 adjacent to real cells."""
    origin_x = _TLS_MX - 1.5 * _CELL
    origin_y = _TLS_MY + 1.5 * _CELL
    data = np.array([[-1, -1, -1], [-1, 50, -1], [-1, -1, -1]], dtype=np.float32)
    raster = tmp_path / "ghspop.tif"
    _write_raster(raster, data, origin_x, origin_y)
    site = _make_site()
    pop = population_in_buffer(site, [raster], radius_m=_RADIUS)
    assert pop >= 0.0
