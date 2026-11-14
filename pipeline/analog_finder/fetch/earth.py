"""Earth data: Earthdata products (login), NASA POWER climatology, Copernicus DEM tiles.

Earthdata Login: this module never asks for, stores or prints credentials.
``earthaccess.login()`` reads them from the environment variables
EARTHDATA_USERNAME / EARTHDATA_PASSWORD, from ~/.netrc, or prompts you in your
own terminal. Create a free account at https://urs.earthdata.nasa.gov/.

MODIS CMG files are HDF4: read them with ``pyhdf`` (the rasterio wheel for
Windows has no HDF4 driver).
"""
from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

import requests

from .. import config
from .common import USER_AGENT, Result, download

# ----------------------------------------------------------------------------- Earthdata


def _granule_mb(g) -> float:
    """Size of a granule in MB. In earthaccess ``size`` is a method in some versions and a number in others."""
    try:
        size = g.size
        value = size() if callable(size) else size
        if value:
            return float(value)
    except Exception:
        pass
    try:      # fall back to the metadata record
        total = 0.0
        for item in g["umm"]["DataGranule"]["ArchiveAndDistributionInformation"]:
            if item.get("SizeInBytes"):
                total += float(item["SizeInBytes"]) / 1e6
            elif item.get("Size"):
                factor = {"B": 1e-6, "KB": 1e-3, "MB": 1.0, "GB": 1e3, "TB": 1e6}.get(str(item.get("SizeUnit", "MB")).upper(), 1.0)
                total += float(item["Size"]) * factor
        return total
    except Exception:
        return 0.0


def _search(earthaccess, ds: dict, year: int):
    """Search granules of one dataset. Falls back to a search without the version filter."""
    kw: dict = {"short_name": ds["short_name"]}
    temporal = ds.get("temporal", "none")
    if temporal == "year":
        kw["temporal"] = (f"{year}-01-01", f"{year}-12-31")
    version = ds.get("version")
    results = earthaccess.search_data(version=version, **kw) if version else earthaccess.search_data(**kw)
    note = ""
    if not results and version:
        results = earthaccess.search_data(**kw)
        if results:
            note = f"no granules for version {version}; used the versions returned by the search"
    if temporal == "latest" and results:
        def start(g):
            try:
                return g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
            except Exception:
                return ""
        results = [sorted(results, key=start)[-1]]
    return results, note


def fetch_earthdata(ids: Optional[list[str]] = None, year: int = 2023, dry_run: bool = False,
                    log: Callable[[str], None] = print, earthaccess=None) -> list[Result]:
    """Download the Earthdata products of config/sources.yaml with the earthaccess library."""
    if earthaccess is None:
        try:
            import earthaccess  # type: ignore
        except ImportError:
            log("earthaccess is not installed. Run: pip install earthaccess pyhdf")
            return [Result("earthaccess", "failed", 0, "library not installed")]
    datasets = config.datasets(world="earth", access="earthdata_login", ids=ids)
    if not dry_run:      # the search is public; only the download needs the login
        auth = earthaccess.login(persist=True)
        if not getattr(auth, "authenticated", True):
            log("Earthdata Login failed. Check the account at https://urs.earthdata.nasa.gov/")
            return [Result("earthdata_login", "failed", 0, "not authenticated")]
    results: list[Result] = []
    for ds in datasets:
        dest = config.resolve(ds["dest"])
        try:
            granules, note = _search(earthaccess, ds, year)
        except Exception as e:  # network or API error: report and continue with the next product
            log(f"[{ds['id']}] search failed: {e}")
            results.append(Result(ds["id"], "failed", 0, str(e)))
            continue
        size_mb = sum(_granule_mb(g) for g in granules)
        size_txt = f"about {size_mb:.0f} MB" if size_mb > 0 else "size not reported"
        log(f"[{ds['id']}] {ds['short_name']}: {len(granules)} granule(s), {size_txt} {note}")
        if not granules:
            results.append(Result(ds["id"], "failed", 0, f"no granules found for {year}; try another --year"))
            continue
        if dry_run:
            results.append(Result(ds["id"], "planned", int(size_mb * 1e6)))
            continue
        dest.mkdir(parents=True, exist_ok=True)
        try:
            files = earthaccess.download(granules, str(dest))
            results.append(Result(ds["id"], "downloaded", int(size_mb * 1e6), f"{len(files)} file(s) -> {dest}"))
        except Exception as e:
            log(f"[{ds['id']}] download failed: {e}")
            results.append(Result(ds["id"], "failed", 0, str(e)))
    return results


# ----------------------------------------------------------------------------- NASA POWER


