"""Low-Sun windows: hours per day with the Sun between 0 and 5 degrees above the horizon.

At the lunar south pole the Sun never climbs more than a few degrees above the
horizon. On Earth the same grazing light lasts minutes at the equator and hours
at high latitudes. This module computes, for any latitude and day of the year,
how long the Sun stays in a low band. Only astronomy is involved: no downloads.

The elevation is geometric (centre of the solar disc, no refraction, flat horizon).
"""
from __future__ import annotations

import datetime as dt
from typing import Sequence

import numpy as np

LOW_BAND_DEG = (0.0, 5.0)
LUNAR_OBLIQUITY_DEG = 1.54      # tilt of the Moon's spin axis to the ecliptic normal
REFERENCE_YEAR = 2026
_J2000 = dt.datetime(2000, 1, 1, 12, 0, 0)


def declination_deg(when: dt.datetime) -> float:
    """Solar declination (low-precision Astronomical Almanac formula, error below 0.02 deg)."""
    n = (when - _J2000).total_seconds() / 86400.0
    L = np.radians((280.460 + 0.9856474 * n) % 360.0)
    g = np.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + np.radians(1.915) * np.sin(g) + np.radians(0.020) * np.sin(2 * g)
    eps = np.radians(23.439 - 0.0000004 * n)
    return float(np.degrees(np.arcsin(np.sin(eps) * np.sin(lam))))


def daily_declinations(year: int = REFERENCE_YEAR) -> tuple[np.ndarray, np.ndarray]:
    """(month of each day, declination at 12:00 UTC of each day) for one year."""
    day = dt.datetime(year, 1, 1, 12)
    months, decl = [], []
    while day.year == year:
        months.append(day.month)
        decl.append(declination_deg(day))
        day += dt.timedelta(days=1)
    return np.array(months), np.array(decl)


def _fraction_above(lat_rad: np.ndarray, decl_rad: np.ndarray, h_deg: float) -> np.ndarray:
    """Fraction of the day the Sun is higher than h_deg."""
    cos_h = (np.sin(np.radians(h_deg)) - np.sin(lat_rad) * np.sin(decl_rad)) / (np.cos(lat_rad) * np.cos(decl_rad))
    return np.arccos(np.clip(cos_h, -1.0, 1.0)) / np.pi


def hours_in_band(lat_deg, decl_deg, lo: float = LOW_BAND_DEG[0], hi: float = LOW_BAND_DEG[1]) -> np.ndarray:
    """Hours per day with the solar elevation between lo and hi degrees.

    ``lat_deg`` and ``decl_deg`` broadcast against each other.
    """
    lat = np.radians(np.clip(np.asarray(lat_deg, dtype=np.float64), -89.999, 89.999))
    decl = np.radians(np.asarray(decl_deg, dtype=np.float64))
    return 24.0 * (_fraction_above(lat, decl, lo) - _fraction_above(lat, decl, hi))


def monthly_low_sun_hours(lats_deg: Sequence[float], year: int = REFERENCE_YEAR,
                          lo: float = LOW_BAND_DEG[0], hi: float = LOW_BAND_DEG[1]) -> np.ndarray:
    """Mean hours per day in the low band for each latitude and month: shape (n_lat, 12)."""
    months, decl = daily_declinations(year)
    daily = hours_in_band(np.asarray(lats_deg)[:, None], decl[None, :], lo, hi)   # (n_lat, n_days)
    return np.stack([daily[:, months == m].mean(axis=1) for m in range(1, 13)], axis=1)


def moon_max_sun_elevation_deg(lat_deg: float) -> float:
    """Highest the Sun can get above a flat horizon at a lunar latitude (topography ignored)."""
    return 90.0 - abs(lat_deg) + LUNAR_OBLIQUITY_DEG


def low_sun_table(cell_deg: float = 0.5, year: int = REFERENCE_YEAR) -> dict:
    """Low-Sun table for the latitude rows of the Earth grid (north to south)."""
    n_lat = int(round(180.0 / cell_deg))
    lats = 90.0 - cell_deg / 2.0 - np.arange(n_lat) * cell_deg
    monthly = monthly_low_sun_hours(lats, year)
    return {
        "lat": lats,
        "monthly_hours": monthly,                       # (n_lat, 12)
        "best_hours": monthly.max(axis=1),
        "best_month": monthly.argmax(axis=1) + 1,
        "mean_hours": monthly.mean(axis=1),
    }
