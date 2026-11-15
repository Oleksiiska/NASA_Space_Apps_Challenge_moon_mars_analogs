"""Surface climate and mineral features of Earth cells: MODIS land temperature, NDVI, snow, land cover, EMIT minerals.

Every product is reduced to the 0.5 degree grid (row 0 = 90 N, column 0 = 180 W, cell centres at .25 / .75):

* MODIS CMG products (MOD11C3, MOD13C2, MOD10CM, MCD12C1) are 3600 x 7200 at 0.05 degrees, row 0 at 90 N. A cell is the mean of
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

CELL_DEG = 0.5            # default; the grid in use is config.cell_deg()
MODIS_DEG = 0.05
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


def _cd() -> float:
    from .. import config
    return config.cell_deg()


def _n() -> int:
    """MODIS 0.05 degree pixels per cell side (10 for 0.5 degree cells, 5 for 0.25)."""
    n = int(round(_cd() / MODIS_DEG))
    if abs(n * MODIS_DEG - _cd()) > 1e-9:
        raise ValueError(f"cell size {_cd()} is not a multiple of {MODIS_DEG} degrees")
    return n


def cell_at(arr: np.ndarray, lat: float, lon: float, cell_deg: Optional[float] = None) -> float:
    """Value of the grid cell that contains a point (by default the cell size follows from the array shape)."""
    cell_deg = 180.0 / arr.shape[0] if cell_deg is None else cell_deg
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


def build_lst(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
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
            store[m] = block_mean(k, n=_n())
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
    return layers.save_layer("earth_lst", items, _cd())


# --------------------------------------------------------------------------- vegetation

NDVI_SOURCE = "NASA MOD13C2 v061 (EOSDIS LP DAAC), monthly 2023, computed by features/earth_surface.py"
NDVI_SDS = "CMG 0.05 Deg Monthly NDVI"
NDVI_SPEC = {
    "ndvi_mean": (-0.2, 0.9, "index", "Mean monthly NDVI over the year (greenness; below 0.1 is bare ground, rock, snow or ice)."),
    "ndvi_max": (-0.2, 0.9, "index", "Greenest monthly NDVI of the year."),
    "bare_px_frac": (0.0, 1.0, "fraction", "Share of the 0.05 degree (about 5 km) pixels of the cell whose annual mean NDVI is "
                                          "at most 0.25: a bare volcano or salt flat inside a green cell still counts."),
}
BARE_NDVI = 0.25          # the same threshold as the bare_ground_min filter


def bare_pixel_share(sum_: np.ndarray, cnt: np.ndarray, n: int = 10, min_months: int = MIN_MONTHS,
                     min_frac: float = MIN_FRAC, thr: float = BARE_NDVI) -> np.ndarray:
    """Share of pixels with annual mean NDVI <= thr in each n x n block, from per-pixel monthly sums and counts."""
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(cnt >= min_months, sum_ / np.maximum(cnt, 1), np.nan)
    valid = np.isfinite(mean)
    bare = valid & (mean <= thr)
    rows, cols = mean.shape
    v = valid.reshape(rows // n, n, cols // n, n).sum(axis=(1, 3))
    b = bare.reshape(rows // n, n, cols // n, n).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (b / v).astype(np.float32)
    out[v < min_frac * n * n] = np.nan
    return out


def ndvi_features(monthly: dict[int, np.ndarray]) -> dict[str, np.ndarray]:
    s = _stack(monthly)
    return {"ndvi_mean": _reduce(s, np.nanmean), "ndvi_max": _reduce(s, np.nanmax)}


def build_ndvi(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    src = _dir("earth_mod13c2", src_dir)
    files = _monthly_files(src, "MOD13C2.*.hdf")
    if len(files) < MIN_MONTHS:
        raise FileNotFoundError(f"{len(files)} MOD13C2 monthly files in {src}, need at least {MIN_MONTHS}. "
                                "Run: python -m analog_finder fetch earth --only earth_mod13c2")
    monthly: dict[int, np.ndarray] = {}
    px_sum = px_cnt = None
    for m, p in sorted(files.items()):
        raw = read_sds(p, NDVI_SDS).astype(np.float32)
        v = np.where((raw > -2999) & (raw >= -2000) & (raw <= 10000), raw / 10000.0, np.nan).astype(np.float32)   # fill -3000
        monthly[m] = block_mean(v, n=_n())
        ok = np.isfinite(v)
        if px_sum is None:
            px_sum, px_cnt = np.zeros(v.shape, np.float32), np.zeros(v.shape, np.uint8)
        px_sum += np.where(ok, v, 0.0)
        px_cnt += ok
        log(f"  month {m:2d}: {p.name}")
    feats = ndvi_features(monthly)
    feats["bare_px_frac"] = bare_pixel_share(px_sum, px_cnt, n=_n())
    problems: list[str] = []
    _check(problems, "NDVI", feats["ndvi_mean"], 25.0, 10.0, lambda v: v < 0.2, "Sahara")
    _check(problems, "NDVI", feats["ndvi_mean"], -3.0, -60.0, lambda v: v > 0.4, "Amazon")
    _fail(problems, "NDVI")
    log("NDVI self-check: ok (Sahara bare, Amazon green)")
    items = [_item(k, feats[k], *NDVI_SPEC[k], NDVI_SOURCE) for k in NDVI_SPEC]
    return layers.save_layer("earth_ndvi", items, _cd())


# --------------------------------------------------------------------------- snow

SNOW_SOURCE = "NASA MOD10CM v061 (NSIDC DAAC), monthly 2023, computed by features/earth_surface.py"
SNOW_SDS = "Snow_Cover_Monthly_CMG"
SNOW_FREE_BELOW = 10.0            # percent of the pixel covered by snow
SNOW_SPEC = {
    "snow_cover_pct": (0.0, 100.0, "percent", "Mean monthly snow cover over the months with a snow decision (MODIS). Polar-night months are missing."),
    "snow_free_months": (0.0, 12.0, "months", "Months with a snow decision and under 10 % snow cover (months without decision are not counted as free)."),
    "snowfree_px_frac": (0.0, 1.0, "fraction", "Share of the 0.05 degree (about 5 km) pixels of the cell with at least one "
                                              "snow-free month: snow-free lowland next to a glacier still counts."),
}


def snowfree_pixel_share(free_months: np.ndarray, valid: np.ndarray, n: int = 10, min_frac: float = MIN_FRAC) -> np.ndarray:
    """Share of pixels with at least one snow-free month among pixels with a snow decision, per n x n block."""
    rows, cols = free_months.shape
    v = valid.reshape(rows // n, n, cols // n, n).sum(axis=(1, 3))
    f = (valid & (free_months >= 1)).reshape(rows // n, n, cols // n, n).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (f / v).astype(np.float32)
    out[v < min_frac * n * n] = np.nan
    return out


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


def build_snow(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    src = _dir("earth_mod10cm", src_dir)
    files = _monthly_files(src, "MOD10CM.*.hdf")
    if len(files) < MIN_MONTHS:
        raise FileNotFoundError(f"{len(files)} MOD10CM monthly files in {src}, need at least {MIN_MONTHS}. "
                                "Run: python -m analog_finder fetch earth --only earth_mod10cm")
    monthly: dict[int, np.ndarray] = {}
    free_px = seen_px = None
    for m, p in sorted(files.items()):
        cover = snow_cover(read_sds(p, SNOW_SDS))
        monthly[m] = block_mean(cover, n=_n())
        if free_px is None:
            free_px, seen_px = np.zeros(cover.shape, np.uint8), np.zeros(cover.shape, np.uint8)
        with np.errstate(invalid="ignore"):
            free_px += np.isfinite(cover) & (cover < SNOW_FREE_BELOW)
        seen_px += np.isfinite(cover)
        log(f"  month {m:2d}: {p.name}")
    feats = snow_features(monthly)
    feats["snowfree_px_frac"] = snowfree_pixel_share(free_px, seen_px >= MIN_MONTHS, n=_n())
    problems: list[str] = []
    _check(problems, "Snow", feats["snow_cover_pct"], 72.0, -40.0, lambda v: v > 80, "Greenland")
    _check(problems, "Snow", feats["snow_cover_pct"], 25.0, 10.0, lambda v: v < 2, "Sahara")
    _check(problems, "Snow", feats["snow_free_months"], 25.0, 10.0, lambda v: v >= 11, "Sahara snow-free months")
    _fail(problems, "Snow")
    log("Snow self-check: ok (Greenland snowy, Sahara free)")
    spec = {**SNOW_SPEC, **SNOW_MONTH_SPEC}
    items = [_item(k, feats[k], *spec[k], SNOW_SOURCE) for k in spec]
    return layers.save_layer("earth_snow", items, _cd())


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


def emit_to_finer_grid(a: np.ndarray, lat: np.ndarray, lon: np.ndarray, cell_deg: float) -> np.ndarray:
    """EMIT 0.5 degree cells -> a finer grid: every fine cell takes the EMIT cell whose centre is nearest to its own."""
    n_lat0, n_lon0 = 360, 720
    k = np.rint((90.0 - np.asarray(lat, dtype=np.float64)) / 0.5).astype(int)
    m = np.rint((np.asarray(lon, dtype=np.float64) + 180.0) / 0.5).astype(int)
    frame = np.full((n_lat0 + 1, n_lon0 + 1), np.nan, dtype=np.float32)
    frame[np.ix_(k, m)] = a
    frame[:, 0] = np.where(np.isfinite(frame[:, 0]), frame[:, 0], frame[:, n_lon0])
    frame[:, n_lon0] = frame[:, 0]
    n_lat, n_lon = int(round(180 / cell_deg)), int(round(360 / cell_deg))
    lat_c = 90.0 - (np.arange(n_lat) + 0.5) * cell_deg
    lon_c = -180.0 + (np.arange(n_lon) + 0.5) * cell_deg
    rk = np.rint((90.0 - lat_c) / 0.5).astype(int)
    cm = np.rint((lon_c + 180.0) / 0.5).astype(int)
    return frame[np.ix_(rk, cm)]


def build_emit(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
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
            grids[name] = (emit_to_grid(raw, lat, lon) if abs(_cd() - 0.5) < 1e-9
                           else emit_to_finer_grid(raw, lat, lon, _cd()))
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
    return layers.save_layer("earth_emit", items, _cd())


# --------------------------------------------------------------------------- land cover

LC_SOURCE = "NASA MCD12C1 v061 (EOSDIS LP DAAC), IGBP classes, computed by features/earth_surface.py"
LC_SDS = "Land_Cover_Type_1_Percent"     # (3600, 7200, 17): percent of each IGBP class in a 0.05 degree pixel, from 500 m pixels
LC_WATER, LC_OPEN_SHRUB, LC_SNOW_ICE, LC_BARREN = 0, 7, 15, 16
LC_SPEC = {
    "barren_frac": (0.0, 1.0, "fraction", "Share of the cell's land that is barren ground at 500 m (IGBP class 16: rock, sand, "
                                          "bare soil, lava). Unlike mean NDVI it sees a bare patch inside a green cell."),
    "sparse_frac": (0.0, 1.0, "fraction", "Share of the cell's land that is barren or open shrubland (IGBP 16 and 7)."),
    "snow_ice_frac": (0.0, 1.0, "fraction", "Share of the cell's land under permanent snow and ice at 500 m (IGBP class 15)."),
}


def landcover_features(pct: np.ndarray, n: int = 10, min_frac: float = MIN_FRAC) -> dict[str, np.ndarray]:
    """Shares of the land of each n x n block from per-pixel class percentages (rows, cols, classes), 255 = fill.

    Each share is the sum of the class percent over the block divided by the sum of the land percent (100 - water), so a
    coastal cell is not diluted by sea. NaN where fewer than ``min_frac`` of the pixels are valid or the block has no land.
    """
    rows, cols, _ = pct.shape
    if rows % n or cols % n:
        raise ValueError(f"shape {pct.shape[:2]} is not a multiple of {n}")
    valid = pct[:, :, LC_WATER] != 255

    def block_sum(a: np.ndarray) -> np.ndarray:
        a = np.where(valid, a.astype(np.float32), 0.0)
        return a.reshape(rows // n, n, cols // n, n).sum(axis=(1, 3), dtype=np.float64)

    land = block_sum(100.0 - pct[:, :, LC_WATER].astype(np.float32))
    cnt = valid.reshape(rows // n, n, cols // n, n).sum(axis=(1, 3))
    bad = (cnt < min_frac * n * n) | (land <= 0)
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        barren = block_sum(pct[:, :, LC_BARREN])
        out["barren_frac"] = barren / land
        out["sparse_frac"] = (barren + block_sum(pct[:, :, LC_OPEN_SHRUB])) / land
        out["snow_ice_frac"] = block_sum(pct[:, :, LC_SNOW_ICE]) / land
    for k in out:
        v = np.clip(out[k], 0.0, 1.0).astype(np.float32)
        v[bad] = np.nan
        out[k] = v
    return out


def build_landcover(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    src = _dir("earth_mcd12c1", src_dir)
    paths = sorted(src.glob("MCD12C1.*.hdf"))
    if not paths:
        raise FileNotFoundError(f"No MCD12C1.*.hdf in {src}. Run: python -m analog_finder fetch earth --only earth_mcd12c1")
    path = paths[-1]                        # the most recent year
    log(f"  {path.name}")
    pct = read_sds(path, LC_SDS)
    if pct.ndim != 3 or pct.shape[:2] != (3600, 7200) or pct.shape[2] < 17:
        raise ValueError(f"{path.name}: {LC_SDS} has shape {pct.shape}, expected (3600, 7200, 17)")
    feats = landcover_features(pct, n=_n())
    problems: list[str] = []
    _check(problems, "Land cover", feats["barren_frac"], 25.0, 10.0, lambda v: v > 0.7, "Sahara barren")
    _check(problems, "Land cover", feats["barren_frac"], -3.0, -60.0, lambda v: v < 0.05, "Amazon barren")
    _check(problems, "Land cover", feats["snow_ice_frac"], 72.0, -40.0, lambda v: v > 0.7, "Greenland ice")
    _check(problems, "Land cover", feats["snow_ice_frac"], 25.0, 10.0, lambda v: v < 0.05, "Sahara ice")
    _fail(problems, "Land cover")
    log("Land cover self-check: ok (Sahara barren, Amazon not, Greenland ice)")
    items = [_item(k, feats[k], *LC_SPEC[k], LC_SOURCE) for k in LC_SPEC]
    return layers.save_layer("earth_landcover", items, _cd())


# --------------------------------------------------------------------------- precipitation

IMERG_SOURCE = "NASA GPM IMERG Final V07 monthly (GES DISC), computed by features/earth_surface.py"
IMERG_MIN_MONTHS = 10
IMERG_SPEC = {
    "precip_log_mm": (0.0, 4.0, "log10(1 + mm/year)",
                      "Annual precipitation on a log scale: 0 = none, 1 = 9 mm, 2 = 99 mm, 3 = 999 mm per year (GPM IMERG). "
                      "Stored as a log so that hyper-arid deserts (a few mm per year) stay apart."),
    "precip_min_log_mm": (0.0, 4.0, "log10(1 + mm/year)",
                          "Annual precipitation of the driest 0.1 degree (about 11 km) land pixel inside the cell, same log "
                          "scale: a salt basin is not hidden by the wetter hills around it."),
}


def read_imerg(path: str | Path) -> np.ndarray:
    """Monthly IMERG precipitation as a north-up (1800, 3600) array in mm/hour, NaN for fill.

    In the file the grid is (time, lon, lat) with latitude from south to north; it is transposed and flipped here so that
    row 0 is 90 N and column 0 is 180 W, like the MODIS CMG products.
    """
    try:
        import h5py
    except ImportError as e:
        raise ImportError("h5py is not installed. Run: pip install h5py") from e
    with h5py.File(str(path), "r") as f:
        lat = f["Grid/lat"][:]
        lon = f["Grid/lon"][:]
        pr = f["Grid/precipitation"][0].astype(np.float32)
    if pr.shape != (lon.size, lat.size) or not (lat[0] < lat[-1] and lon[0] < lon[-1]):
        raise ValueError(f"{Path(path).name}: unexpected IMERG layout {pr.shape}, lat {lat[0]}..{lat[-1]}, lon {lon[0]}..{lon[-1]}")
    pr[pr < 0] = np.nan
    return pr.T[::-1].copy()


def precip_features(monthly: dict[int, np.ndarray], year: int, n: int = 1,
                    land: Optional[np.ndarray] = None, up: int = 1) -> dict[str, np.ndarray]:
    """Annual precipitation from monthly mean rates (mm/hour); cells are n x n blocks of the input pixels.

    The annual total of a pixel is its mean rate over the valid months times the hours of the year; a pixel needs
    IMERG_MIN_MONTHS valid months. ``precip_log_mm`` is the block mean, ``precip_min_log_mm`` the driest pixel of the
    block; pixels where ``land`` is False (sea) are left out of the minimum when a mask is given. ``up`` repeats every
    pixel up x up times first (IMERG 0.1 degree -> 0.05, so that 0.25 degree cells are whole blocks).
    """
    hours = {m: (date(year + (m == 12), m % 12 + 1, 1) - date(year, m, 1)).days * 24 for m in monthly}
    s = _stack(monthly)
    w = np.array([hours[m] for m in sorted(monthly)], dtype=np.float64)[:, None, None]
    ok = np.isfinite(s)
    with np.errstate(invalid="ignore", divide="ignore"):
        annual = (np.where(ok, s * w, 0.0).sum(axis=0) / np.where(ok, w, 0.0).sum(axis=0) * sum(hours.values()))
    annual[ok.sum(axis=0) < IMERG_MIN_MONTHS] = np.nan
    if up > 1:
        annual = np.repeat(np.repeat(annual, up, axis=0), up, axis=1)
    mean = block_mean(annual.astype(np.float32), n=n) if n > 1 else annual
    a = annual.copy()
    if land is not None:
        a[~land] = np.nan
    rows, cols = a.shape
    blocks = a.reshape(rows // n, n, cols // n, n)
    with np.errstate(invalid="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            low = np.nanmin(blocks, axis=(1, 3))
    low = np.where(np.isfinite(low), low, mean)               # no land pixel with data: fall back to the mean
    log1 = lambda x: np.log10(1.0 + np.maximum(x, 0.0)).astype(np.float32)
    return {"precip_log_mm": log1(mean), "precip_min_log_mm": log1(low)}


def land_mask_005(src_dir: Optional[Path] = None) -> Optional[np.ndarray]:
    """North-up 0.05 degree land mask (3600, 7200) from MCD12C1 (water under 50 %), or None when the file is missing."""
    try:
        src = _dir("earth_mcd12c1", src_dir)
    except Exception:
        return None
    paths = sorted(src.glob("MCD12C1.*.hdf"))
    if not paths:
        return None
    water = read_sds(paths[-1], LC_SDS)[:, :, LC_WATER]
    return (water != 255) & (water < 50)


def build_precip(src_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> Path:
    src = _dir("earth_imerg_monthly", src_dir)
    files: dict[int, dict[int, Path]] = {}
    for p in sorted(src.glob("3B-MO.MS.MRG.3IMERG.*.HDF5")):
        m = re.search(r"\.(\d{4})(\d{2})01-S", p.name)
        if m:
            files.setdefault(int(m.group(1)), {})[int(m.group(2))] = p
    full = [y for y, ms in files.items() if len(ms) >= IMERG_MIN_MONTHS]
    if not full:
        raise FileNotFoundError(f"No year with at least {IMERG_MIN_MONTHS} IMERG monthly files in {src}. "
                                "Run: python -m analog_finder fetch earth --only earth_imerg_monthly --year 2023")
    year = max(full)
    monthly = {}
    for m, p in sorted(files[year].items()):
        monthly[m] = read_imerg(p)
        log(f"  month {m:2d}: {p.name}")
    land = land_mask_005()
    log("  driest pixel: " + ("land pixels only (MCD12C1 water mask)" if land is not None else
                              "no MCD12C1 file, sea pixels included"))
    feats = precip_features(monthly, year, n=_n(), land=land, up=2)
    annual = 10.0 ** feats["precip_log_mm"] - 1.0                 # mm per year
    problems: list[str] = []
    _check(problems, "Precipitation", annual, -24.0, -69.75, lambda v: v < 100, "Atacama, mm/year")
    _check(problems, "Precipitation", annual, 25.0, 10.0, lambda v: v < 100, "Sahara, mm/year")
    _check(problems, "Precipitation", annual, -3.0, -60.0, lambda v: v > 1500, "Amazon, mm/year")
    _fail(problems, "Precipitation")
    log(f"Precipitation self-check: ok (Atacama and Sahara dry, Amazon wet; year {year})")
    src = IMERG_SOURCE.replace("monthly", f"monthly {year}")
    items = [_item(k, feats[k], *IMERG_SPEC[k], src) for k in IMERG_SPEC]
    return layers.save_layer("earth_precip", items, _cd())


BUILDERS = {"lst": build_lst, "ndvi": build_ndvi, "snow": build_snow, "emit": build_emit, "landcover": build_landcover,
            "precip": build_precip}


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
