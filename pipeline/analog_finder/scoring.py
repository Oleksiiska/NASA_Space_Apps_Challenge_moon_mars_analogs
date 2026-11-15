"""Similarity of Earth cells to a Moon or Mars target, per test task.

Every criterion is a score in [0, 1] per cell, NaN where the data are missing (unknown is never turned into 0).
Two kinds of criteria:

* Matched to the target (need the target's profile): slope_hist, relief, roughness. The same ground step of ~1 km on all
  three worlds makes these numbers directly comparable.
* Earth-side direction criteria (the same for every target): cold, thermal_range, low_sun, ground_ice, bare_ground,
  snow_free, composition. Earth cannot reach lunar or Martian values (Earth never gets as cold as a permanently shadowed
  crater), so these rank Earth cells by how far they go in the useful direction: percentile among Earth land cells, or an
  absolute scale where one exists. What stays different is listed in data/reference/environment_gaps.json.

A task score is the weighted mean of the criteria that exist for the cell. ``coverage`` is the share of the task weight that
had data; cells under ``MIN_COVERAGE`` get no score. Hard constraints are boolean masks; a cell that fails one is not ranked.
Volcanic, impact and dryness exist only when their layers are in the grid (``context``, ``surface --only precip``); a
criterion without data is reported, never guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from . import config
from .export import to_binary

MIN_COVERAGE = 0.5
HIST = [f"slope_h{k}" for k in range(9)]
NO_DATA_YET = ("dryness", "volcanic", "impact")   # criteria that may have no layer; see no_data()
CONTEXT_NEAR_KM, CONTEXT_FAR_KM = 25.0, 150.0     # volcanic / impact: full score within 25 km, none beyond 150 km
ALTERATION = ("min_kaolinite", "min_montmorillonite", "min_illite_muscovite", "min_vermiculite", "min_chlorite",
              "min_gypsum", "min_calcite", "min_dolomite", "min_hematite", "min_goethite")
SHARED = ("cold", "thermal_range", "ground_ice", "bare_ground", "low_sun", "snow_free", "composition",
          "volcanic", "impact", "dryness")
MATCHED = ("slope_hist", "relief", "roughness")
SITE_NEAR_KM = 60.0       # a site whose own cell is not land (island, coast) takes the nearest land cell this close
BARE_PX_MIN = 0.10        # bare_ground_min also passes when this share of 5 km pixels has NDVI <= 0.25


@dataclass
class Cells:
    index: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    f: dict[str, np.ndarray]
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(self.index.size)

    def position(self, lat: float, lon: float) -> int:
        """Position of the cell that contains a point, -1 if it is not a land cell of the grid."""
        g = self.meta["grid"]
        r = int((90.0 - lat) / g["cell_deg"])
        c = int((lon + 180.0) / g["cell_deg"])
        flat = r * g["n_lon"] + c
        k = int(np.searchsorted(self.index, flat))
        return k if k < self.index.size and int(self.index[k]) == flat else -1

    def site_position(self, lat: float, lon: float, max_km: float = SITE_NEAR_KM) -> int:
        """Cell of a site; when that cell is not a land cell (a narrow island or a coast), the nearest land cell
        whose centre lies within ``max_km`` of the site. -1 if there is none."""
        k = self.position(lat, lon)
        if k >= 0:
            return k
        g = self.meta["grid"]
        r0, c0 = int((90.0 - lat) / g["cell_deg"]), int((lon + 180.0) / g["cell_deg"])
        best, best_d = -1, max_km
        for dr in (-2, -1, 0, 1, 2):
            for dc in (-2, -1, 0, 1, 2):
                r, c = r0 + dr, (c0 + dc) % g["n_lon"]
                if not 0 <= r < g["n_lat"]:
                    continue
                flat = r * g["n_lon"] + c
                j = int(np.searchsorted(self.index, flat))
                if j >= self.index.size or int(self.index[j]) != flat:
                    continue
                p1, p2 = np.radians(lat), np.radians(self.lat[j])
                a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(self.lon[j] - lon) / 2) ** 2
                d = 2 * 6371.0 * np.arcsin(np.sqrt(a))
                if d <= best_d:
                    best, best_d = j, d
        return best


def load_cells(processed_dir: str | Path | None = None) -> Cells:
    meta, index, feats = to_binary.read_grid(processed_dir or config.processed_dir())
    g = meta["grid"]
    idx = index.astype(np.int64)
    row, col = idx // g["n_lon"], idx % g["n_lon"]
    lat = g["row0_lat_center"] - row * g["cell_deg"]
    lon = g["col0_lon_center"] + col * g["cell_deg"]
    return Cells(index=index, lat=lat, lon=lon, f=feats, meta=meta)


def pct_rank(x: np.ndarray) -> np.ndarray:
    """Percentile 0..1 of each finite value among the finite values (ties share the mean rank); NaN stays NaN."""
    out = np.full(x.shape, np.nan, dtype=np.float32)
    ok = np.isfinite(x)
    v = x[ok]
    if v.size:
        srt = np.sort(v)
        lo = np.searchsorted(srt, v, side="left")
        hi = np.searchsorted(srt, v, side="right")
        out[ok] = ((lo + hi) / 2.0 / v.size).astype(np.float32)
    return out


def _log_match(c: np.ndarray, t: float, scale: float, sigma: float = 0.7) -> np.ndarray:
    d = (np.log1p(np.maximum(c, 0) / scale) - np.log1p(max(t, 0.0) / scale)) / sigma
    return np.exp(-0.5 * d * d).astype(np.float32)


def matched_criteria(cells: Cells, terrain_1km: dict) -> dict[str, np.ndarray]:
    """Terrain criteria of every Earth cell against one target's 1 km terrain fingerprint."""
    t_hist = np.asarray(terrain_1km["slope_hist"], dtype=np.float64)
    if t_hist.size != len(HIST):
        raise ValueError(f"target slope histogram has {t_hist.size} bins, the grid has {len(HIST)}")
    h = np.stack([cells.f[k] for k in HIST]).astype(np.float64)            # (9, n)
    slope = (1.0 - 0.5 * np.abs(h - t_hist[:, None]).sum(axis=0)).astype(np.float32)
    slope[~np.isfinite(h).all(axis=0)] = np.nan
    return {
        "slope_hist": np.clip(slope, 0, 1),
        "relief": _log_match(cells.f["relief_m"], float(terrain_1km["relief_p5_p95_m"]), 50.0),
        "roughness": _log_match(cells.f["rough_p50_m"], float(terrain_1km["roughness_rms_p50_m"]), 5.0),
    }


