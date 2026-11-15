"""Distance from every cell centre to the nearest major road (Natural Earth 1:10M), for the ``road_access`` filter
and the "getting there" part of the cell card."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np

from .. import config
from ..prep import layers

MAX_KM = 300.0
EARTH_R_KM = 6371.0
BIN_DEG = 0.1             # road vertices are binned to 0.1 degree before the distance search
STEP_KM = 5.0             # long segments are densified to this step
SOURCE = "Natural Earth 1:10M roads (public domain); computed by features/roads.py"


def cell_centres(cell_deg: float) -> tuple[np.ndarray, np.ndarray]:
    n_lat, n_lon = int(round(180 / cell_deg)), int(round(360 / cell_deg))
    return 90.0 - (np.arange(n_lat) + 0.5) * cell_deg, -180.0 + (np.arange(n_lon) + 0.5) * cell_deg


def nearest(points: Iterable[dict], cell_deg: float, max_km: float = MAX_KM) -> np.ndarray:
    """Great-circle distance from every cell centre to the nearest point, capped at ``max_km``."""
    clat, clon = cell_centres(cell_deg)
    n_lat, n_lon = clat.size, clon.size
    dist = np.full((n_lat, n_lon), max_km, dtype=np.float64)
    dlat = math.degrees(max_km / EARTH_R_KM)
    for p in points:
        r0 = max(0, int((90.0 - (p["lat"] + dlat)) / cell_deg))
        r1 = min(n_lat, int((90.0 - (p["lat"] - dlat)) / cell_deg) + 1)
        if r0 >= r1:
            continue
        coslat = math.cos(math.radians(min(abs(p["lat"]) + dlat, 89.9)))
        dlon = 360.0 if coslat < 1e-3 else dlat / coslat
        if dlon >= 180.0:
            cols = np.arange(n_lon)
        else:
            c0 = int(math.floor((p["lon"] - dlon + 180.0) / cell_deg))
            c1 = int(math.floor((p["lon"] + dlon + 180.0) / cell_deg)) + 1
            cols = np.arange(c0, c1) % n_lon
        la = np.radians(clat[r0:r1])[:, None]
        lo = np.radians(clon[cols])[None, :]
        pla, plo = math.radians(p["lat"]), math.radians(p["lon"])
        a = np.sin((la - pla) / 2) ** 2 + np.cos(la) * math.cos(pla) * np.sin((lo - plo) / 2) ** 2
        d = 2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        dist[r0:r1, cols] = np.minimum(dist[r0:r1][:, cols], d)
    return dist.astype(np.float32)


def cell_value(arr: np.ndarray, lat: float, lon: float, cell_deg: float) -> float:
    r = min(max(int((90.0 - lat) / cell_deg), 0), arr.shape[0] - 1)
    c = min(max(int((lon + 180.0) / cell_deg), 0), arr.shape[1] - 1)
    return float(arr[r, c])


def road_points(data: dict, bin_deg: float = BIN_DEG, step_km: float = STEP_KM) -> list[dict]:
    """Points along every road (ferry routes excluded), one per occupied bin of ``bin_deg`` degrees."""
    bins: set[tuple[int, int]] = set()
    for ft in data.get("features", []):
        props = ft.get("properties") or {}
        if "ferry" in str(props.get("type", "")).lower() or "ferry" in str(props.get("featurecla", "")).lower():
            continue
        geom = ft.get("geometry") or {}
        lines = geom.get("coordinates") or []
        if geom.get("type") == "LineString":
            lines = [lines]
        for line in lines:
            for (lo0, la0, *_), (lo1, la1, *_) in zip(line[:-1], line[1:]):
                dlon = (lo1 - lo0) * math.cos(math.radians((la0 + la1) / 2))
                n = max(1, int(math.hypot(dlon, la1 - la0) * 111.2 / step_km))
                for k in range(n + 1):
                    la, lo = la0 + (la1 - la0) * k / n, lo0 + (lo1 - lo0) * k / n
                    bins.add((int(math.floor(la / bin_deg)), int(math.floor(lo / bin_deg))))
    return [{"lat": (i + 0.5) * bin_deg, "lon": (j + 0.5) * bin_deg} for i, j in bins]


def roads_file(src_dir: Optional[Path] = None) -> Path:
    base = Path(src_dir) if src_dir else config.resolve(config.dataset("earth_naturalearth_roads")["dest"])
    return base / "ne_10m_roads.geojson"


def build_layer(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    path = roads_file(src_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python -m analog_finder fetch aux")
    cell = config.cell_deg()
    pts = road_points(json.loads(path.read_text(encoding="utf-8")))
    d = nearest(pts, cell)
    checks = (("Paris", 48.86, 2.35, lambda v: v < 30), ("Kyiv", 50.45, 30.52, lambda v: v < 30),
              ("Denver", 39.74, -104.99, lambda v: v < 30), ("Greenland ice sheet", 72.0, -40.0, lambda v: v > 250))
    problems = [f"{name}: {cell_value(d, lat, lon, cell):.0f} km to the nearest road is not plausible"
                for name, lat, lon, ok in checks if not ok(cell_value(d, lat, lon, cell))]
    if problems:
        raise RuntimeError("Road self-check failed:\n  " + "\n  ".join(problems))
    log(f"Roads: {len(pts)} road points (0.1 degree bins); self-check ok (Paris, Kyiv, Denver, Greenland)")
    item = layers.LayerFeature("road_dist_km", d, 0.0, MAX_KM, "km",
                               "Distance from the cell centre to the nearest major road of Natural Earth 1:10M (capped at "
                               "300 km); small and unpaved roads are not in the map", SOURCE)
    return layers.save_layer("earth_roads", [item], cell)
