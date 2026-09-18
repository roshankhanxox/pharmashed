"""Download GHS-POP tiles covering the five PharmaShed cities (M05).

Release used: GHS-POP R2023A, epoch 2025, 100 m resolution, Mollweide
(ESRI:54009). Tiles are 1°×1° in Mollweide coordinates. Each tile is
named GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R<row>_C<col>.tif.

JRC GHSL download page (requires free registration):
  https://human-settlement.emergency.copernicus.eu/download.php?ds=pop

This script downloads the minimum set of tiles that cover the 500 m buffers
around all five cities. It will print the required tile URLs; download them
manually if automated download fails (the JRC site sometimes requires a
session token).

Usage::

    uv run python scripts/fetch_ghspop.py [--out data/raw/]

Outputs files to ``data/raw/``. Record the release in provenance.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pyproj import Transformer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

_WGS84 = "EPSG:4326"
_GHS_CRS = "ESRI:54009"
_to_mollweide = Transformer.from_crs(_WGS84, _GHS_CRS, always_xy=True)

# City centres [lon, lat] (D02)
CITIES = {
    "TLS": (1.4442,  43.6047),
    "GNT": (3.7174,  51.0543),
    "BNV": (14.7839, 41.1290),
    "CBR": (-8.4191, 40.2033),
    "OSL": (10.7522, 59.9139),
}

# GHS-POP R2023A tile grid: tiles are 1° Mollweide cells (100,000 m)
# Row/col numbering: origin at top-left of the world grid.
# Full grid: 18 rows × 36 cols at 10°-equivalent Mollweide spacing.
# Tile size: 100,000 m × 100,000 m in Mollweide
_TILE_SIZE_M = 100_000  # 100 km tiles
_GRID_ORIGIN_X = -18_040_095.696  # Mollweide west extent
_GRID_ORIGIN_Y =   9_000_000.0    # Mollweide north extent

# JRC base URL (direct tile download; may require session cookie for large files)
_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
    "GHS_POP_E2025_GLOBE_R2023A_54009_100/V1-0/"
)
_TILE_TPL = "GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R{row}_C{col}.tif"
_BUFFER_M = 5_000  # 5 km safety margin around city centre


def _tile_rowcol(mx: float, my: float) -> tuple[int, int]:
    col = int((mx - _GRID_ORIGIN_X) / _TILE_SIZE_M) + 1
    row = int((_GRID_ORIGIN_Y - my) / _TILE_SIZE_M) + 1
    return row, col


def required_tiles() -> list[tuple[int, int]]:
    """Return the set of (row, col) tile indices needed to cover all cities."""
    tiles: set[tuple[int, int]] = set()
    for city, (lon, lat) in CITIES.items():
        mx, my = _to_mollweide.transform(lon, lat)
        # check corners of the bounding box
        for dx in (-_BUFFER_M, 0, _BUFFER_M):
            for dy in (-_BUFFER_M, 0, _BUFFER_M):
                tiles.add(_tile_rowcol(mx + dx, my + dy))
    return sorted(tiles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/raw/")
    parser.add_argument(
        "--download", action="store_true",
        help="attempt automated download with requests (may fail without auth)"
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tiles = required_tiles()
    log.info("Tiles required for 5 cities (±5 km margin): %d", len(tiles))

    for row, col in tiles:
        name = _TILE_TPL.format(row=row, col=col)
        url = _BASE_URL + name
        dest = out_dir / name
        if dest.exists():
            log.info("  already exists: %s", dest)
            continue
        log.info("  %s\n    URL: %s", name, url)
        if args.download:
            try:
                import requests  # noqa: PLC0415
                r = requests.get(url, stream=True, timeout=120)
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                log.info("    → saved %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
            except Exception as exc:
                log.warning("    download failed: %s — download manually", exc)
        else:
            log.info("    Run with --download to attempt automated fetch.")

    log.info(
        "\nProvenance note: GHS-POP R2023A, epoch 2025, 100 m, ESRI:54009.\n"
        "Citation: Schiavina M., Freire S., Carioli A., MacManus K. (2023)\n"
        "GHS-POP R2023A — GHS population grid multitemporal (1975-2030).\n"
        "European Commission, Joint Research Centre (JRC). doi:10.2905/D6D86A90"
    )


if __name__ == "__main__":
    main()
