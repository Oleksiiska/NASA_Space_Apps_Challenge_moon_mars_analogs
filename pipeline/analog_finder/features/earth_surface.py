"""Surface climate and mineral features of Earth cells: MODIS land temperature, NDVI, snow, EMIT minerals.

Every product is reduced to the land grid, 0.5 or 0.25 degrees (row 0 = 90 N, column 0 = 180 W); the text below
gives the numbers for 0.5 degrees, a 0.25 degree cell takes 5 x 5 MODIS pixels and repeats each EMIT cell 2 x 2:

* MODIS CMG products (MOD11C3, MOD13C2, MOD10CM) are 3600 x 7200 at 0.05 degrees, row 0 at 90 N. A cell is the mean of
  10 x 10 valid pixels (at least 30 % must be valid). One file per month; annual statistics need at least 6 valid months.
* EMIT L3 ASA is 220 x 690 at 0.5 degrees, but its cell centres lie on multiples of 0.5 (55.0, 54.5, ...), a quarter of a
  cell away from our centres. Each of our cells is the mean of the 2 x 2 EMIT cells around its centre (at least 2 valid).
  EMIT covers only 55 N to 54.5 S and only bare, dust-source surfaces; elsewhere the mineral features stay empty.
  (The file's GeoTransform puts the top edge at 54.75, the lat vector at 55.0; the vector is used, the lon vector agrees
  with the GeoTransform.)

Polar night leaves winter months without LST or snow values; means over the remaining months are therefore warm-biased
for cells above about 60 degrees, and that is stated in the feature descriptions.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..prep import layers

CELL_DEG = 0.5
MIN_MONTHS = 6
MIN_FRAC = 0.3          # share of valid 0.05 degree pixels inside a 0.5 degree cell

_DOY = re.compile(r"\.A(\d{4})(\d{3})\.")


# --------------------------------------------------------------------------- helpers

def month_of(name: str) -> int:
    """Month (1-12) of a MODIS monthly file name such as MOD11C3.A2023182.061....hdf (A + year + day of year)."""
    m = _DOY.search(Path(name).name)
    if not m:
        raise ValueError(f"{name}: not a MODIS file name (expected ...A2023182...)")
    return (date(int(m.group(1)), 1, 1) + timedelta(days=int(m.group(2)) - 1)).month


def read_sds(path: str | Path, name: str) -> np.ndarray:
    """One scientific dataset of an HDF4 file as a raw numpy array (pyhdf)."""
    try:
        from pyhdf.SD import SD, SDC
    except ImportError as e:
        raise ImportError("pyhdf is not installed. Run: pip install pyhdf") from e
    sd = SD(str(path), SDC.READ)
    try:
        if name not in sd.datasets():
            raise KeyError(f"{Path(path).name}: no dataset {name!r}; has {sorted(sd.datasets())}")
        return sd.select(name)[:]
    finally:
        sd.end()


def block_mean(a: np.ndarray, n: int = 10, min_frac: float = MIN_FRAC) -> np.ndarray:
    """Mean of n x n blocks ignoring NaN; NaN where fewer than min_frac of the pixels are valid."""
    rows, cols = a.shape
    if rows % n or cols % n:
        raise ValueError(f"shape {a.shape} is not a multiple of {n}")
    r = a.reshape(rows // n, n, cols // n, n)
    valid = np.isfinite(r)
    cnt = valid.sum(axis=(1, 3))
    tot = np.where(valid, r, 0.0).sum(axis=(1, 3), dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (tot / cnt).astype(np.float32)
    out[cnt < min_frac * n * n] = np.nan
    return out


def cell_at(arr: np.ndarray, lat: float, lon: float, cell_deg: Optional[float] = None) -> float:
    """Value of the grid cell that contains a point (the cell size follows from the array shape)."""
    cell_deg = cell_deg or 180.0 / arr.shape[0]
    r = int((90.0 - lat) / cell_deg)
    c = int((lon + 180.0) / cell_deg)
    return float(arr[min(max(r, 0), arr.shape[0] - 1), min(max(c, 0), arr.shape[1] - 1)])


def _monthly_files(src: Path, pattern: str) -> dict[int, Path]:
    files: dict[int, Path] = {}
    for p in sorted(src.glob(pattern)):
        files.setdefault(month_of(p.name), p)       # one file per month; the first one wins
    return files


def _stack(monthly: dict[int, np.ndarray]) -> np.ndarray:
    return np.stack([monthly[m] for m in sorted(monthly)])


def _reduce(stack: np.ndarray, fn, min_months: Optional[int] = None) -> np.ndarray:
    """fn over the month axis ignoring NaN; NaN where fewer than min_months months have a value."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = fn(stack, axis=0).astype(np.float32)
    out[np.isfinite(stack).sum(axis=0) < (MIN_MONTHS if min_months is None else min_months)] = np.nan
    return out


