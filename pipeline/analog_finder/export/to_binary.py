"""Compact binary grid for the browser.

Files written to data/processed/:
  grid_index.bin  Uint32 little-endian, one flat cell index per kept cell
                  (index = row * n_lon + col; row 0 is the northernmost)
  grid.bin        Uint8, feature-major: feature f occupies bytes [f * n_cells, (f + 1) * n_cells)
  grid.json       metadata: grid geometry, feature list, quantisation

Decoding a value:  v = min + q / 254 * (max - min);  q == 255 means "no data".
Python (this module) and TypeScript (web/src/lib/grid.ts) must decode identically.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

NODATA = 255
QMAX = 254


@dataclass
class Feature:
    name: str
    values: np.ndarray          # one float per kept cell
    vmin: float
    vmax: float
    unit: str = ""
    description: str = ""
    source: str = ""


def quantize(values: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    q = np.full(v.shape, NODATA, dtype=np.uint8)
    ok = np.isfinite(v)
    span = (vmax - vmin) or 1.0
    q[ok] = np.clip(np.rint((v[ok] - vmin) / span * QMAX), 0, QMAX).astype(np.uint8)
    return q


def dequantize(q: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    out = vmin + q.astype(np.float64) / QMAX * (vmax - vmin)
    out[q == NODATA] = np.nan
    return out


def write_grid(out_dir: str | Path, index: np.ndarray, shape: tuple[int, int], cell_deg: float,
               features: list[Feature], extra: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = int(index.size)
    for ft in features:
        if ft.values.shape != (n,):
            raise ValueError(f"feature {ft.name}: expected {n} values, got {ft.values.shape}")
    index.astype("<u4").tofile(out_dir / "grid_index.bin")
    block = np.concatenate([quantize(ft.values, ft.vmin, ft.vmax) for ft in features]) if features else np.zeros(0, np.uint8)
    block.tofile(out_dir / "grid.bin")
    meta = {
        "version": 1,
        "created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid": {
            "cell_deg": cell_deg,
            "n_lat": shape[0],
            "n_lon": shape[1],
            "n_cells": n,
            "row0_lat_center": 90.0 - cell_deg / 2.0,
            "col0_lon_center": -180.0 + cell_deg / 2.0,
            "row_order": "north_to_south",
            "index": {"file": "grid_index.bin", "dtype": "uint32", "endian": "little",
                      "meaning": "row * n_lon + col"},
        },
        "bin": {"file": "grid.bin", "dtype": "uint8", "layout": "feature_major", "nodata": NODATA,
                "decode": "value = min + q / 254 * (max - min)"},
        "features": [
            {"name": ft.name, "offset": k * n, "min": ft.vmin, "max": ft.vmax, "unit": ft.unit,
             "description": ft.description, "source": ft.source}
            for k, ft in enumerate(features)
        ],
    }
    if extra:
        meta.update(extra)
    with open(out_dir / "grid.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def read_grid(out_dir: str | Path) -> tuple[dict, np.ndarray, dict[str, np.ndarray]]:
    """Read the exported grid back: (metadata, cell index, decoded features)."""
    out_dir = Path(out_dir)
    with open(out_dir / "grid.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    n = meta["grid"]["n_cells"]
    index = np.fromfile(out_dir / "grid_index.bin", dtype="<u4")
    raw = np.fromfile(out_dir / "grid.bin", dtype=np.uint8)
    feats = {}
    for ft in meta["features"]:
        q = raw[ft["offset"]: ft["offset"] + n]
        feats[ft["name"]] = dequantize(q, ft["min"], ft["max"])
    return meta, index, feats