def read_points(csv_path: str | Path) -> list[dict]:
    """Points from a CSV with columns id, lat, lon (extra columns are ignored)."""
    out = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:      # tolerate a BOM added by Excel
        for row in csv.DictReader(f):
            try:
                out.append({"id": row["id"], "lat": float(row["lat"]), "lon": float(row["lon"])})
            except (KeyError, ValueError):
                continue
    return out


def fetch_power(points: Iterable[dict], dry_run: bool = False, pause_s: float = 1.2,
                log: Callable[[str], None] = print, session=None) -> list[Result]:
    """Monthly climatology at points from the NASA POWER API (no login, up to 20 parameters)."""
    ds = config.dataset("earth_power_climatology")
    dest = config.resolve(ds["dest"])
    dest.mkdir(parents=True, exist_ok=True)
    s = session or requests.Session()
    results = []
    for p in points:
        out = dest / f"{p['id']}.json"
        if out.exists():
            results.append(Result(out.name, "present", out.stat().st_size))
            continue
        params = {"parameters": ",".join(ds["parameters"]), "community": ds["community"],
                  "longitude": f"{p['lon']:.4f}", "latitude": f"{p['lat']:.4f}", "format": "JSON"}
        if dry_run:
            log(f"  planned  {p['id']}  {ds['base_url']}?{requests.compat.urlencode(params)}")
            results.append(Result(out.name, "planned"))
            continue
        try:
            r = s.get(ds["base_url"], params=params, headers={"User-Agent": USER_AGENT}, timeout=(20, 120))
            r.raise_for_status()
            data = r.json()
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f)
            results.append(Result(out.name, "downloaded", out.stat().st_size))
            log(f"  ok   {p['id']}")
        except (requests.RequestException, ValueError) as e:
            results.append(Result(out.name, "failed", 0, str(e)))
            log(f"  ERR  {p['id']}: {e}")
        time.sleep(pause_s)
    return results


def power_annual(json_path: str | Path) -> dict:
    """Annual values of every parameter of one saved POWER response."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    params = data.get("properties", {}).get("parameter", {})
    return {name: months.get("ANN") for name, months in params.items()}


# ----------------------------------------------------------------------------- Copernicus DEM


def copdem_tile_name(lat: float, lon: float, arcsec: int = 30) -> str:
    """Folder/file stem of the 1 x 1 degree Copernicus DEM tile that holds a point.

    arcsec = 30 for GLO-90, 10 for GLO-30. Tiles are named by their south-west corner.
    """
    la, lo = math.floor(lat), math.floor(lon)
    ns = f"{'N' if la >= 0 else 'S'}{abs(la):02d}_00"
    ew = f"{'E' if lo >= 0 else 'W'}{abs(lo):03d}_00"
    return f"Copernicus_DSM_COG_{arcsec}_{ns}_{ew}_DEM"


def copdem_tiles_around(lat: float, lon: float, radius_deg: float = 0.5) -> list[tuple[int, int]]:
    """South-west corners of the tiles that touch a box around a point."""
    lats = range(math.floor(lat - radius_deg), math.floor(lat + radius_deg) + 1)
    scale = max(math.cos(math.radians(lat)), 0.05)
    lons = range(math.floor(lon - radius_deg / scale), math.floor(lon + radius_deg / scale) + 1)
    return [(la, ((lo + 180) % 360) - 180) for la in lats if -90 <= la < 90 for lo in lons]


def fetch_copdem(points: Iterable[dict], radius_deg: float = 0.5, dry_run: bool = False,
                 log: Callable[[str], None] = print, session=None) -> list[Result]:
    """Download Copernicus DEM GLO-90 tiles around points from the public AWS bucket (no login).

    A missing tile (HTTP 404) means open ocean: Copernicus publishes no tile there.
    """
    ds = config.dataset("earth_copdem_glo90")
    dest = config.resolve(ds["dest"])
    base = ds["base_url"].rstrip("/") + "/"
    wanted: dict[str, None] = {}
    for p in points:
        for la, lo in copdem_tiles_around(p["lat"], p["lon"], radius_deg):
            wanted[copdem_tile_name(la + 0.5, lo + 0.5)] = None
    results = []
    log(f"{len(wanted)} Copernicus DEM tile(s)")
    for stem in wanted:
        url = f"{base}{stem}/{stem}.tif"
        out = dest / f"{stem}.tif"
        if dry_run:
            log(f"  planned  {url}")
            results.append(Result(out.name, "planned"))
            continue
        r = download(url, out, log=log, session=session, retries=3)
        if not r.ok and "404" in r.message:
            r = Result(out.name, "skipped", 0, "no tile (open ocean)")
        log(f"  {'ok ' if r.ok else 'ERR'} {r.status:10s} {stem} {r.message}")
        results.append(r)
    return results