def _item(name: str, values: np.ndarray, vmin: float, vmax: float, unit: str, desc: str, source: str) -> layers.LayerFeature:
    return layers.LayerFeature(name, values, vmin, vmax, unit=unit, description=desc, source=source)


def _dir(key: str, src_dir: Optional[Path]) -> Path:
    from .. import config
    return Path(src_dir) if src_dir else config.resolve(config.dataset(key)["dest"])


def _check(problems: list[str], what: str, arr: np.ndarray, lat: float, lon: float, ok: Callable[[float], bool], label: str) -> None:
    v = cell_at(arr, lat, lon)
    if not np.isfinite(v) or not ok(v):
        problems.append(f"{what}: {label} ({lat}, {lon}) has {v:.3g}, which is not plausible")


def _fail(problems: list[str], product: str) -> None:
    if problems:
        raise RuntimeError(f"{product} self-check failed, the files are read wrongly:\n  " + "\n  ".join(problems))


# --------------------------------------------------------------------------- land surface temperature

LST_SOURCE = "NASA MOD11C3 v061 (EOSDIS LP DAAC), monthly 2023, computed by features/earth_surface.py"
_POLAR = " Above about 60 degrees the polar-night months are missing, so the mean is warm-biased there."


def lst_features(day: dict[int, np.ndarray], night: dict[int, np.ndarray]) -> dict[str, np.ndarray]:
    """Annual statistics from monthly 0.5 degree day and night temperatures in K (month -> array)."""
    d, n = _stack(day), _stack(night)
    both = np.where(np.isfinite(d) & np.isfinite(n), d - n, np.nan)
    return {
        "lst_day_mean_k": _reduce(d, np.nanmean),
        "lst_night_mean_k": _reduce(n, np.nanmean),
        "lst_day_max_k": _reduce(d, np.nanmax),
        "lst_night_min_k": _reduce(n, np.nanmin),
        "lst_diurnal_k": _reduce(both, np.nanmean),
    }


LST_SPEC = {
    "lst_day_mean_k": (200.0, 340.0, "K", "Mean daytime land surface temperature over the year (MODIS, clear sky)." + _POLAR),
    "lst_night_mean_k": (200.0, 320.0, "K", "Mean night-time land surface temperature over the year (MODIS, clear sky)." + _POLAR),
    "lst_day_max_k": (220.0, 340.0, "K", "Hottest monthly mean daytime temperature."),
    "lst_night_min_k": (190.0, 310.0, "K", "Coldest monthly mean night-time temperature." + _POLAR),
    "lst_diurnal_k": (0.0, 40.0, "K", "Mean day minus night temperature (day-night swing), months with both values."),
}


def _cells(cell_deg: Optional[float]) -> tuple[float, int]:
    """(cell size, 0.05 degree pixels per cell side) for the grid in data/processed."""
    cd = cell_deg or layers.grid_cell_deg()
    n = int(round(cd / 0.05))
    if abs(n * 0.05 - cd) > 1e-9:
        raise ValueError(f"cell size {cd} is not a multiple of the 0.05 degree MODIS pixels")
    return cd, n


def build_lst(src_dir: Optional[Path] = None, log: Callable[[str], None] = print, cell_deg: Optional[float] = None) -> Path:
    cd, nb = _cells(cell_deg)
    src = _dir("earth_mod11c3", src_dir)
    files = _monthly_files(src, "MOD11C3.*.hdf")
    if len(files) < MIN_MONTHS:
        raise FileNotFoundError(f"{len(files)} MOD11C3 monthly files in {src}, need at least {MIN_MONTHS}. "
                                "Run: python -m analog_finder fetch earth --only earth_mod11c3")
    day: dict[int, np.ndarray] = {}
    night: dict[int, np.ndarray] = {}
    for m, p in sorted(files.items()):
        for store, sds in ((day, "LST_Day_CMG"), (night, "LST_Night_CMG")):
            raw = read_sds(p, sds)
            k = np.where(raw >= 7500, raw * 0.02, np.nan).astype(np.float32)      # valid_range 7500..65535, scale 0.02
            store[m] = block_mean(k, nb)
        log(f"  month {m:2d}: {p.name}")
    feats = lst_features(day, night)
    problems: list[str] = []
    _check(problems, "LST", feats["lst_day_mean_k"], 25.0, 10.0, lambda v: v > 295, "Sahara daytime mean")
    _check(problems, "LST", feats["lst_day_mean_k"], 72.0, -40.0, lambda v: v < 270, "Greenland daytime mean")
    _check(problems, "LST", feats["lst_day_mean_k"], -3.0, -60.0, lambda v: 290 < v < 315, "Amazon daytime mean")
    _check(problems, "LST", feats["lst_diurnal_k"], 25.0, 10.0, lambda v: v > 10, "Sahara day-night swing")
    _fail(problems, "LST")
    log("LST self-check: ok (Sahara hot, Greenland cold, Amazon warm)")
    items = [_item(k, feats[k], *LST_SPEC[k], LST_SOURCE) for k in LST_SPEC]
    return layers.save_layer("earth_lst", items, cd)


