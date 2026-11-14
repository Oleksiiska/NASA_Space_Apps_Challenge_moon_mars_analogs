"""Terrain metrics on elevation grids, identical for the three worlds.

Compare worlds only at the same ground step. The project uses about 1 km:
Earth SRTMGL30 (926 m), Mars MOLA 64 px/deg (926 m), Moon LOLA 240 m
aggregated 4 x 4 (960 m).
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

# Slope classes in degrees. 8 deg ~ landing limit, 15 deg ~ pressurised rover limit.
SLOPE_EDGES = (0.0, 2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 90.0)


def block_mean(z: np.ndarray, factor: int) -> np.ndarray:
    """Aggregate by averaging factor x factor blocks (edges that do not fill a block are dropped)."""
    if factor <= 1:
        return np.asarray(z, dtype=np.float32)
    rows, cols = (z.shape[0] // factor) * factor, (z.shape[1] // factor) * factor
    a = np.asarray(z[:rows, :cols], dtype=np.float32)
    return a.reshape(rows // factor, factor, cols // factor, factor).mean(axis=(1, 3))


def slope_deg(z: np.ndarray, dx, dy: float) -> np.ndarray:
    """Slope in degrees by Horn's 3 x 3 method. Border pixels are NaN.

    ``dx`` is the east-west pixel size in metres: a scalar, or one value per row
    for latitude/longitude grids where it shrinks with cos(latitude).
    ``dy`` is the north-south pixel size in metres.
    """
    z = np.asarray(z, dtype=np.float64)
    out = np.full(z.shape, np.nan, dtype=np.float32)
    if z.shape[0] < 3 or z.shape[1] < 3:
        return out
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    dx_arr = np.asarray(dx, dtype=np.float64)
    if dx_arr.ndim == 1:
        dx_arr = dx_arr[1:-1, None]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8.0 * dx_arr)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8.0 * dy)
    out[1:-1, 1:-1] = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    return out


def roughness_rms(z: np.ndarray, win: int = 3) -> np.ndarray:
    """RMS deviation of elevation from the mean of a win x win neighbourhood, metres. Border is NaN."""
    z = np.asarray(z, dtype=np.float64)
    out = np.full(z.shape, np.nan, dtype=np.float32)
    if min(z.shape) < win:
        return out
    w = sliding_window_view(z, (win, win))
    half = win // 2
    out[half: half + w.shape[0], half: half + w.shape[1]] = w.std(axis=(2, 3))
    return out


def relief(z: np.ndarray, lo: float = 5.0, hi: float = 95.0) -> float:
    """Elevation range between two percentiles (robust to single spikes), metres."""
    v = np.asarray(z, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    p_lo, p_hi = np.percentile(v, [lo, hi])
    return float(p_hi - p_lo)


def slope_histogram(s: np.ndarray, edges: Sequence[float] = SLOPE_EDGES) -> np.ndarray:
    """Fraction of pixels in each slope class (sums to 1)."""
    v = np.asarray(s, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros(len(edges) - 1)
    counts, _ = np.histogram(np.clip(v, edges[0], np.nextafter(edges[-1], 0)), bins=edges)
    return counts / counts.sum()


def circle_mask(shape: tuple[int, int], center_rc: tuple[float, float], radius_px_r: float,
                radius_px_c: Optional[float] = None) -> np.ndarray:
    """Boolean mask of an ellipse (a circle on the ground when pixels are not square)."""
    radius_px_c = radius_px_r if radius_px_c is None else radius_px_c
    r = (np.arange(shape[0]) - center_rc[0])[:, None] / max(radius_px_r, 1e-9)
    c = (np.arange(shape[1]) - center_rc[1])[None, :] / max(radius_px_c, 1e-9)
    return r * r + c * c <= 1.0


def summarize(z: np.ndarray, dx, dy: float, mask: Optional[np.ndarray] = None) -> dict:
    """Terrain fingerprint of an elevation window.

    Returns relief, slope statistics, the slope histogram and roughness. The same
    function is used for the Moon, Mars and Earth so the numbers are comparable.
    """
    z = np.asarray(z, dtype=np.float64)
    s = slope_deg(z, dx, dy)
    rough = roughness_rms(z)
    if mask is not None:
        s = np.where(mask, s, np.nan)
        rough = np.where(mask, rough, np.nan)
        zz = np.where(mask, z, np.nan)
    else:
        zz = z
    sv = s[np.isfinite(s)]
    rv = rough[np.isfinite(rough)]
    hist = slope_histogram(s)

    def pct(v: np.ndarray, q: float) -> float:
        return float(np.percentile(v, q)) if v.size else float("nan")

    dx_mean = float(np.mean(dx))
    return {
        "n_pixels": int(np.isfinite(zz).sum()),
        "step_m": round((dx_mean + float(dy)) / 2.0, 1),
        "elev_mean_m": float(np.nanmean(zz)) if np.isfinite(zz).any() else float("nan"),
        "elev_min_m": float(np.nanmin(zz)) if np.isfinite(zz).any() else float("nan"),
        "elev_max_m": float(np.nanmax(zz)) if np.isfinite(zz).any() else float("nan"),
        "relief_p5_p95_m": relief(zz),
        "slope_mean_deg": float(sv.mean()) if sv.size else float("nan"),
        "slope_p50_deg": pct(sv, 50),
        "slope_p90_deg": pct(sv, 90),
        "frac_slope_lt8": float((sv < 8).mean()) if sv.size else float("nan"),
        "frac_slope_lt15": float((sv < 15).mean()) if sv.size else float("nan"),
        "roughness_rms_p50_m": pct(rv, 50),
        "roughness_rms_p90_m": pct(rv, 90),
        "slope_hist": [round(float(x), 5) for x in hist],
        "slope_hist_edges_deg": list(SLOPE_EDGES),
    }


def hist_intersection(p: Sequence[float], q: Sequence[float]) -> float:
    """Similarity of two normalised histograms in [0, 1] (1 = identical)."""
    p, q = np.asarray(p, dtype=np.float64), np.asarray(q, dtype=np.float64)
    return float(np.minimum(p, q).sum())
