"""Fingerprints of the Moon and Mars targets, computed from the raw PDS files.

For each target in config/targets.yaml:
  terrain_1km   relief, slopes and roughness at a step of about 1 km (comparable with Earth)
  thermal, ice  Moon: Diviner Polar Resource Product; Mars: Odyssey GRS water map
  sun           Moon: highest possible Sun elevation at that latitude

Run ``python -m analog_finder fetch pds`` first. Missing inputs are reported, not fatal.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import config
from ..features import sun, terrain
from ..io import pds, tables

MOON_RADIUS_KM = 1737.4
MOON_AGGREGATE = 4          # LOLA 240 m -> 960 m


def _haversine_km(lat0: float, lon0: float, lat, lon, radius_km: float) -> np.ndarray:
    p0, p = math.radians(lat0), np.radians(lat)
    dphi = p - p0
    dlam = np.radians(np.asarray(lon) - lon0)
    a = np.sin(dphi / 2) ** 2 + math.cos(p0) * np.cos(p) * np.sin(dlam / 2) ** 2
    return 2 * radius_km * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _clean(obj):
    """Make a result JSON-safe: NaN -> None, numpy scalars -> Python."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


# ----------------------------------------------------------------------------- Moon

def moon_terrain(img: pds.PdsImage, lat: float, lon: float, radius_km: float,
                 aggregate: int = MOON_AGGREGATE) -> dict:
    """Terrain of a polar-stereographic LOLA window, aggregated to about 1 km."""
    geo = img.geo
    pad = 2 * aggregate * geo.scale_m
    rs, cs, clipped = geo.window(lat, lon, radius_km * 1000.0 + pad)
    z = terrain.block_mean(img.height(rs, cs), aggregate)
    dx, dy = geo.pixel_size_m(lat)
    step_x, step_y = dx * aggregate, dy * aggregate
    row, col = geo.rowcol(lat, lon)
    center = ((row - rs.start + 0.5) / aggregate - 0.5, (col - cs.start + 0.5) / aggregate - 0.5)
    mask = terrain.circle_mask(z.shape, center, radius_km * 1000.0 / step_y, radius_km * 1000.0 / step_x)
    out = terrain.summarize(z, step_x, step_y, mask)
    out["clipped_by_image_edge"] = bool(clipped)
    return out


def moon_thermal(prp: dict, lat: float, lon: float, radius_km: float) -> dict:
    """Diviner PRP statistics of the model triangles whose centres fall inside the window."""
    d = _haversine_km(lat, lon, prp["tri_clat"], prp["tri_clon"], MOON_RADIUS_KM)
    m = d <= radius_km
    n = int(m.sum())
    if n == 0:
        return {"n_triangles": 0, "note": "No Diviner PRP triangles inside the window (outside the product coverage)."}
    t_avg, t_max, ice = prp["temp_avg"][m], prp["temp_max"][m], prp["ice_depth"][m]
    stable = ice >= 0                      # -999 marks "deeper than 2.87 m"
    return {
        "n_triangles": n,
        "temp_avg_mean_K": float(np.mean(t_avg)),
        "temp_avg_min_K": float(np.min(t_avg)),
        "temp_avg_p10_K": float(np.percentile(t_avg, 10)),
        "temp_max_mean_K": float(np.mean(t_max)),
        "temp_max_min_K": float(np.min(t_max)),
        "frac_ice_stable_at_surface": float(np.mean(ice == 0)),
        "frac_ice_stable_within_1m": float(np.mean(stable & (ice <= 1.0))),
        "frac_ice_stable_within_2p87m": float(np.mean(stable)),
        "ice_depth_median_m_where_stable": float(np.median(ice[stable])) if stable.any() else None,
    }