# --------------------------------------------------------------------------- vegetation

NDVI_SOURCE = "NASA MOD13C2 v061 (EOSDIS LP DAAC), monthly 2023, computed by features/earth_surface.py"
NDVI_SDS = "CMG 0.05 Deg Monthly NDVI"
NDVI_SPEC = {
    "ndvi_mean": (-0.2, 0.9, "index", "Mean monthly NDVI over the year (greenness; below 0.1 is bare ground, rock, snow or ice)."),
    "ndvi_max": (-0.2, 0.9, "index", "Greenest monthly NDVI of the year."),
}


def ndvi_features(monthly: dict[int, np.ndarray]) -> dict[str, np.ndarray]:
    s = _stack(monthly)
    return {"ndvi_mean": _reduce(s, np.nanmean), "ndvi_max": _reduce(s, np.nanmax)}


def build_ndvi(src_dir: Optional[Path] = None, log: Callable[[str], None] = print, cell_deg: Optional[float] = None) -> Path:
    cd, nb = _cells(cell_deg)
    src = _dir("earth_mod13c2", src_dir)
    files = _monthly_files(src, "MOD13C2.*.hdf")
    if len(files) < MIN_MONTHS:
        raise FileNotFoundError(f"{len(files)} MOD13C2 monthly files in {src}, need at least {MIN_MONTHS}. "
                                "Run: python -m analog_finder fetch earth --only earth_mod13c2")
    monthly: dict[int, np.ndarray] = {}
    for m, p in sorted(files.items()):
        raw = read_sds(p, NDVI_SDS).astype(np.float32)
        v = np.where((raw > -2999) & (raw >= -2000) & (raw <= 10000), raw / 10000.0, np.nan).astype(np.float32)   # fill -3000
        monthly[m] = block_mean(v, nb)
        log(f"  month {m:2d}: {p.name}")
    feats = ndvi_features(monthly)
    problems: list[str] = []
    _check(problems, "NDVI", feats["ndvi_mean"], 25.0, 10.0, lambda v: v < 0.2, "Sahara")
    _check(problems, "NDVI", feats["ndvi_mean"], -3.0, -60.0, lambda v: v > 0.4, "Amazon")
    _fail(problems, "NDVI")
    log("NDVI self-check: ok (Sahara bare, Amazon green)")
    items = [_item(k, feats[k], *NDVI_SPEC[k], NDVI_SOURCE) for k in NDVI_SPEC]
    return layers.save_layer("earth_ndvi", items, cd)


# --------------------------------------------------------------------------- snow

SNOW_SOURCE = "NASA MOD10CM v061 (NSIDC DAAC), monthly 2023, computed by features/earth_surface.py"
SNOW_SDS = "Snow_Cover_Monthly_CMG"
SNOW_FREE_BELOW = 10.0            # percent of the pixel covered by snow
SNOW_SPEC = {
    "snow_cover_pct": (0.0, 100.0, "percent", "Mean monthly snow cover over the months with a snow decision (MODIS). Polar-night months are missing."),
    "snow_free_months": (0.0, 12.0, "months", "Months with a snow decision and under 10 % snow cover (months without decision are not counted as free)."),
}


def snow_cover(raw: np.ndarray) -> np.ndarray:
    """0-100 percent as float, NaN for the codes 211 night, 250 cloud, 253 no decision, 254 water, 255 fill."""
    return np.where(raw <= 100, raw, np.nan).astype(np.float32)


