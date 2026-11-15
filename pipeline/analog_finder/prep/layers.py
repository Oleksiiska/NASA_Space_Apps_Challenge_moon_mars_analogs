"""Feature layers on the Earth grid.

A layer is a set of 2D arrays on the full grid (n_lat x n_lon, NaN where unknown)
saved to ``data/interim/layers/<name>.npz``. ``merge_into_grid`` writes layers into
``data/processed/grid.bin`` for the land cells of the existing grid, replacing
features of the same name. The slow land mask is not rebuilt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import config
from ..export import to_binary


@dataclass
class LayerFeature:
    name: str
    values: np.ndarray        # (n_lat, n_lon) float, NaN = no data
    vmin: float
    vmax: float
    unit: str = ""
    description: str = ""
    source: str = ""


def layers_dir() -> Path:
    return config.data_dir() / "interim" / ("layers" + config.grid_suffix())


def save_layer(layer: str, features: list[LayerFeature], cell_deg: float = 0.5) -> Path:
    path = layers_dir() / f"{layer}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"layer": layer, "cell_deg": cell_deg,
            "features": [{"name": f.name, "vmin": f.vmin, "vmax": f.vmax, "unit": f.unit,
                          "description": f.description, "source": f.source} for f in features]}
    arrays = {f.name: np.asarray(f.values, dtype=np.float32) for f in features}
    np.savez_compressed(path, __meta__=np.array(json.dumps(meta)), **arrays)
    return path


def load_layer(path: str | Path) -> tuple[dict, list[LayerFeature]]:
    with np.load(path, allow_pickle=False) as z:
        meta = json.loads(str(z["__meta__"]))
        feats = [LayerFeature(name=m["name"], values=z[m["name"]], vmin=m["vmin"], vmax=m["vmax"], unit=m.get("unit", ""),
                              description=m.get("description", ""), source=m.get("source", ""))
                 for m in meta["features"]]
    return meta, feats


def merge_into_grid(out_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> dict:
    """Add every saved layer to grid.bin / grid.json; features of the same name are replaced."""
    out_dir = Path(out_dir) if out_dir else config.processed_dir()
    meta, index, current = to_binary.read_grid(out_dir)
    n_lat, n_lon, cell_deg = meta["grid"]["n_lat"], meta["grid"]["n_lon"], meta["grid"]["cell_deg"]
    order = [f["name"] for f in meta["features"]]
    feats = {f["name"]: to_binary.Feature(f["name"], current[f["name"]], f["min"], f["max"], f.get("unit", ""),
                                          f.get("description", ""), f.get("source", "")) for f in meta["features"]}
    added = []
    for path in sorted(layers_dir().glob("*.npz")) if layers_dir().exists() else []:
        lmeta, lfeats = load_layer(path)
        if abs(lmeta["cell_deg"] - cell_deg) > 1e-9:
            log(f"  skipped {path.name}: cell size {lmeta['cell_deg']} differs from the grid ({cell_deg})")
            continue
        for lf in lfeats:
            if lf.values.shape != (n_lat, n_lon):
                log(f"  skipped {path.name}:{lf.name}: shape {lf.values.shape} differs from the grid")
                continue
            vals = lf.values.ravel()[index.astype(np.int64)]
            feats[lf.name] = to_binary.Feature(lf.name, vals, lf.vmin, lf.vmax, lf.unit, lf.description, lf.source)
            if lf.name not in order:
                order.append(lf.name)
            added.append(lf.name)
    skip = {"version", "created_utc", "grid", "bin", "features"}
    extra = {k: v for k, v in meta.items() if k not in skip}
    new_meta = to_binary.write_grid(out_dir, index, (n_lat, n_lon), cell_deg, [feats[n] for n in order], extra=extra)
    have = [int(np.isfinite(feats[n].values).sum()) for n in added]
    log(f"grid.bin now holds {len(order)} features ({len(added)} added or replaced) for {index.size} land cells")
    for n, k in zip(added, have):
        log(f"  {n:18s} {k:6d} of {index.size} cells have a value")
    return new_meta