def selfcheck_moon(img: pds.PdsImage) -> list[str]:
    """Georeferencing sanity check on known lunar landmarks. Returns a list of problems."""
    problems = []
    geo = img.geo
    rs, cs, _ = geo.window(-89.67, 129.78, 3000.0)
    floor = float(np.median(img.height(rs, cs)))
    if not floor < -2000.0:
        problems.append(f"Shackleton floor should be below -2000 m, got {floor:.0f} m")
    rs, cs, _ = geo.window(-84.6, 31.0, 30000.0)
    top = float(np.max(img.height(rs, cs)))
    if not top > 3000.0:
        problems.append(f"Mons Mouton should rise above +3000 m, got {top:.0f} m")
    return problems


# ----------------------------------------------------------------------------- Mars

def mars_dem_for(lat: float, lon_e: float) -> Optional[pds.PdsImage]:
    """The 64 px/deg MOLA tile that holds the point, or the global 16 px/deg grid as a fallback."""
    top = 90 if lat >= 0 else 0
    west = 0 if (lon_e % 360.0) < 180.0 else 180
    lbl = config.dataset_file("mars_mola_megdr_64", f"megt{top:02d}n{west:03d}gb.lbl")
    if lbl.exists() and lbl.with_suffix(".img").exists():
        return pds.read_image(lbl)
    lbl = config.dataset_file("mars_mola_megdr_16", "megt90n000eb.lbl")
    if lbl.exists() and lbl.with_suffix(".img").exists():
        return pds.read_image(lbl)
    return None