def snow_features(monthly: dict[int, np.ndarray]) -> dict[str, np.ndarray]:
    s = _stack(monthly)
    with np.errstate(invalid="ignore"):
        free = (np.isfinite(s) & (s < SNOW_FREE_BELOW)).sum(axis=0).astype(np.float32)
    free[np.isfinite(s).sum(axis=0) < MIN_MONTHS] = np.nan
    out = {"snow_cover_pct": _reduce(s, np.nanmean), "snow_free_months": free}
    for m in range(1, 13):                       # monthly cover for the low-Sun calendar; NaN = no decision that month
        out[f"snow_m{m:02d}"] = monthly[m].astype(np.float32) if m in monthly else np.full(s.shape[1:], np.nan, np.float32)
    return out


SNOW_MONTH_SPEC = {f"snow_m{m:02d}": (0.0, 100.0, "percent", f"Snow cover in month {m} of 2023 (MODIS); missing in polar night and under cloud")
                   for m in range(1, 13)}


def build_snow(src_dir: Optional[Path] = None, log: Callable[[str], None] = print, cell_deg: Optional[float] = None) -> Path:
    cd, nb = _cells(cell_deg)
    src = _dir("earth_mod10cm", src_dir)
    files = _monthly_files(src, "MOD10CM.*.hdf")
    if len(files) < MIN_MONTHS:
        raise FileNotFoundError(f"{len(files)} MOD10CM monthly files in {src}, need at least {MIN_MONTHS}. "
                                "Run: python -m analog_finder fetch earth --only earth_mod10cm")
    monthly: dict[int, np.ndarray] = {}
    for m, p in sorted(files.items()):
        monthly[m] = block_mean(snow_cover(read_sds(p, SNOW_SDS)), nb)
        log(f"  month {m:2d}: {p.name}")
    feats = snow_features(monthly)
    problems: list[str] = []
    _check(problems, "Snow", feats["snow_cover_pct"], 72.0, -40.0, lambda v: v > 80, "Greenland")
    _check(problems, "Snow", feats["snow_cover_pct"], 25.0, 10.0, lambda v: v < 2, "Sahara")
    _check(problems, "Snow", feats["snow_free_months"], 25.0, 10.0, lambda v: v >= 11, "Sahara snow-free months")
    _fail(problems, "Snow")
    log("Snow self-check: ok (Greenland snowy, Sahara free)")
    spec = {**SNOW_SPEC, **SNOW_MONTH_SPEC}
    items = [_item(k, feats[k], *spec[k], SNOW_SOURCE) for k in spec]
    return layers.save_layer("earth_snow", items, cd)


# --------------------------------------------------------------------------- EMIT minerals

EMIT_SOURCE = "NASA EMIT L3 ASA v002 (EOSDIS LP DAAC), computed by features/earth_surface.py"
EMIT_MINERALS = {          # variable in the file -> (feature name, label)
    "Calcite": ("min_calcite", "calcite"), "Chlorite": ("min_chlorite", "chlorite"), "Dolomite": ("min_dolomite", "dolomite"),
    "Goethite": ("min_goethite", "goethite"), "Gypsum": ("min_gypsum", "gypsum"), "Hematite": ("min_hematite", "hematite"),
    "Illite+Muscovite": ("min_illite_muscovite", "illite and muscovite"), "Kaolinite": ("min_kaolinite", "kaolinite"),
    "Montmorillonite": ("min_montmorillonite", "montmorillonite"), "Vermiculite": ("min_vermiculite", "vermiculite"),
    "Quartz+Feldspar": ("min_quartz_feldspar", "quartz and feldspar"),
}


def emit_to_grid(a: np.ndarray, lat: np.ndarray, lon: np.ndarray, n_lat: int = 360, n_lon: int = 720) -> np.ndarray:
    """EMIT 0.5 degree cells centred on multiples of 0.5 -> our cells (centres at .25 / .75), mean of the 2 x 2 around each centre.

    ``a`` is (len(lat), len(lon)) with NaN for no data. Cells with fewer than 2 valid EMIT cells stay NaN.
    """
    k = np.rint((90.0 - np.asarray(lat, dtype=np.float64)) / 0.5).astype(int)           # frame row: lat = 90 - 0.5 k
    m = np.rint((np.asarray(lon, dtype=np.float64) + 180.0) / 0.5).astype(int)          # frame col: lon = -180 + 0.5 m
    if k.min() < 0 or k.max() > n_lat or m.min() < 0 or m.max() > n_lon:
        raise ValueError("EMIT coordinates fall outside the global frame")
    frame = np.full((n_lat + 1, n_lon + 1), np.nan, dtype=np.float32)
    frame[np.ix_(k, m)] = a
    frame[:, 0] = np.where(np.isfinite(frame[:, 0]), frame[:, 0], frame[:, n_lon])      # lon 180 = lon -180
    frame[:, n_lon] = frame[:, 0]
    q = np.stack([frame[:-1, :-1], frame[:-1, 1:], frame[1:, :-1], frame[1:, 1:]])
    valid = np.isfinite(q)
    cnt = valid.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (np.where(valid, q, 0.0).sum(axis=0, dtype=np.float64) / cnt).astype(np.float32)
    out[cnt < 2] = np.nan
    return out


