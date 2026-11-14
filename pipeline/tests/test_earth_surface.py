import numpy as np
import pytest

from analog_finder.features import earth_surface as es
from analog_finder.prep import layers


def test_month_of_from_day_of_year():
    assert es.month_of("MOD11C3.A2023182.061.2023215224507.hdf") == 7
    assert es.month_of("MOD10CM.A2023001.061.x.hdf") == 1
    assert es.month_of("MOD13C2.A2023335.061.x.hdf") == 12
    with pytest.raises(ValueError):
        es.month_of("something.hdf")


def test_block_mean_ignores_nan_and_needs_enough_pixels():
    a = np.full((20, 20), np.nan, dtype=np.float32)
    a[:10, :10] = 5.0                       # full block
    a[10:13, 10:20] = 7.0                   # 30 of 100 pixels valid: exactly the minimum
    a[10:12, 0:5] = 9.0                     # 10 of 100 valid: too few
    out = es.block_mean(a, 10, 0.3)
    assert out.shape == (2, 2)
    assert out[0, 0] == pytest.approx(5.0)
    assert np.isnan(out[0, 1]) and np.isnan(out[1, 0])
    assert out[1, 1] == pytest.approx(7.0)
    with pytest.raises(ValueError):
        es.block_mean(np.zeros((15, 20)), 10)


def test_cell_at_uses_north_up_west_first_layout():
    arr = np.zeros((360, 720), dtype=np.float32)
    arr[0, 0] = 1.0                         # 90 N..89.5 N, 180 W..179.5 W
    arr[359, 719] = 2.0
    assert es.cell_at(arr, 89.9, -179.9) == 1.0
    assert es.cell_at(arr, -89.9, 179.9) == 2.0


def test_snow_codes_become_nan():
    raw = np.array([0, 50, 100, 211, 250, 253, 254, 255], dtype=np.uint8)
    out = es.snow_cover(raw)
    assert out[:3].tolist() == [0.0, 50.0, 100.0]
    assert np.isnan(out[3:]).all()


def test_snow_features_count_free_months_and_need_six_months():
    shape = (1, 2)
    months = {m: np.array([[0.0, 90.0]], dtype=np.float32) for m in range(1, 13)}
    for m in range(1, 7):
        months[m][0, 0] = np.nan                       # cell 0: only 6 months with a decision
    for m in range(1, 12):
        months[m][0, 1] = np.nan                       # cell 1: a single month
    f = es.snow_features(months)
    assert f["snow_free_months"][0, 0] == 6 and f["snow_cover_pct"][0, 0] == 0
    assert np.isnan(f["snow_free_months"][0, 1]) and np.isnan(f["snow_cover_pct"][0, 1])
    assert np.isnan(f["snow_m01"][0, 0]) and f["snow_m07"][0, 0] == 0 and f["snow_m12"][0, 1] == 90


def test_lst_features_annual_stats():
    day = {m: np.full((1, 1), 300.0 + m, dtype=np.float32) for m in range(1, 13)}
    night = {m: np.full((1, 1), 280.0 + m, dtype=np.float32) for m in range(1, 13)}
    f = es.lst_features(day, night)
    assert f["lst_day_mean_k"][0, 0] == pytest.approx(306.5)
    assert f["lst_day_max_k"][0, 0] == 312 and f["lst_night_min_k"][0, 0] == 281
    assert f["lst_diurnal_k"][0, 0] == pytest.approx(20.0)


def test_emit_to_grid_shifts_a_quarter_cell():
    # EMIT centres at 55.0, 54.5 (lat) and -165.0, -164.5 (lon): our cell centred 54.75 / -164.75 sits between them
    lat = np.array([55.0, 54.5])
    lon = np.array([-165.0, -164.5])
    a = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    g = es.emit_to_grid(a, lat, lon)
    r = int((90 - 54.75) / 0.5)
    c = int((-164.75 + 180) / 0.5)
    assert g[r, c] == pytest.approx(2.5)
    assert g[r - 1, c] == pytest.approx(1.5)            # centre 55.25: only the two EMIT cells at 55.0 are valid
    assert g[r - 2, c] != g[r - 2, c]                   # nothing around 55.75
    assert np.isfinite(g).sum() == 5                    # centre (4 valid) + 4 edge cells (2 valid); the 4 corners have 1 valid -> NaN


def test_emit_to_grid_corner_cells_need_two_valid():
    lat = np.array([55.0])
    lon = np.array([-165.0])
    g = es.emit_to_grid(np.array([[1.0]], dtype=np.float32), lat, lon)
    assert np.isfinite(g).sum() == 0                    # one valid EMIT cell never fills a whole cell


def test_emit_to_grid_wraps_at_the_date_line():
    lat = np.array([0.5, 0.0])
    lon = np.array([179.5, -180.0])
    g = es.emit_to_grid(np.ones((2, 2), dtype=np.float32), lat, lon)
    r = int((90 - 0.25) / 0.5)
    assert g[r, 719] == pytest.approx(1.0) and g[r, 0] == pytest.approx(1.0)


def test_build_layers_from_synthetic_monthly_data_and_merge(tmp_path, monkeypatch):
    monkeypatch.setattr(layers.config, "data_dir", lambda: tmp_path)
    shape = (360, 720)
    day = {m: np.full(shape, 300.0, dtype=np.float32) for m in range(1, 13)}
    f = es.lst_features(day, {m: np.full(shape, 285.0, dtype=np.float32) for m in range(1, 13)})
    items = [layers.LayerFeature(k, v, *es.LST_SPEC[k][:2]) for k, v in f.items()]
    p = layers.save_layer("earth_lst", items, 0.5)
    meta, back = layers.load_layer(p)
    assert [x.name for x in back] == list(es.LST_SPEC)
    assert back[0].values[10, 10] == pytest.approx(300.0)
