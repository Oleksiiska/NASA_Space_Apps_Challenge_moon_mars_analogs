"""One command for the whole pipeline: ``python -m analog_finder all``.

Every step checks whether its result is already there and is skipped if so; ``--force STEP`` redoes it.
Without ``--fetch`` nothing is downloaded: a fresh clone of the repository has the processed grid,
so ``all`` then only builds the layers whose inputs are in the repository (volcanoes, impacts),
scores, validates and builds the web page. With ``--fetch`` missing downloads are made first
(the Earthdata step asks for your Earthdata Login).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable

from . import config

STEPS = ["fetch", "profiles", "grid", "terrain", "surface", "context", "merge", "score", "web"]


def _grid_features() -> set[str]:
    p = config.processed_dir() / "grid.json"
    if not p.exists():
        return set()
    return {f["name"] for f in json.loads(p.read_text(encoding="utf-8"))["features"]}


def _has_files(key: str, pattern: str) -> bool:
    d = config.resolve(config.dataset(key)["dest"])
    return d.exists() and any(d.glob(pattern))


def build_web(log: Callable[[str], None] = print) -> Path:
    script = config.project_root() / "webapp" / "build_app.py"
    spec = importlib.util.spec_from_file_location("build_app", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = config.project_root() / "webapp" / "index.html"
    mod.build(config.processed_dir(), out)
    return out


def run_all(force: list[str] | None = None, fetch: bool = False, log: Callable[[str], None] = print) -> int:
    force = set(force or [])
    if "all" in force:
        force = set(STEPS)
    unknown = force - set(STEPS)
    if unknown:
        log(f"Unknown step(s): {', '.join(sorted(unknown))}. Steps: {', '.join(STEPS)}")
        return 2
    built_layers = False

    def head(step: str, msg: str) -> None:
        log(f"\n== {step}: {msg}")

    # 1. downloads (only on request)
    if fetch or "fetch" in force:
        from .fetch import earth, pds
        head("fetch", "PDS (Moon, Mars), Natural Earth, volcano and impact lists, Earthdata")
        pds.fetch_world(None)
        pds.fetch_datasets(config.datasets(ids=["earth_naturalearth_land", "earth_naturalearth_roads",
                                                "earth_naturalearth_places", "earth_gvp_volcanoes", "earth_impact_structures"]))
        earth.fetch_earthdata(ids=["earth_srtmgl30", "earth_mod11c3", "earth_mod13c2", "earth_mod10cm", "earth_emit_l3asa",
                                   "earth_mcd12c1", "earth_imerg_monthly"])
    else:
        head("fetch", "skipped (add --fetch to download missing data)")

    feats = _grid_features()

    # 2. target fingerprints
    prof = config.processed_dir() / "target_profiles.json"
    if prof.exists() and "profiles" not in force:
        head("profiles", "done (target_profiles.json is there)")
    elif _has_files("moon_lola_polar_dem", "*.IMG") or _has_files("moon_lola_polar_dem", "*.img"):
        head("profiles", "computing")
        from .targets import profiles
        profiles.write_profiles()
    else:
        head("profiles", "cannot run: no PDS files. Run: python -m analog_finder fetch pds")
        return 1

    # 3. land grid and low-Sun features
    if (config.processed_dir() / "grid.bin").exists() and "grid" not in force:
        head("grid", "done (grid.bin is there)")
    else:
        head("grid", "building the land grid (about 3 minutes)")
        from . import build
        build.build_grid()
        feats = _grid_features()

    # 4. terrain from SRTM
    if "slope_h0" in feats and "terrain" not in force:
        head("terrain", "done (terrain features are in grid.bin)")
    elif _has_files("earth_srtmgl30", "*.zip"):
        head("terrain", "computing from SRTMGL30")
        from .features import earth_terrain
        earth_terrain.build_layer()
        built_layers = True
    else:
        head("terrain", "skipped: no SRTMGL30 tiles (fetch earth)")

    # 5. MODIS and EMIT
    if {"lst_day_mean_k", "ndvi_mean", "snow_free_months", "min_calcite", "snow_m01"} <= feats and "surface" not in force:
        head("surface", "done (temperature, NDVI, snow and minerals are in grid.bin)")
    elif {"lst_day_mean_k", "ndvi_mean", "snow_free_months", "min_calcite"} <= feats and "surface" not in force:
        head("surface", "adding the monthly snow cover (low-Sun calendar)")
        from .features import earth_surface
        built_layers |= bool(earth_surface.build_all(["snow"]))
    else:
        head("surface", "computing from MODIS and EMIT")
        from .features import earth_surface
        built_layers |= bool(earth_surface.build_all())

    # 6. volcanoes and impacts (features/context.py, from the lists in data/reference), roads (features/roads.py).
    #    Dryness comes from GPM IMERG in the surface step (earth_surface.build_precip).
    todo = []
    if not {"volcano_dist_km", "impact_dist_km"} <= feats or "context" in force:
        from .features import context
        head("context", "volcano and impact distances")
        context.build_layer()
        built_layers = True
        todo.append("gvp")
    if ("road_dist_km" not in feats or "context" in force) and _has_files("earth_naturalearth_roads", "ne_10m_roads.geojson"):
        from .features import roads
        head("context", "roads")
        roads.build_layer()
        built_layers = True
        todo.append("roads")
    if not todo:
        head("context", "done")

    # 7. merge
    if built_layers or "merge" in force:
        head("merge", "adding the new layers to grid.bin")
        from .prep import layers
        layers.merge_into_grid()
    else:
        head("merge", "nothing new to add")

    # 8. score and validation, 9. web page: always (seconds)
    head("score", "scoring, validation, export for the web page")
    from . import validate
    validate.run()
    head("web", "building webapp/index.html")
    out = build_web()
    log(f"\nDone. Open {out} in a browser.")
    return 0
