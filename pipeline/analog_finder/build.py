"""Build the Earth grid and the features that need no downloads.

Outputs in data/processed/:
  grid.json, grid.bin, grid_index.bin   land cells with land_frac, ice_frac and low-Sun features
  lowsun_by_latitude.csv                hours per day with a low Sun, by latitude and month
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Optional


from . import config
from .export import to_binary
from .features import sun
from .prep import grid as grid_mod


def write_low_sun_csv(path: Path, table: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat"] + [f"m{m:02d}" for m in range(1, 13)] + ["mean_hours", "best_hours", "best_month"])
        for k, lat in enumerate(table["lat"]):
            w.writerow([f"{lat:.2f}"] + [f"{v:.3f}" for v in table["monthly_hours"][k]]
                       + [f"{table['mean_hours'][k]:.3f}", f"{table['best_hours'][k]:.3f}", int(table["best_month"][k])])


def build_grid(cell_deg: float = grid_mod.CELL_DEG, min_land_frac: float = grid_mod.MIN_LAND_FRAC,
               out_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> dict:
    out_dir = out_dir or config.processed_dir()
    land = config.dataset_file("earth_naturalearth_land", "ne_50m_land.geojson")
    ice = config.dataset_file("earth_naturalearth_land", "ne_50m_glaciated_areas.geojson")
    if not land.exists():
        raise FileNotFoundError(f"{land} is missing. Run: python -m analog_finder fetch aux")
    log("Rasterising Natural Earth land polygons...")
    g = grid_mod.build(land, ice if ice.exists() else None, cell_deg=cell_deg, min_land_frac=min_land_frac)
    rows = g.rows
    log(f"Grid {g.shape[0]} x {g.shape[1]}, {g.index.size} land cells (land fraction >= {min_land_frac})")

    table = sun.low_sun_table(cell_deg)
    write_low_sun_csv(out_dir / "lowsun_by_latitude.csv", table)

    band = f"{sun.LOW_BAND_DEG[0]:g}-{sun.LOW_BAND_DEG[1]:g} deg"
    features = [
        to_binary.Feature("land_frac", g.land_frac.ravel()[g.index], 0.0, 1.0, "fraction",
                          "Share of the cell that is land", "Natural Earth 1:50m land"),
        to_binary.Feature("ice_frac", g.ice_frac.ravel()[g.index], 0.0, 1.0, "fraction",
                          "Share of the cell under glaciers or ice sheets", "Natural Earth 1:50m glaciated areas"),
        to_binary.Feature("lowsun_best_h", table["best_hours"][rows], 0.0, 24.0, "hours/day",
                          f"Hours per day with the Sun {band} above the horizon, mean of the best month",
                          "Computed from solar geometry (features/sun.py)"),
        to_binary.Feature("lowsun_mean_h", table["mean_hours"][rows], 0.0, 24.0, "hours/day",
                          f"Hours per day with the Sun {band} above the horizon, annual mean",
                          "Computed from solar geometry (features/sun.py)"),
        to_binary.Feature("lowsun_best_month", table["best_month"][rows].astype(float), 1.0, 12.0, "month",
                          "Month (1-12) with the longest low-Sun time; round the decoded value",
                          "Computed from solar geometry (features/sun.py)"),
    ]
    meta = to_binary.write_grid(out_dir, g.index, g.shape, cell_deg, features,
                                extra={"min_land_frac": min_land_frac,
                                       "low_sun_band_deg": list(sun.LOW_BAND_DEG),
                                       "low_sun_table": "lowsun_by_latitude.csv"})
    log(f"Wrote grid.json, grid.bin ({len(features)} features), grid_index.bin and lowsun_by_latitude.csv to {out_dir}")
    return meta
