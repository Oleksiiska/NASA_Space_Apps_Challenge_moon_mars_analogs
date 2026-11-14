import datetime as dt
import math

import numpy as np
import pytest

from analog_finder.features import sun, terrain


# ------------------------------------------------------------------ terrain

def test_slope_of_a_tilted_plane():
    step = 926.0
    rows, cols = np.mgrid[0:40, 0:50]
    for angle in (0.0, 2.0, 8.0, 15.0, 30.0):
        z = math.tan(math.radians(angle)) * cols * step
        s = terrain.slope_deg(z, step, step)
        assert np.isnan(s[0, 0]) and np.isnan(s[-1, -1])
        assert np.allclose(s[1:-1, 1:-1], angle, atol=1e-3)
    z = math.tan(math.radians(10.0)) * (rows * step + cols * step) / math.sqrt(2)   # diagonal 10 deg
    assert np.allclose(terrain.slope_deg(z, step, step)[1:-1, 1:-1], 10.0, atol=1e-3)


def test_slope_with_row_dependent_pixel_width():
    dy = 926.0
    dx_rows = np.linspace(926.0, 300.0, 30)                    # shrinking with latitude
    cols = np.arange(40)
    z = math.tan(math.radians(5.0)) * cols[None, :] * dx_rows[:, None]
    s = terrain.slope_deg(z, dx_rows, dy)
    # an east-west tilt of 5 degrees; the small extra term comes from dx changing between rows
    assert np.all(np.abs(s[1:-1, 1:3] - 5.0) < 0.05)


def test_block_mean_roughness_relief_histogram():
    z = np.arange(16, dtype=float).reshape(4, 4)
    assert np.allclose(terrain.block_mean(z, 2), [[2.5, 4.5], [10.5, 12.5]])
    flat = np.zeros((10, 10))
    assert np.nanmax(terrain.roughness_rms(flat)) == 0.0
    checker = np.indices((10, 10)).sum(axis=0) % 2 * 10.0     # 0/10 m checkerboard
    rough = terrain.roughness_rms(checker)
    assert 4.9 < np.nanmedian(rough) < 5.1
    assert abs(terrain.relief(np.linspace(0, 1000, 1001)) - 900.0) < 1.0
    h = terrain.slope_histogram(np.array([1.0, 1.0, 6.0, 12.0, 40.0, np.nan]))
    assert abs(h.sum() - 1.0) < 1e-12
    assert h[0] == 0.4 and h[2] == 0.2 and h[4] == 0.2 and h[-1] == 0.2
    assert terrain.hist_intersection(h, h) == pytest.approx(1.0)
    assert terrain.hist_intersection([1, 0], [0, 1]) == 0.0


def test_summarize_reports_plane_and_mask():
    step = 960.0
    rows, cols = np.mgrid[0:60, 0:60]
    z = math.tan(math.radians(8.0)) * rows * step
    mask = terrain.circle_mask(z.shape, (30, 30), 20)
    out = terrain.summarize(z, step, step, mask)
    assert abs(out["slope_mean_deg"] - 8.0) < 1e-3
    assert out["frac_slope_lt15"] == 1.0 and out["frac_slope_lt8"] < 1.0
    assert out["step_m"] == 960.0
    assert out["n_pixels"] == int(mask.sum())
    assert abs(sum(out["slope_hist"]) - 1.0) < 1e-4


# ------------------------------------------------------------------ sun

def test_declination_at_solstices_and_equinox():
    assert abs(sun.declination_deg(dt.datetime(2026, 6, 21, 12)) - 23.44) < 0.05
    assert abs(sun.declination_deg(dt.datetime(2026, 12, 21, 12)) + 23.44) < 0.05
    assert abs(sun.declination_deg(dt.datetime(2026, 3, 20, 15))) < 0.1


def test_hours_in_band_limits():
    # Equator at equinox: the Sun climbs 15 deg/hour, so 0-5 deg takes 20 min at dawn and at dusk
    assert abs(float(sun.hours_in_band(0.0, 0.0)) - 2 * 5 / 15) < 0.01
    # Polar night and midnight Sun: never inside the band
    assert float(sun.hours_in_band(80.0, -23.44)) == 0.0
    assert float(sun.hours_in_band(89.0, 23.44)) == 0.0
    # At the pole the elevation equals the declination: inside the band all day
    assert abs(float(sun.hours_in_band(90.0, 3.0)) - 24.0) < 1e-6
    assert float(sun.hours_in_band(-90.0, 3.0)) == 0.0
    assert abs(float(sun.hours_in_band(-90.0, -3.0)) - 24.0) < 1e-6
    assert np.all(sun.hours_in_band(np.linspace(-90, 90, 181)[:, None], np.linspace(-23.44, 23.44, 40)[None, :]) >= 0)


def test_low_sun_grows_with_latitude():
    table = sun.low_sun_table(0.5)
    lat = table["lat"]
    assert lat[0] == 89.75 and lat[-1] == -89.75 and table["monthly_hours"].shape == (360, 12)
    best = dict(zip(np.round(lat, 2), table["best_hours"]))
    assert best[0.25] < best[45.25] < best[65.25] < best[80.25]
    assert best[0.25] < 1.0 and best[80.25] > 4.0
    # hemispheres nearly mirror each other (not exactly: the seasons differ in length)
    assert np.allclose(table["mean_hours"], table["mean_hours"][::-1], atol=0.1)


def test_against_pvlib_minute_by_minute():
    pvlib = pytest.importorskip("pvlib")
    pd = pytest.importorskip("pandas")
    for lat, day in [(50.45, "2026-12-21"), (50.45, "2026-06-21"), (70.0, "2026-03-20"),
                     (24.0, "2026-09-23"), (-45.0, "2026-06-21"), (66.0, "2026-08-10")]:
        times = pd.date_range(f"{day} 00:00", periods=1440, freq="1min", tz="UTC")
        elev = pvlib.solarposition.get_solarposition(times, lat, 0.0)["elevation"].to_numpy()
        ref_hours = float(((elev >= 0.0) & (elev <= 5.0)).sum()) / 60.0
        when = dt.datetime.fromisoformat(day) + dt.timedelta(hours=12)
        got = float(sun.hours_in_band(lat, sun.declination_deg(when)))
        assert abs(got - ref_hours) < 0.12, (lat, day, got, ref_hours)


def test_moon_sun_elevation():
    assert abs(sun.moon_max_sun_elevation_deg(-89.684) - 1.856) < 1e-3
    assert sun.moon_max_sun_elevation_deg(-84.6) < 7.0