def upsample(a: np.ndarray, factor: int) -> np.ndarray:
    """Repeat every cell ``factor`` x ``factor`` times (EMIT stays a 0.5 degree product on a finer grid)."""
    return a if factor == 1 else np.repeat(np.repeat(a, factor, axis=0), factor, axis=1)


def build_emit(src_dir: Optional[Path] = None, log: Callable[[str], None] = print, cell_deg: Optional[float] = None) -> Path:
    cd = cell_deg or layers.grid_cell_deg()
    factor = int(round(0.5 / cd))
    if abs(factor * cd - 0.5) > 1e-9:
        raise ValueError(f"cell size {cd} does not divide the 0.5 degree EMIT cells")
    try:
        import netCDF4
    except ImportError as e:
        raise ImportError("netCDF4 is not installed. Run: pip install netCDF4") from e
    src = _dir("earth_emit_l3asa", src_dir)
    paths = sorted(src.glob("EMIT_L3_ASA*.nc"))
    if not paths:
        raise FileNotFoundError(f"No EMIT_L3_ASA*.nc in {src}. Run: python -m analog_finder fetch earth --only earth_emit_l3asa")
    ds = netCDF4.Dataset(str(paths[0]))
    try:
        lat = np.asarray(ds["lat"][:], dtype=np.float64)
        lon = np.asarray(ds["lon"][:], dtype=np.float64)
        if not (np.allclose(np.diff(lat), -0.5) and np.allclose(np.diff(lon), 0.5)):
            raise ValueError(f"{paths[0].name}: lat/lon vectors are not regular 0.5 degree steps (north to south, west to east)")
        grids = {}
        for var, (name, _) in EMIT_MINERALS.items():
            raw = np.ma.filled(ds[var][:].astype(np.float32), np.nan)
            raw[raw < -9000] = np.nan
            grids[name] = upsample(emit_to_grid(raw, lat, lon), factor)
    finally:
        ds.close()
    problems: list[str] = []
    _check(problems, "EMIT", grids["min_quartz_feldspar"], 25.0, 10.0, lambda v: v > 0.4, "Sahara quartz and feldspar")
    if np.isfinite(cell_at(grids["min_quartz_feldspar"], 0.25, -30.0)):
        problems.append("EMIT: an open-ocean cell (0.25, -30.0) has a mineral value, the grid is shifted")
    _fail(problems, "EMIT")
    covered = int(np.isfinite(grids["min_quartz_feldspar"]).sum())
    log(f"EMIT self-check: ok ({covered} cells with mineral abundances)")
    items = []
    for var, (name, label) in EMIT_MINERALS.items():
        g = grids[name]
        top = float(np.nanmax(g)) if np.isfinite(g).any() else 1.0
        vmax = min(1.0, float(np.ceil(top * 100) / 100))
        items.append(_item(name, g, 0.0, max(vmax, 0.01), "fraction",
                           f"Surface abundance of {label} from EMIT imaging spectroscopy (bare surfaces between 55 N and 54.5 S only).",
                           EMIT_SOURCE))
    return layers.save_layer("earth_emit", items, cd)


BUILDERS = {"lst": build_lst, "ndvi": build_ndvi, "snow": build_snow, "emit": build_emit}


def build_all(which: Optional[list[str]] = None, log: Callable[[str], None] = print) -> list[Path]:
    """Build the chosen products (default all); a product whose files are missing is reported and skipped."""
    out = []
    for key in which or list(BUILDERS):
        if key not in BUILDERS:
            raise ValueError(f"unknown product {key!r}; choose from {sorted(BUILDERS)}")
        log(f"{key}:")
        try:
            out.append(BUILDERS[key](log=log))
        except (FileNotFoundError, ImportError) as e:
            log(f"  skipped: {e}")
    return out
