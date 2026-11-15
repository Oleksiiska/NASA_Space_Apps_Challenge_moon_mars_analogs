"""Command line: python -m analog_finder <command>

  sources                 list datasets and what is already on disk
  fetch pds|moon|mars     download Moon and Mars files from NASA PDS (no login)
  fetch aux               download the Natural Earth land mask, roads, places and the volcano and impact tables
  fetch context           download the current volcano list (Smithsonian GVP) and the impact structure list
  fetch power-grid        NASA POWER precipitation for every land box (alternative dryness; no login, about an hour)
  fetch earth             download Earthdata products (asks for your Earthdata Login)
  fetch power             NASA POWER climatology for the points of a CSV
  fetch copdem            Copernicus DEM tiles around the points of a CSV
  check                   verify the size of every downloaded PDS file
  grid                    build the Earth land grid and the low-Sun features
  profiles                compute the Moon and Mars target fingerprints
  reference               write the map layers of targets and known analogs
  terrain                 terrain features of Earth cells from the SRTMGL30 tiles
  surface                 temperature, NDVI, snow and mineral layers from MODIS and EMIT
  context                 volcano and impact distances (GVP, impact list); --only adds road and alternative layers
  merge                   add the computed Earth layers to data/processed/grid.bin
  score                   validate on known analogs, export the scores for the web page
  evaluate                metrics with confidence intervals, compared with a saved baseline
  web                     build webapp/index.html from data/processed
  all                     run every step that is not done yet, then score and build the page
  ml                      resemblance to the known analog sites (PU learning; needs scikit-learn)
  inspect FILE            show the variables inside an HDF4 / NetCDF file
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config


def _cmd_sources(args) -> int:
    print(f"Project root: {config.project_root()}\n")
    print(f"{'dataset':34s} {'access':16s} {'files':>5s} {'size':>10s}  on disk")
    for ds in config.sources()["datasets"]:
        files = ds.get("files", [])
        size = sum(f.get("bytes") or 0 for f in files)
        dest = config.resolve(ds["dest"])
        if files:
            have = sum(1 for f in files if (dest / f["name"]).exists())
            state = f"{have}/{len(files)}"
        else:
            n = len([p for p in dest.glob("*") if p.is_file()]) if dest.exists() else 0
            state = f"{n} file(s)"
        size_s = f"{size / 1e6:8.1f} MB" if size else "         -"
        print(f"{ds['id']:34s} {ds['access']:16s} {len(files):5d} {size_s}  {state}")
    return 0


def _cmd_fetch(args) -> int:
    what = args.what
    if what in ("pds", "moon", "mars"):
        from .fetch import pds
        world = None if what == "pds" else what
        results = pds.fetch_world(world, ids=args.only, dry_run=args.dry_run)
    elif what == "aux":
        from .fetch import pds
        results = pds.fetch_datasets(config.datasets(ids=["earth_naturalearth_land", "earth_volcanoes", "earth_impacts",
                                                           "earth_naturalearth_roads", "earth_naturalearth_places"]),
                                     dry_run=args.dry_run)
    elif what == "context":
        from .fetch import pds
        results = pds.fetch_datasets(config.datasets(ids=["earth_gvp_volcanoes", "earth_impact_structures"]), dry_run=args.dry_run)
    elif what == "power-grid":
        from .fetch import earth
        results = earth.fetch_power_grid(dry_run=args.dry_run)
    elif what == "earth":
        from .fetch import earth
        results = earth.fetch_earthdata(ids=args.only, year=args.year, dry_run=args.dry_run)
    elif what in ("power", "copdem"):
        from .fetch import earth
        points_csv = Path(args.points) if args.points else config.reference_dir() / "known_analogs.csv"
        points = earth.read_points(points_csv)
        print(f"{len(points)} point(s) from {points_csv}")
        if what == "power":
            results = earth.fetch_power(points, dry_run=args.dry_run)
        else:
            results = earth.fetch_copdem(points, radius_deg=args.radius_deg, dry_run=args.dry_run)
    else:  # pragma: no cover - argparse restricts the choices
        return 2
    failed = [r for r in results if not r.ok]
    return 1 if failed else 0


def _cmd_check(args) -> int:
    from .fetch import pds
    ok = pds.check()
    print("All PDS files are complete." if ok else "Some PDS files are missing or incomplete: run `python -m analog_finder fetch pds`.")
    return 0 if ok else 1


def _cmd_grid(args) -> int:
    from . import build
    build.build_grid(cell_deg=config.cell_deg(), min_land_frac=args.min_land_frac)
    from .prep import layers
    if layers.layers_dir().exists() and any(layers.layers_dir().glob("*.npz")):
        layers.merge_into_grid()
    return 0


def _cmd_profiles(args) -> int:
    from .targets import profiles
    profiles.write_profiles()
    return 0


def _cmd_reference(args) -> int:
    from .prep import reference
    reference.write_reference()
    return 0


def _cmd_terrain(args) -> int:
    from .features import earth_terrain
    path = earth_terrain.build_layer(cell_deg=args.cell_deg or config.cell_deg())
    print(f"Layer saved: {path}\nNext: python -m analog_finder merge")
    return 0


def _cmd_surface(args) -> int:
    from .features import earth_surface
    paths = earth_surface.build_all(args.only)
    if paths:
        print("Layers saved: " + ", ".join(p.name for p in paths) + "\nNext: python -m analog_finder merge")
    return 0


CONTEXT_DEFAULT = ["gvp"]


def _cmd_context(args) -> int:
    """``gvp``: our layer (features/context.py: volcano_dist_km, holocene_volcano_dist_km, impact_dist_km).
    ``volcanic``, ``impact``, ``dryness``, ``roads``: the layers of features/earth_context.py. Its ``impact`` layer writes
    impact_dist_km too, so build either ``gvp`` or ``impact``, not both."""
    which = list(args.only or CONTEXT_DEFAULT)
    if "gvp" in which and "impact" in which:
        print("gvp and impact both write impact_dist_km: choose one.")
        return 2
    paths = []
    if "gvp" in which:
        from .features import context
        paths.append(context.build_layer())
    rest = [w for w in which if w != "gvp"]
    if rest:
        from .features import earth_context
        paths += earth_context.build_all(rest)
    if paths:
        print("Layers saved: " + ", ".join(p.name for p in paths) + "\nNext: python -m analog_finder merge")
    return 0


def _cmd_ml(args) -> int:
    from .ml import pu
    pu.run(n_bags=args.bags, loso_bags=args.loso_bags)
    print("Layer saved: ml_pu.npz; report: data/processed/ml_report.md\nNext: python -m analog_finder merge, then web")
    return 0


def _cmd_web(args) -> int:
    from . import pipeline_all
    pipeline_all.build_web()
    return 0


def _cmd_all(args) -> int:
    from . import pipeline_all
    return pipeline_all.run_all(force=args.force, fetch=args.fetch)


def _cmd_score(args) -> int:
    from . import validate
    validate.run()
    return 0


def _cmd_evaluate(args) -> int:
    from . import evaluate
    evaluate.run(save_baseline=args.save_baseline, baseline=args.baseline, holdout=2 if args.holdout2 else int(args.holdout))
    return 0


def _cmd_merge(args) -> int:
    from .prep import layers
    layers.merge_into_grid()
    return 0


def _cmd_inspect(args) -> int:
    from .io import inspect
    for f in args.files:
        inspect.inspect_file(f)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analog_finder", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("sources", help="list datasets and local status").set_defaults(func=_cmd_sources)

    f = sub.add_parser("fetch", help="download data")
    f.add_argument("what", choices=["pds", "moon", "mars", "aux", "context", "earth", "power", "power-grid", "copdem"])
    f.add_argument("--dry-run", action="store_true", help="show what would be downloaded")
    f.add_argument("--only", nargs="+", metavar="DATASET_ID", help="restrict to these dataset ids")
    f.add_argument("--year", type=int, default=2023, help="year of the monthly Earth products (default 2023)")
    f.add_argument("--points", help="CSV with columns id, lat, lon (default: data/reference/known_analogs.csv)")
    f.add_argument("--radius-deg", type=float, default=0.5, help="half-size of the box around each point for copdem")
    f.set_defaults(func=_cmd_fetch)

    sub.add_parser("check", help="verify downloaded PDS files").set_defaults(func=_cmd_check)

    g = sub.add_parser("grid", help="build the Earth land grid and low-Sun features")
    g.add_argument("--min-land-frac", type=float, default=0.2)
    g.set_defaults(func=_cmd_grid)

    sub.add_parser("profiles", help="compute Moon and Mars target fingerprints").set_defaults(func=_cmd_profiles)
    sub.add_parser("reference", help="write GeoJSON layers of targets and known analogs").set_defaults(func=_cmd_reference)

    t = sub.add_parser("terrain", help="terrain features of Earth cells from SRTMGL30")
    t.add_argument("--cell-deg", type=float, default=None, help="default: ANALOG_CELL_DEG or 0.5")
    t.set_defaults(func=_cmd_terrain)
    sf = sub.add_parser("surface", help="temperature, NDVI, snow and mineral features from MODIS and EMIT")
    sf.add_argument("--only", nargs="+", choices=["lst", "ndvi", "snow", "emit", "landcover", "precip"], help="restrict to these products")
    sf.set_defaults(func=_cmd_surface)
    cx = sub.add_parser("context", help="volcano and impact distances; --only for road and alternative layers")
    cx.add_argument("--only", nargs="+", choices=["gvp", "volcanic", "impact", "dryness", "roads"],
                    help="layers to build (default: gvp)")
    cx.set_defaults(func=_cmd_context)
    sub.add_parser("web", help="build webapp/index.html from data/processed").set_defaults(func=_cmd_web)
    ml = sub.add_parser("ml", help="resemblance to the known analog sites (PU learning; needs scikit-learn)")
    ml.add_argument("--bags", type=int, default=40, help="bags of the final model")
    ml.add_argument("--loso-bags", type=int, default=20, help="bags per held-out site in the evaluation")
    ml.set_defaults(func=_cmd_ml)
    al = sub.add_parser("all", help="run every step that is not done yet, then score and build the page")
    al.add_argument("--fetch", action="store_true", help="also download missing data (PDS, Earthdata with login, POWER)")
    al.add_argument("--force", nargs="+", default=[], metavar="STEP", help="redo these steps even if done (or: all)")
    al.set_defaults(func=_cmd_all)
    sub.add_parser("score", help="validate the ranking on known analogs and export scores for the web app").set_defaults(func=_cmd_score)
    ev = sub.add_parser("evaluate", help="metrics of the ranking with confidence intervals; compare with a saved baseline")
    ev.add_argument("--save-baseline", action="store_true", help="store the current metrics as the baseline")
    ev.add_argument("--baseline", help="baseline file (default: data/processed/eval_baseline.json)")
    ev.add_argument("--holdout", action="store_true", help="score the hold-out sites (check a finished method, do not tune on them)")
    ev.add_argument("--holdout2", action="store_true", help="score the second hold-out set (holdout2_analogs.csv)")
    ev.set_defaults(func=_cmd_evaluate)
    sub.add_parser("merge", help="add computed Earth layers to grid.bin").set_defaults(func=_cmd_merge)
    i = sub.add_parser("inspect", help="show the variables inside an HDF4 / NetCDF file")
    i.add_argument("files", nargs="+")
    i.set_defaults(func=_cmd_inspect)

    args = p.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
