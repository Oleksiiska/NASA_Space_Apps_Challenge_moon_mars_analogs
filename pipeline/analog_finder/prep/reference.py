"""Reference layers: known analog sites and Moon/Mars targets.

Inputs
  data/reference/known_analogs.csv   hand-kept table of sites already used as analogs
  pipeline/config/targets.yaml       Moon and Mars targets

Outputs (``python -m analog_finder reference``)
  data/reference/targets.geojson         targets as points, for the map
  data/reference/known_analogs.geojson   analog sites as points, for the map
  data/processed/analogs_grid.csv        grid cell and ready grid features at each analog site

Known analogs are used to validate the ranking, never to train it.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from .. import config
from . import grid as grid_mod

ANALOG_COLUMNS = ("id", "name", "name_uk", "country", "lat", "lon", "world", "tasks", "kind", "validate",
                  "used_by", "coord_quality", "coord_source", "use_source", "use_checked", "notes")
WORLDS = ("moon", "mars", "both")
COORD_QUALITY = ("verified", "approx")


def _split(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def analogs_path() -> Path:
    return config.reference_dir() / "known_analogs.csv"


def read_analogs(path: str | Path | None = None, validate_only: bool = False) -> list[dict]:
    """Rows of known_analogs.csv: lat/lon as floats, tasks and kind as lists, yes/no as booleans."""
    path = Path(path) if path else analogs_path()
    out = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            row = {k: (v or "").strip() for k, v in raw.items() if k}
            row["lat"] = float(row["lat"])
            row["lon"] = float(row["lon"])
            row["tasks"] = _split(row.get("tasks", ""))
            row["kind"] = _split(row.get("kind", ""))
            row["validate"] = row.get("validate", "").lower() == "yes"
            row["use_checked"] = row.get("use_checked", "").lower() == "yes"
            if validate_only and not row["validate"]:
                continue
            out.append(row)
    return out


def check_analogs(rows: Iterable[dict]) -> list[str]:
    """Problems in the analog table (empty list when it is consistent)."""
    task_ids = {t["id"] for t in config.tasks()["tasks"]}
    problems, seen = [], set()
    for r in rows:
        rid = r.get("id", "?")
        if not rid or rid in seen:
            problems.append(f"{rid}: empty or duplicate id")
        seen.add(rid)
        if not (-90.0 <= r["lat"] <= 90.0 and -180.0 <= r["lon"] <= 180.0):
            problems.append(f"{rid}: coordinates out of range ({r['lat']}, {r['lon']})")
        if r.get("world") not in WORLDS:
            problems.append(f"{rid}: world must be one of {WORLDS}")
        if r.get("coord_quality") not in COORD_QUALITY:
            problems.append(f"{rid}: coord_quality must be one of {COORD_QUALITY}")
        if r.get("coord_quality") == "verified" and not r.get("coord_source"):
            problems.append(f"{rid}: verified coordinates need coord_source")
        unknown = [t for t in r["tasks"] if t not in task_ids]
        if unknown:
            problems.append(f"{rid}: unknown task ids {unknown}")
        if r["validate"] and not r["tasks"]:
            problems.append(f"{rid}: a validation site needs at least one task")
    return problems


def _feature(lon: float, lat: float, props: dict) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": props}


def analogs_geojson(rows: Iterable[dict]) -> dict:
    feats = []
    for r in rows:
        props = {k: r[k] for k in ("id", "name", "name_uk", "country", "world", "tasks", "kind", "validate",
                                   "used_by", "coord_quality", "coord_source", "use_source", "use_checked", "notes")}
        feats.append(_feature(r["lon"], r["lat"], props))
    return {"type": "FeatureCollection", "name": "known_analogs",
            "note": "Generated from data/reference/known_analogs.csv; edit the CSV, not this file.",
            "features": feats}


def targets_geojson() -> dict:
    """Targets as points. Longitude is converted from 0..360 east to -180..180 for map libraries.

    Coordinates are planetocentric on the Moon or Mars, not on Earth: draw each world on its own map.
    """
    cfg = config.targets()
    defaults = cfg.get("defaults", {})
    feats = []
    for t in cfg["targets"]:
        lon180 = ((float(t["lon_e"]) + 180.0) % 360.0) - 180.0
        props = {
            "id": t["id"], "world": t["world"], "name": t["name"], "name_uk": t.get("name_uk", ""),
            "role": t.get("role", ""), "mvp": bool(t.get("mvp", False)),
            "lat": float(t["lat"]), "lon_e": float(t["lon_e"]),
            "radius_km": float(t.get("radius_km", defaults.get(t["world"], {}).get("radius_km", 0))),
            "coord_quality": t.get("coord_quality", ""), "note": " ".join(str(t.get("note", "")).split()),
            "source": t.get("source", ""),
        }
        feats.append(_feature(lon180, float(t["lat"]), props))
    return {"type": "FeatureCollection", "name": "targets",
            "note": "Generated from pipeline/config/targets.yaml; edit the YAML, not this file. "
                    "Coordinates are on the Moon or Mars (see properties.world), longitude east, -180..180.",
            "features": feats}


def analogs_on_grid(rows: Iterable[dict], processed_dir: str | Path | None = None) -> list[dict]:
    """Grid cell and the ready grid features at each analog site.

    A site is ``in_grid`` when its cell is a land cell of the exported grid.
    """
    from ..export import to_binary

    meta, index, feats = to_binary.read_grid(processed_dir or config.processed_dir())
    cell_deg = meta["grid"]["cell_deg"]
    n_lon = meta["grid"]["n_lon"]
    out = []
    for r in rows:
        row, col = grid_mod.cell_of(r["lat"], r["lon"], cell_deg)
        flat = row * n_lon + col
        k = int(np.searchsorted(index, flat))
        inside = k < index.size and int(index[k]) == flat
        rec = {"id": r["id"], "name": r["name"], "world": r["world"], "validate": "yes" if r["validate"] else "no",
               "lat": r["lat"], "lon": r["lon"], "cell_row": row, "cell_col": col,
               "cell_index": k if inside else "", "in_grid": "yes" if inside else "no"}
        for name, values in feats.items():
            v = float(values[k]) if inside else float("nan")
            if not np.isfinite(v):
                rec[name] = ""
            elif name == "lowsun_best_month":
                rec[name] = int(round(v))
            else:
                rec[name] = round(v, 3)
        out.append(rec)
    return out


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def write_reference(log: Callable[[str], None] = print) -> list[Path]:
    """Write the GeoJSON layers and, when the grid exists, the analog-grid table."""
    written = []
    ref = config.reference_dir()

    path = ref / "targets.geojson"
    gj = targets_geojson()
    _write_json(path, gj)
    log(f"{len(gj['features'])} targets -> {path}")
    written.append(path)

    if not analogs_path().exists():
        log(f"{analogs_path()} is missing: analog layers skipped")
        return written
    rows = read_analogs()
    problems = check_analogs(rows)
    for p in problems:
        log(f"  problem: {p}")
    if problems:
        raise ValueError(f"known_analogs.csv has {len(problems)} problem(s), see above")

    path = ref / "known_analogs.geojson"
    _write_json(path, analogs_geojson(rows))
    log(f"{len(rows)} known analogs -> {path}")
    written.append(path)

    grid_json = config.processed_dir() / "grid.json"
    if grid_json.exists():
        table = analogs_on_grid(rows)
        path = config.processed_dir() / "analogs_grid.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(table)
        inside = sum(1 for t in table if t["in_grid"] == "yes")
        log(f"{inside} of {len(table)} analog sites fall on land cells of the grid -> {path}")
        written.append(path)
    else:
        log("data/processed/grid.json is missing: run `python -m analog_finder grid` to get analogs_grid.csv")
    return written
