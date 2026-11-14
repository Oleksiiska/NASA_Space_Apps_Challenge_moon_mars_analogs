"""Geological and climate context of Earth cells: Holocene volcanoes, impact structures, dryness.

* Volcanoes (Smithsonian Global Volcanism Program list): distance from each cell centre to the nearest
  land volcano, and to the nearest basaltic one (shield volcanoes, volcanic fields, fissure vents,
  cinder cones and similar forms, which are where lava tubes and fresh basalt are found).
* Impact structures (Earth Impact Database): distance from the cell centre to the rim of the nearest
  confirmed structure (0 inside it), and that structure's diameter.
* Dryness (NASA POWER precipitation climatology, MERRA-2): mean annual precipitation of the cell.

Distances are great-circle distances in km, capped at ``MAX_KM``: a cell further away than that gets
``MAX_KM``, which the scoring turns into a score near 0. The tables list points, so a volcanic field of
50 km is reduced to one point: the distance is a proxy for "volcanic terrain nearby", nothing more.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np

from ..prep import layers

CELL_DEG = 0.5
MAX_KM = 300.0
EARTH_R_KM = 6371.0
BASALTIC = ("shield", "volcanic field", "fissure", "cinder", "scoria", "lava field", "lava cone", "crater row",
            "pyroclastic shield", "maar", "tuya")
VOLC_SOURCE = "Smithsonian Global Volcanism Program, list of Holocene volcanoes; computed by features/earth_context.py"
IMPACT_SOURCE = "Earth Impact Database (PASSC, University of New Brunswick); computed by features/earth_context.py"
POWER_SOURCE = "NASA POWER climatology (PRECTOTCORR, MERRA-2); computed by features/earth_context.py"


# --------------------------------------------------------------------------- reading the tables

def _float(x) -> float:
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return float("nan")


def read_volcanoes(path: str | Path) -> list[dict]:
    """Land volcanoes with lat, lon, type and a basaltic flag; submarine volcanoes are left out."""
    out = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            lat, lon = _float(row.get("Latitude")), _float(row.get("Longitude"))
            vtype = (row.get("Type") or "").strip()
            if not (math.isfinite(lat) and math.isfinite(lon)) or "submarine" in vtype.lower():
                continue
            out.append({"name": (row.get("Volcano Name") or "").strip(), "lat": lat, "lon": lon, "type": vtype,
                        "basaltic": any(k in vtype.lower() for k in BASALTIC)})
    return out


def read_impacts(path: str | Path) -> list[dict]:
    """Impact structures with lat, lon and diameter in km."""
    out = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            lat, lon, d = _float(row.get("latitude")), _float(row.get("longitude")), _float(row.get("diameter_km"))
            if math.isfinite(lat) and math.isfinite(lon):
                out.append({"name": (row.get("crater_name") or "").strip(), "lat": lat, "lon": lon,
                            "diameter_km": d if math.isfinite(d) else 0.0})
    return out


# --------------------------------------------------------------------------- distances on the grid

def cell_centres(n_lat: int = 360, n_lon: int = 720, cell_deg: float = CELL_DEG) -> tuple[np.ndarray, np.ndarray]:
    lat = 90.0 - (np.arange(n_lat) + 0.5) * cell_deg
    lon = -180.0 + (np.arange(n_lon) + 0.5) * cell_deg
    return lat, lon


def nearest(points: Iterable[dict], radius_km: Optional[Iterable[float]] = None, max_km: float = MAX_KM,
            n_lat: int = 360, n_lon: int = 720, cell_deg: float = CELL_DEG) -> tuple[np.ndarray, np.ndarray]:
    """(distance, index) of the nearest point for every cell centre, minus that point's radius (never below 0).

    Only cells within ``max_km`` + radius of a point are computed; the rest get ``max_km`` and index -1.
    """
    pts = list(points)
    rad = list(radius_km) if radius_km is not None else [0.0] * len(pts)
    clat, clon = cell_centres(n_lat, n_lon, cell_deg)
    dist = np.full((n_lat, n_lon), max_km, dtype=np.float64)
    idx = np.full((n_lat, n_lon), -1, dtype=np.int32)
    for k, (p, r) in enumerate(zip(pts, rad)):
        reach = max_km + max(r, 0.0)
        dlat = math.degrees(reach / EARTH_R_KM)
        r0 = max(0, int((90.0 - (p["lat"] + dlat)) / cell_deg))
        r1 = min(n_lat, int((90.0 - (p["lat"] - dlat)) / cell_deg) + 1)
        if r0 >= r1:
            continue
        coslat = min(math.cos(math.radians(min(abs(p["lat"]) + dlat, 89.9))), 1.0)
        dlon = 360.0 if coslat < 1e-3 else math.degrees(reach / EARTH_R_KM) / coslat
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
        d = 2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1))) - max(r, 0.0)
        d = np.maximum(d, 0.0)
        sub = dist[r0:r1][:, cols]
        better = d < sub
        sub = np.where(better, d, sub)
        isub = np.where(better, k, idx[r0:r1][:, cols])
        dist[r0:r1, cols] = sub
        idx[r0:r1, cols] = isub
    return np.minimum(dist, max_km).astype(np.float32), idx


def cell_value(arr: np.ndarray, lat: float, lon: float, cell_deg: float = CELL_DEG) -> float:
    r = min(max(int((90.0 - lat) / cell_deg), 0), arr.shape[0] - 1)
    c = min(max(int((lon + 180.0) / cell_deg), 0), arr.shape[1] - 1)
    return float(arr[r, c])


# --------------------------------------------------------------------------- volcanoes and impacts

def _src(key: str, name: str, src_dir: Optional[Path]) -> Path:
    from .. import config
    base = Path(src_dir) if src_dir else config.resolve(config.dataset(key)["dest"])
    path = base / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python -m analog_finder fetch aux")
    return path


def build_volcanic(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    vols = read_volcanoes(_src("earth_volcanoes", "volcano_db.csv", src_dir))
    basalt = [v for v in vols if v["basaltic"]]
    d_any, _ = nearest(vols)
    d_bas, _ = nearest(basalt)
    problems = []
    for name, lat, lon, arr, ok in (("Kilauea", 19.41, -155.29, d_bas, lambda v: v < 40),
                                    ("Craters of the Moon", 43.42, -113.5, d_bas, lambda v: v < 60),
                                    ("Etna", 37.75, 14.99, d_any, lambda v: v < 40),
                                    ("Tademait plateau, Algeria", 28.0, 2.0, d_any, lambda v: v > 250),
                                    ("Amazon", -3.0, -60.0, d_any, lambda v: v > 250)):
        v = cell_value(arr, lat, lon)
        if not ok(v):
            problems.append(f"{name}: distance {v:.0f} km is not plausible")
    if problems:
        raise RuntimeError("Volcano self-check failed:\n  " + "\n  ".join(problems))
    log(f"Volcanoes: {len(vols)} on land, {len(basalt)} basaltic; self-check ok (Kilauea, Craters of the Moon, Etna, Tademait, Amazon)")
    items = [layers.LayerFeature("volc_dist_km", d_any, 0.0, MAX_KM, "km", "Distance to the nearest Holocene volcano on land (capped at 300 km)", VOLC_SOURCE),
             layers.LayerFeature("volc_basalt_dist_km", d_bas, 0.0, MAX_KM, "km",
                                 "Distance to the nearest basaltic Holocene volcano: shield, volcanic field, fissure vent, cinder cone (capped at 300 km)", VOLC_SOURCE)]
    return layers.save_layer("earth_volcanic", items, CELL_DEG)


def build_impacts(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    imp = read_impacts(_src("earth_impacts", "earth-impact-craters.csv", src_dir))
    d, k = nearest(imp, radius_km=[p["diameter_km"] / 2 for p in imp])
    diam = np.where(k >= 0, np.array([p["diameter_km"] for p in imp] + [0.0], dtype=np.float32)[k], 0.0).astype(np.float32)
    problems = []
    for name, lat, lon, ok in (("Meteor Crater", 35.03, -111.02, lambda v: v < 40), ("Ries", 48.88, 10.58, lambda v: v < 40),
                               ("Vredefort", -27.0, 27.5, lambda v: v == 0), ("Amazon", -3.0, -60.0, lambda v: v > 250)):
        v = cell_value(d, lat, lon)
        if not ok(v):
            problems.append(f"{name}: distance {v:.0f} km is not plausible")
    if problems:
        raise RuntimeError("Impact self-check failed:\n  " + "\n  ".join(problems))
    log(f"Impact structures: {len(imp)}; self-check ok (Meteor Crater, Ries, Vredefort, Amazon)")
    items = [layers.LayerFeature("impact_dist_km", d, 0.0, MAX_KM, "km", "Distance to the rim of the nearest confirmed impact structure, 0 inside (capped at 300 km)", IMPACT_SOURCE),
             layers.LayerFeature("impact_diam_km", np.minimum(diam, 300.0), 0.0, 300.0, "km", "Diameter of that impact structure (0 when none within 300 km)", IMPACT_SOURCE)]
    return layers.save_layer("earth_impact", items, CELL_DEG)


# --------------------------------------------------------------------------- dryness from NASA POWER

def power_points(data: dict, parameter: str = "PRECTOTCORR") -> list[tuple[float, float, float]]:
    """(lat, lon, annual value) of every grid point of one POWER regional JSON response; fill -999 -> NaN."""
    feats = data.get("features")
    if feats is None and "geometry" in data:
        feats = [data]
    if feats is None:
        raise ValueError(f"not a POWER regional response: keys {sorted(data)[:8]}")
    out = []
    for ft in feats:
        coords = (ft.get("geometry") or {}).get("coordinates") or []
        par = ((ft.get("properties") or {}).get("parameter") or {}).get(parameter)
        if len(coords) < 2 or par is None:
            continue
        ann = par.get("ANN") if isinstance(par, dict) else None
        if ann is None and isinstance(par, dict):
            months = [v for k, v in par.items() if k.upper()[:3] in ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")]
            ann = float(np.mean(months)) if len(months) == 12 else None
        v = _float(ann)
        out.append((float(coords[1]), float(coords[0]), v if (math.isfinite(v) and v > -990) else float("nan")))
    return out


def points_to_grid(points: Iterable[tuple[float, float, float]], lat_step: float = 0.5, lon_step: float = 0.625,
                   n_lat: int = 360, n_lon: int = 720, cell_deg: float = CELL_DEG) -> np.ndarray:
    """POWER points (MERRA-2 grid, 0.5 x 0.625 degrees) -> our cells: mean of the two POWER rows around the centre at the nearest column."""
    nla = int(round(180 / lat_step)) + 1
    nlo = int(round(360 / lon_step))
    g = np.full((nla, nlo), np.nan, dtype=np.float64)
    for lat, lon, v in points:
        i = int(round((lat + 90.0) / lat_step))
        j = int(round((lon + 180.0) / lon_step)) % nlo
        if 0 <= i < nla:
            g[i, j] = v
    clat, clon = cell_centres(n_lat, n_lon, cell_deg)
    fi = (clat + 90.0) / lat_step
    i0 = np.clip(np.floor(fi).astype(int), 0, nla - 1)
    i1 = np.clip(np.ceil(fi).astype(int), 0, nla - 1)
    x = (clon + 180.0) / lon_step
    j1 = np.rint(x).astype(int)
    j2 = np.where(j1 == np.floor(x).astype(int), np.ceil(x).astype(int), np.floor(x).astype(int))

    def rows_mean(j: np.ndarray) -> np.ndarray:
        a, b = g[i0][:, j % nlo], g[i1][:, j % nlo]
        with np.errstate(invalid="ignore"):
            return np.where(np.isfinite(a) & np.isfinite(b), (a + b) / 2, np.where(np.isfinite(a), a, b))

    near, other = rows_mean(j1), rows_mean(j2)
    # the POWER regional API leaves out the column at longitude 0: fall back to the other neighbouring column
    return np.where(np.isfinite(near), near, other).astype(np.float32)


def build_dryness(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    from .. import config
    src = Path(src_dir) if src_dir else config.resolve(config.dataset("earth_power_precip_grid")["dest"])
    files = sorted(src.glob("box_*.json"))
    if not files:
        raise FileNotFoundError(f"No POWER boxes in {src}. Run: python -m analog_finder fetch power-grid")
    pts = []
    for p in files:
        pts += power_points(json.loads(p.read_text(encoding="utf-8")))
    mm_day = points_to_grid(pts)
    mm_yr = (mm_day * 365.25).astype(np.float32)
    problems = []
    for name, lat, lon, ok in (("Atacama", -24.0, -69.5, lambda v: v < 250), ("central Sahara", 25.0, 10.0, lambda v: v < 250),
                               ("Amazon", -3.0, -60.0, lambda v: v > 1200)):
        v = cell_value(mm_yr, lat, lon)
        if not math.isfinite(v):
            log(f"  note: {name} has no POWER value (box not downloaded?)")
        elif not ok(v):
            problems.append(f"{name}: {v:.0f} mm per year is not plausible")
    if problems:
        raise RuntimeError("POWER self-check failed, the boxes are read wrongly:\n  " + "\n  ".join(problems))
    log(f"Dryness: {len(files)} boxes, {len(pts)} POWER points, {int(np.isfinite(mm_yr).sum())} cells with precipitation")
    items = [layers.LayerFeature("precip_mm_yr", np.minimum(mm_yr, 4000.0), 0.0, 4000.0, "mm/year",
                                 "Mean annual precipitation, NASA POWER (MERRA-2 corrected), 0.5 x 0.625 degree points", POWER_SOURCE)]
    return layers.save_layer("earth_dryness", items, CELL_DEG)


BUILDERS = {"volcanic": build_volcanic, "impact": build_impacts, "dryness": build_dryness}


def build_all(which: Optional[list[str]] = None, log: Callable[[str], None] = print) -> list[Path]:
    out = []
    for key in which or list(BUILDERS):
        log(f"{key}:")
        try:
            out.append(BUILDERS[key](log=log))
        except FileNotFoundError as e:
            log(f"  skipped: {e}")
    return out