def cylindrical_terrain(img: pds.PdsImage, lat: float, lon: float, radius_km: float) -> dict:
    """Terrain of a window of a latitude/longitude grid (Mars MOLA, Earth SRTMGL30).

    Columns are averaged in groups so that pixels are roughly square on the ground.
    """
    geo = img.geo
    dx0, dy = geo.pixel_size_m(lat)
    fx = max(1, int(round(dy / max(dx0, 1e-9))))
    pad = 2.0 * max(dy, dx0 * fx)
    rs, cs, clipped = geo.window(lat, lon, radius_km * 1000.0 + pad)
    z = img.height(rs, cs)
    n_cols = (z.shape[1] // fx) * fx
    z = z[:, :n_cols].reshape(z.shape[0], n_cols // fx, fx).mean(axis=2)
    rows = np.arange(rs.start, rs.stop)
    lat_rows = geo.max_lat - (rows + 0.5) / geo.res
    deg_m = math.pi * geo.radius_m / 180.0
    dx_rows = deg_m * np.cos(np.radians(lat_rows)) / geo.res * fx
    row, col = geo.rowcol(lat, lon)
    center = (row - rs.start, (col - cs.start + 0.5) / fx - 0.5)
    mask = terrain.circle_mask(z.shape, center, radius_km * 1000.0 / dy, radius_km * 1000.0 / (dx0 * fx))
    out = terrain.summarize(z, dx_rows, dy, mask)
    out["clipped_by_image_edge"] = bool(clipped)
    out["column_aggregation"] = fx
    return out


def selfcheck_mars() -> list[str]:
    """Georeferencing sanity check on Olympus Mons and Hellas. Returns a list of problems."""
    problems = []
    img = mars_dem_for(18.65, 226.2)
    if img is not None:
        rs, cs, _ = img.geo.window(18.65, 226.2, 100000.0)
        top = float(np.max(img.height(rs, cs)))
        if not top > 20000.0:
            problems.append(f"Olympus Mons should rise above 20000 m, got {top:.0f} m")
    img = mars_dem_for(-42.7, 70.0)
    if img is not None:
        rs, cs, _ = img.geo.window(-42.7, 70.0, 300000.0)
        low = float(np.min(img.height(rs, cs)))
        if not low < -6500.0:
            problems.append(f"Hellas floor should be below -6500 m, got {low:.0f} m")
    return problems


# ----------------------------------------------------------------------------- all targets

def build_profiles(log: Callable[[str], None] = print) -> dict:
    cfg = config.targets()
    defaults = cfg.get("defaults", {})
    out: dict = {"created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "method": "Terrain at a step of about 1 km: Horn slopes, RMS roughness in 3x3 windows, relief P95-P5.",
                 "selfcheck": {}, "missing_inputs": [], "targets": {}}

    # Moon inputs
    moon_img = None
    lbl = config.dataset_file("moon_lola_polar_dem", "ldem_75s_240m.lbl")
    if lbl.exists() and lbl.with_suffix(".img").exists():
        moon_img = pds.read_image(lbl)
        out["selfcheck"]["moon_lola"] = selfcheck_moon(moon_img) or "ok"
        log(f"Moon LOLA georeferencing check: {out['selfcheck']['moon_lola']}")
    else:
        out["missing_inputs"].append("data/raw/moon/lola/ldem_75s_240m.img + .lbl")
    prp = None
    prp_path = config.dataset_file("moon_diviner_prp", "dlre_prp_south.tab")
    if prp_path.exists():
        log("Reading Diviner PRP (2.88 million rows)...")
        prp = tables.read_diviner_prp(prp_path)
    else:
        out["missing_inputs"].append("data/raw/moon/diviner/dlre_prp_south.tab")

    # Mars inputs
    grs = None
    grs_path = config.dataset_file("mars_grs_h2o", "h2o_sr_5x5.tab")
    if grs_path.exists():
        grs = tables.read_grs_table(grs_path)
    else:
        out["missing_inputs"].append("data/raw/mars/grs/h2o_sr_5x5.tab")
    mars_problems = selfcheck_mars()
    if mars_dem_for(0.0, 0.0) is None:
        out["missing_inputs"].append("data/raw/mars/mola/megt*.img + .lbl")
    else:
        out["selfcheck"]["mars_mola"] = mars_problems or "ok"
        log(f"Mars MOLA georeferencing check: {out['selfcheck']['mars_mola']}")

    for t in cfg["targets"]:
        world, lat, lon = t["world"], float(t["lat"]), float(t["lon_e"])
        radius = float(t.get("radius_km", defaults.get(world, {}).get("radius_km", 25)))
        prof: dict = {"world": world, "name": t["name"], "lat": lat, "lon_e": lon, "radius_km": radius,
                      "mvp": bool(t.get("mvp", False)), "coord_quality": t.get("coord_quality")}
        if world == "moon":
            prof["sun"] = {"max_elevation_deg_flat_horizon": sun.moon_max_sun_elevation_deg(lat)}
            if moon_img is not None:
                prof["terrain_1km"] = moon_terrain(moon_img, lat, lon, radius)
                prof["terrain_240m"] = moon_terrain(moon_img, lat, lon, radius, aggregate=1)
            if prp is not None:
                prof["thermal_ice"] = moon_thermal(prp, lat, lon, radius)
        elif world == "mars":
            img = mars_dem_for(lat, lon)
            if img is not None:
                prof["terrain_1km"] = cylindrical_terrain(img, lat, lon, radius)
                prof["terrain_source"] = img.path.name
            if grs is not None:
                b = tables.nearest_bin(grs, lat, lon)
                prof["water"] = {"h2o_weight_percent": b["value"], "sigma": b.get("sigma"),
                                 "bin_center_lat": b["lat"], "bin_center_lon_e": b["lon"],
                                 "note": "Mars Odyssey GRS, 5 degree bins, smoothed; upper tens of centimetres of soil."}
        out["targets"][t["id"]] = prof
        log(f"  {t['id']:20s} {world:5s} " + ("terrain ok" if "terrain_1km" in prof else "terrain missing"))
    return _clean(out)


def write_profiles(path: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    path = path or (config.processed_dir() / "target_profiles.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    profiles = build_profiles(log)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    if profiles["missing_inputs"]:
        log("Missing inputs (run: python -m analog_finder fetch pds):")
        for m in profiles["missing_inputs"]:
            log(f"  {m}")
    log(f"Wrote {path}")
    return path