def proximity(dist_km: np.ndarray, near: float = CONTEXT_NEAR_KM, far: float = CONTEXT_FAR_KM) -> np.ndarray:
    """1 within ``near`` km, falling linearly to 0 at ``far`` km; NaN stays NaN."""
    return np.clip((far - dist_km) / (far - near), 0.0, 1.0).astype(np.float32)


def no_data(shared: dict) -> list[str]:
    """Criteria of NO_DATA_YET that have no layer in this grid."""
    return [c for c in NO_DATA_YET if c not in shared]


def shared_criteria(cells: Cells) -> dict[str, np.ndarray]:
    f = cells.f
    t_mean = (f["lst_day_mean_k"] + f["lst_night_mean_k"]) / 2.0
    ndvi = f["ndvi_mean"]
    permafrost = np.clip((273.15 - t_mean) / 20.0, 0, 1)                   # annual mean skin temperature under 0 C ~ permafrost
    ground_ice = np.fmax(permafrost, f["ice_frac"])                          # glacier ice is also accessible ice
    ground_ice = np.where(np.isfinite(permafrost), ground_ice, np.nan).astype(np.float32)
    alt = np.zeros(cells.n, dtype=np.float32)
    have = np.isfinite(f["min_kaolinite"])
    for k in ALTERATION:
        alt += np.nan_to_num(f[k])
    alt[~have] = np.nan
    out = {
        "cold": pct_rank(-t_mean),
        "thermal_range": pct_rank(f["lst_diurnal_k"]),
        "ground_ice": ground_ice,
        "bare_ground": np.clip(1.0 - (ndvi - 0.05) / 0.25, 0, 1).astype(np.float32),
        "low_sun": pct_rank(f["lowsun_best_h"]),
        "snow_free": (f["snow_free_months"] / 12.0).astype(np.float32),
        "composition": pct_rank(alt),
    }
    if "precip_log_mm" in f:              # GPM IMERG annual precipitation: drier ranks higher, as cold does
        out["dryness"] = pct_rank(-f["precip_log_mm"])
    if "volcano_dist_km" in f:
        out["volcanic"] = proximity(f["volcano_dist_km"])
    if "impact_dist_km" in f:
        out["impact"] = proximity(f["impact_dist_km"])
    return out


