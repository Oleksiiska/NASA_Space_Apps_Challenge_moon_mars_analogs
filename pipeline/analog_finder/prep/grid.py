"""Global Earth grid of land cells.

The grid is a regular latitude/longitude raster. Row 0 is the northernmost row,
column 0 starts at 180 W. A cell is kept when at least ``min_land_frac`` of it
is land according to the Natural Earth 1:50m land polygons.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CELL_DEG = 0.5
MIN_LAND_FRAC = 0.2


@dataclass
class Grid:
    cell_deg: float
    land_frac: np.ndarray      # (n_lat, n_lon) fraction of land in each cell
    ice_frac: np.ndarray       # (n_lat, n_lon) fraction covered by glaciers and ice sheets
    index: np.ndarray          # flat indices (row * n_lon + col) of the kept cells, uint32

    @property
    def shape(self) -> tuple[int, int]:
        return self.land_frac.shape

    @property
    def rows(self) -> np.ndarray:
        return self.index // self.shape[1]

    @property
    def cols(self) -> np.ndarray:
        return self.index % self.shape[1]

    @property
    def lat(self) -> np.ndarray:
        return row_lat(self.rows, self.cell_deg)

    @property
    def lon(self) -> np.ndarray:
        return col_lon(self.cols, self.cell_deg)


def grid_shape(cell_deg: float = CELL_DEG) -> tuple[int, int]:
    return int(round(180.0 / cell_deg)), int(round(360.0 / cell_deg))


def row_lat(row, cell_deg: float = CELL_DEG):
    """Latitude of the cell centre for a row index."""
    return 90.0 - cell_deg / 2.0 - np.asarray(row) * cell_deg


def col_lon(col, cell_deg: float = CELL_DEG):
    """Longitude of the cell centre for a column index (-180..180)."""
    return -180.0 + cell_deg / 2.0 + np.asarray(col) * cell_deg


def cell_of(lat: float, lon: float, cell_deg: float = CELL_DEG) -> tuple[int, int]:
    """(row, col) of the cell that contains a point."""
    n_lat, n_lon = grid_shape(cell_deg)
    row = min(max(int((90.0 - lat) // cell_deg), 0), n_lat - 1)
    col = int(((lon + 180.0) % 360.0) // cell_deg) % n_lon
    return row, col


def polygon_fraction(geojson_path: str | Path, cell_deg: float = CELL_DEG, sub: int = 4) -> np.ndarray:
    """Fraction of each cell covered by the polygons of a GeoJSON file.

    Each cell is sampled at ``sub`` x ``sub`` regularly spaced points.
    Needs shapely 2.x.
    """
    import shapely
    from shapely.geometry import shape

    with open(geojson_path, "r", encoding="utf-8") as f:
        fc = json.load(f)
    geoms = [shape(ft["geometry"]) for ft in fc["features"] if ft.get("geometry")]
    geoms = [g if g.is_valid else g.buffer(0) for g in geoms]
    tree = shapely.STRtree(geoms)

    n_lat, n_lon = grid_shape(cell_deg)
    step = cell_deg / sub
    xs = -180.0 + step / 2.0 + np.arange(n_lon * sub) * step
    ys = 90.0 - step / 2.0 - np.arange(n_lat * sub) * step
    inside = np.zeros((n_lat * sub, n_lon * sub), dtype=bool)
    chunk = 64  # sample rows per chunk: keeps memory low
    for r0 in range(0, ys.size, chunk):
        yy, xx = np.meshgrid(ys[r0: r0 + chunk], xs, indexing="ij")
        pts = shapely.points(xx.ravel(), yy.ravel())
        hit = tree.query(pts, predicate="intersects")[0]
        flat = np.zeros(pts.size, dtype=bool)
        flat[np.unique(hit)] = True
        inside[r0: r0 + yy.shape[0]] = flat.reshape(yy.shape)
    return inside.reshape(n_lat, sub, n_lon, sub).mean(axis=(1, 3)).astype(np.float32)


def build(land_geojson: str | Path, ice_geojson: str | Path | None = None,
          cell_deg: float = CELL_DEG, min_land_frac: float = MIN_LAND_FRAC, sub: int = 4) -> Grid:
    land = polygon_fraction(land_geojson, cell_deg, sub)
    ice = polygon_fraction(ice_geojson, cell_deg, sub) if ice_geojson else np.zeros_like(land)
    ice = np.minimum(ice, land)
    index = np.flatnonzero(land.ravel() >= min_land_frac).astype(np.uint32)
    return Grid(cell_deg=cell_deg, land_frac=land, ice_frac=ice, index=index)
