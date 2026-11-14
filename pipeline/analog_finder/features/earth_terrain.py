"""Terrain features of Earth land cells from SRTMGL30, same metrics as the Moon and Mars.

Each 0.5 degree cell is 60 x 60 pixels of 30 arc seconds (about 926 m). Slopes,
roughness and relief are computed with the functions of features/terrain.py,
so a cell and a Moon or Mars target are compared on the same ground step.

The tiles cover 90 N to 60 S (checked on the downloaded files: every land cell north of 60 N has values,
none south of 60 S). Real SRTM data end at 60 N and 56 S; the rest of the product is filled from other
sources (GTOPO30 north of 60 N, to be confirmed on the product page), so polar values are coarser.
Cells south of 60 S (Antarctica) get no terrain features.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..io import srtm
from ..prep import layers
from . import terrain

EARTH_RADIUS_M = 6371000.0
MIN_VALID = 0.2           # a cell needs this share of pixels with a valid slope

N_BINS = len(terrain.SLOPE_EDGES) - 1
_HIST = [f"slope_h{k}" for k in range(N_BINS)]
SPEC = {                  # name: (min, max, unit, description)
    "elev_mean_m": (-500.0, 6500.0, "m", "Mean elevation of the cell above the geoid"),
    "relief_m": (0.0, 6000.0, "m", "Elevation range P95-P5 inside the cell"),
    "slope_mean_deg": (0.0, 40.0, "deg", "Mean slope at a ~926 m step (Horn)"),
    "slope_lt8": (0.0, 1.0, "fraction", "Share of the cell with slope under 8 deg (landing limit)"),
    "slope_lt15": (0.0, 1.0, "fraction", "Share of the cell with slope under 15 deg (rover limit)"),
    "rough_p50_m": (0.0, 500.0, "m", "Median RMS deviation of elevation in 3 x 3 pixel windows"),
    **{h: (0.0, 1.0, "fraction", f"Share of the cell in slope class {k} ({terrain.SLOPE_EDGES[k]:g}-{terrain.SLOPE_EDGES[k + 1]:g} deg)")
       for k, h in enumerate(_HIST)},
}
SOURCE = "NASA SRTMGL30 (EOSDIS LP DAAC), computed by features/earth_terrain.py"


def _cells(a: np.ndarray, n: int, nc: int) -> np.ndarray:
    """(n, nc * n) strip -> (nc, n * n): one row of pixels per cell."""
    return a.reshape(n, nc, n).transpose(1, 0, 2).reshape(nc, n * n)


def tile_cell_features(z: np.ndarray, ul_lat: float, cell_deg: float = 0.5,
                       min_valid: float = MIN_VALID) -> dict[str, np.ndarray]:
    """Features of every cell of one tile. Returns name -> (rows // n, cols // n) arrays (NaN = no data)."""
    n = int(round(cell_deg / srtm.PIXEL_DEG))
    rows, cols = z.shape
    nr, nc = rows // n, cols // n
    out = {k: np.full((nr, nc), np.nan, dtype=np.float32) for k in SPEC}
    dy = EARTH_RADIUS_M * np.radians(srtm.PIXEL_DEG)
    edges = np.asarray(terrain.SLOPE_EDGES[1:-1])
    for i in range(nr):
        r0, r1 = i * n, (i + 1) * n
        a, b = max(r0 - 1, 0), min(r1 + 1, rows)          # one extra row each side for the 3 x 3 windows
        band = z[a:b]
        if np.isnan(band[r0 - a: r0 - a + n]).all():
            continue
        lat = ul_lat - (np.arange(a, b) + 0.5) * srtm.PIXEL_DEG
        dx = dy * np.cos(np.radians(lat))
        s = terrain.slope_deg(band, dx, dy)[r0 - a: r0 - a + n, : nc * n]
        rg = terrain.roughness_rms(band)[r0 - a: r0 - a + n, : nc * n]
        zz = band[r0 - a: r0 - a + n, : nc * n]
        s, rg, zz = _cells(s, n, nc), _cells(rg, n, nc), _cells(zz, n, nc)
        valid = np.isfinite(s)
        cnt = valid.sum(axis=1)
        ok = cnt >= min_valid * n * n
        if not ok.any():
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            out["elev_mean_m"][i] = np.nanmean(zz, axis=1)
            p5, p95 = np.nanpercentile(zz, [5, 95], axis=1)
            out["relief_m"][i] = p95 - p5
            out["slope_mean_deg"][i] = np.nanmean(s, axis=1)
            out["rough_p50_m"][i] = np.nanmedian(rg, axis=1)
            with np.errstate(invalid="ignore"):
                out["slope_lt8"][i] = (np.where(valid, s, np.inf) < 8).sum(axis=1) / cnt
                out["slope_lt15"][i] = (np.where(valid, s, np.inf) < 15).sum(axis=1) / cnt
                cls = np.digitize(np.where(valid, s, 0.0), edges)
                for k, h in enumerate(_HIST):
                    out[h][i] = ((cls == k) & valid).sum(axis=1) / cnt
        for k in out:
            out[k][i, ~ok] = np.nan
    return out


def selfcheck(tiles: dict[str, "srtm.Tile"]) -> list[str]:
    """Known pixels: a flipped, shifted or mis-scaled tile fails here. Returns the problems found."""
    checks = [("Everest", 27.99, 86.93, lambda v: v > 6500), ("Dead Sea", 31.5, 35.5, lambda v: v < -300),
              ("Lake Titicaca shore", -15.9, -69.4, lambda v: 3500 < v < 4300), ("Death Valley", 36.5, -117.0, lambda v: v < 400)]
    problems = []
    for name, lat, lon, ok in checks:
        for t in tiles.values():
            h, w = t.z.shape
            if t.ul_lat - h * srtm.PIXEL_DEG <= lat < t.ul_lat and t.ul_lon <= lon < t.ul_lon + w * srtm.PIXEL_DEG:
                v = t.z[srtm.pixel_of(t, lat, lon)]
                if not np.isfinite(v) or not ok(float(v)):
                    problems.append(f"{name} ({lat}, {lon}): elevation {v} in {t.name} is not plausible")
                break
    return problems


def build_layer(src_dir: Optional[Path] = None, cell_deg: float = 0.5, log: Callable[[str], None] = print) -> Path:
    """Compute all cells from the downloaded tiles and save the layer ``earth_terrain``."""
    from .. import config

    src = Path(src_dir) if src_dir else config.resolve(config.dataset("earth_srtmgl30")["dest"])
    zips = sorted(src.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"No SRTMGL30 zips in {src}. Run: python -m analog_finder fetch earth --only earth_srtmgl30")
    n_lat, n_lon = int(round(180 / cell_deg)), int(round(360 / cell_deg))
    full = {k: np.full((n_lat, n_lon), np.nan, dtype=np.float32) for k in SPEC}
    problems: list[str] = []
    for k, path in enumerate(zips, 1):
        tile = srtm.read_tile(path)
        feats = tile_cell_features(tile.z, tile.ul_lat, cell_deg)
        r0 = int(round((90.0 - tile.ul_lat) / cell_deg))
        c0 = int(round((tile.ul_lon + 180.0) / cell_deg))
        nr, nc = feats["elev_mean_m"].shape
        for name, arr in feats.items():
            full[name][r0: r0 + nr, c0: c0 + nc] = arr
        log(f"  [{k:2d}/{len(zips)}] {path.name}: {int(np.isfinite(feats['elev_mean_m']).sum())} cells")
        problems += selfcheck({path.name: tile})        # one tile at a time: a tile is 115 MB in memory
    if problems:
        raise RuntimeError("SRTM self-check failed, the tiles are read wrongly:\n  " + "\n  ".join(problems))
    log("SRTM self-check: ok (Everest, Dead Sea, Titicaca, Death Valley)")
    items = [layers.LayerFeature(name, full[name], *SPEC[name][:2], unit=SPEC[name][2], description=SPEC[name][3], source=SOURCE)
             for name in SPEC]
    return layers.save_layer("earth_terrain", items, cell_deg)