def constraints(cells: Cells) -> dict[str, np.ndarray]:
    """Hard filters that can be checked with the data in the grid. Unknown values pass, except for the snow window."""
    f = cells.f
    with np.errstate(invalid="ignore"):
        ndvi_ok = ~(f["ndvi_mean"] > 0.25)
        if "bare_px_frac" in f:           # or at least 10 % of the 5 km pixels are bare (a bare volcano in a green cell)
            ndvi_ok = ndvi_ok | (f["bare_px_frac"] >= BARE_PX_MIN)
        flat_ok = ~(f["slope_lt8"] < 0.05)
        ice_ok = ~((f["lst_day_mean_k"] + f["lst_night_mean_k"]) / 2.0 >= 273.15) | (f["ice_frac"] > 0.5)
        snow_ok = f["snow_free_months"] >= 0.5         # whole months, stored quantised: 1 month reads back as 0.99
        no_ice_sheet = ~(f["ice_frac"] > 0.5)
    out = {"bare_ground_min": ndvi_ok, "flat_patch_exists": flat_ok, "ground_ice_present": ice_ok,
           "snow_free_window": np.asarray(snow_ok), "not_ice_sheet": np.asarray(no_ice_sheet)}
    if "road_dist_km" in f:
        with np.errstate(invalid="ignore"):
            out["road_access"] = ~(f["road_dist_km"] > ROAD_MAX_KM)
    return out


NOT_CHECKED = ("road_access", "safe_access", "protected_ecosystem_flag")
ROAD_MAX_KM = 50.0        # road_access: a major road within 50 km of the cell centre


def task_score(task: dict, crit: dict[str, np.ndarray], world: str, cells: Cells,
               weights: Optional[dict[str, float]] = None, min_coverage: float = MIN_COVERAGE,
               check_constraints: bool = True) -> tuple[np.ndarray, np.ndarray, dict]:
    """(score, coverage, info) for one task. ``info`` names the criteria used and the ones without data."""
    w = dict(weights or task["weights"])
    total = sum(w.values())
    num = np.zeros(cells.n, dtype=np.float64)
    den = np.zeros(cells.n, dtype=np.float64)
    used, missing = [], []
    for name, wt in w.items():
        s = crit.get(name)
        if s is None or (world == "moon" and name == "composition"):
            missing.append(name)
            continue
        used.append(name)
        ok = np.isfinite(s)
        num += np.where(ok, wt * np.nan_to_num(s), 0.0)
        den += np.where(ok, wt, 0.0)
    cov = (den / total).astype(np.float32)
    with np.errstate(invalid="ignore", divide="ignore"):
        score = (num / den).astype(np.float32)
    score[(cov < min_coverage) | (den == 0)] = np.nan
    unchecked = []
    if check_constraints:
        cons = constraints(cells)
        off = set(task.get("constraints_off", []))   # listed for the page switch, but off by default
        for c in task.get("constraints", []):
            if c in off:
                continue
            if c in cons:
                score[~cons[c]] = np.nan
            else:
                unchecked.append(c)
    return score, cov, {"used": used, "no_data": missing, "constraints_not_checked": unchecked}


def criteria_for(cells: Cells, target: dict, shared: Optional[dict] = None) -> dict[str, np.ndarray]:
    crit = dict(shared if shared is not None else shared_criteria(cells))
    crit.update(matched_criteria(cells, target["terrain_1km"]))
    return crit


def rank_of(score: np.ndarray, pos: int) -> float:
    """Share of ranked cells that score below cell ``pos`` (ties count half); NaN if that cell has no score."""
    if pos < 0 or not np.isfinite(score[pos]):
        return float("nan")
    ok = score[np.isfinite(score)]
    return float(((ok < score[pos]).sum() + 0.5 * (ok == score[pos]).sum()) / ok.size)
