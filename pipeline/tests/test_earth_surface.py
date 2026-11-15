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


def test_landcover_shares_are_relative_to_land_and_see_small_bare_patches():
    pct = np.zeros((20, 20, 17), dtype=np.uint8)
    pct[:, :, 12] = 100                              # cropland everywhere
    pct[0:10, 0:10, 12] = 0                          # block (0, 0): half sea, half land
    pct[0:10, 0:10, es.LC_WATER] = 50
    pct[0:10, 0:10, es.LC_BARREN] = 50
    pct[0:2, 10:20, 12] = 0                          # block (0, 1): one bare strip, 20 % of the pixels
    pct[0:2, 10:20, es.LC_BARREN] = 100
    pct[10:20, 0:10] = 255                           # block (1, 0): fill
    pct[10:20, 10:20, 12] = 60                       # block (1, 1): ice and open shrubs
    pct[10:20, 10:20, es.LC_SNOW_ICE] = 30
    pct[10:20, 10:20, es.LC_OPEN_SHRUB] = 10
    f = es.landcover_features(pct)
    assert f["barren_frac"][0, 0] == pytest.approx(1.0)        # all land of the block is bare, sea does not dilute
    assert f["barren_frac"][0, 1] == pytest.approx(0.2)
    assert np.isnan(f["barren_frac"][1, 0])
    assert f["snow_ice_frac"][1, 1] == pytest.approx(0.3) and f["sparse_frac"][1, 1] == pytest.approx(0.1)
    assert f["barren_frac"][1, 1] == 0.0


def test_landcover_all_water_block_is_nan():
    pct = np.zeros((10, 10, 17), dtype=np.uint8)
    pct[:, :, es.LC_WATER] = 100
    assert np.isnan(es.landcover_features(pct)["barren_frac"][0, 0])


def test_imerg_is_flipped_to_north_up(tmp_path):
    h5py = pytest.importorskip("h5py")
    lat = np.arange(-89.95, 90, 0.1, dtype=np.float32)[:1800]
    lon = np.arange(-179.95, 180, 0.1, dtype=np.float32)[:3600]
    pr = np.zeros((1, 3600, 1800), np.float32)
    pr[0, 0, 1799] = 1.0                       # lon -179.95, lat 89.95: north-west corner
    pr[0, 5, 3] = -9999.9                      # fill near the south pole
    p = tmp_path / "3B-MO.MS.MRG.3IMERG.20230101-S000000-E235959.01.V07B.HDF5"
    with h5py.File(p, "w") as f:
        f["Grid/lat"], f["Grid/lon"], f["Grid/precipitation"] = lat, lon, pr
    a = es.read_imerg(p)
    assert a.shape == (1800, 3600) and a[0, 0] == 1.0 and np.isnan(a[1799 - 3, 5])


def test_precip_features_weight_months_by_hours_and_need_ten_months():
    one = np.ones((2, 2), np.float32)
    monthly = {m: one * 0.1 for m in range(1, 13)}                  # 0.1 mm/hour all year
    monthly[2] = np.array([[0.1, np.nan], [0.1, 0.1]], np.float32)
    monthly[3] = np.array([[0.1, np.nan], [0.1, 0.1]], np.float32)
    monthly[4] = np.array([[0.1, np.nan], [0.1, 0.1]], np.float32)
    f = es.precip_features(monthly, 2023)["precip_log_mm"]
    assert 10 ** f[0, 0] - 1 == pytest.approx(0.1 * 8760, rel=1e-4)
    assert np.isnan(f[0, 1])                                          # only 9 valid months


def test_precip_min_takes_the_driest_land_pixel():
    rate = np.full((10, 10), 0.1, np.float32)
    rate[2, 3] = 0.001                                   # dry salt flat inside the first block
    rate[7, 7] = 0.0                                     # dry sea pixel in the last block
    monthly = {m: rate.copy() for m in range(1, 13)}
    land = np.ones((10, 10), bool)
    land[7, 7] = False
    f = es.precip_features(monthly, 2023, n=5, land=land)
    mm = 10 ** f["precip_min_log_mm"] - 1
    assert mm[0, 0] == pytest.approx(0.001 * 8760, rel=1e-3)
    assert mm[1, 1] == pytest.approx(0.1 * 8760, rel=1e-3)               # the sea pixel is ignored
    assert 10 ** f["precip_log_mm"][0, 0] - 1 == pytest.approx((24 * 0.1 + 0.001) / 25 * 8760, rel=1e-3)


def test_bare_pixel_share_counts_pixels_not_the_block_mean():
    ndvi = np.full((10, 10), 0.6, np.float32)
    ndvi[:2, :] = 0.05                                   # a bare strip: 20 % of the pixels
    cnt = np.full((10, 10), 12, np.uint8)
    share = es.bare_pixel_share(ndvi * 12, cnt)
    assert share[0, 0] == pytest.approx(0.2)
    cnt[:, :] = 3                                        # too few months everywhere
    assert np.isnan(es.bare_pixel_share(ndvi * 3, cnt)[0, 0])


def test_emit_to_finer_grid_takes_the_nearest_emit_cell():
    lat = np.array([0.5, 0.0, -0.5])
    lon = np.array([-0.5, 0.0, 0.5])
    a = np.arange(9, dtype=np.float32).reshape(3, 3)          # value at (lat[i], lon[j])
    g = es.emit_to_finer_grid(a, lat, lon, 0.25)
    assert g.shape == (720, 1440)
    r, c = int((90 - 0.125) / 0.25), int((0.125 + 180) / 0.25)   # fine cell centred at (0.125, 0.125) -> EMIT (0, 0)
    assert g[r, c] == 4.0
    assert np.isnan(g[0, 0])


def test_other_grid_sizes_get_their_own_folders(monkeypatch):
    from analog_finder import config
    from analog_finder.prep import layers
    monkeypatch.delenv("ANALOG_CELL_DEG", raising=False)
    assert config.processed_dir().name == "processed" and layers.layers_dir().name == "layers"
    monkeypatch.setenv("ANALOG_CELL_DEG", "0.25")
    assert config.processed_dir().name == "processed_025" and layers.layers_dir().name == "layers_025"
    assert es._n() == 5
