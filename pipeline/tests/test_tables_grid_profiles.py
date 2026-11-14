import json
import math

import numpy as np
import pytest

from analog_finder import config
from analog_finder.export import to_binary
from analog_finder.io import tables
from analog_finder.prep import grid as grid_mod

from conftest import write_synthetic_grs, write_synthetic_lola, write_synthetic_mola, write_synthetic_prp


# ------------------------------------------------------------------ tables

def test_diviner_prp_fixed_width(tmp_path):
    path = tmp_path / "dlre_prp_south.tab"
    truth = write_synthetic_prp(path, n=3000)
    assert path.stat().st_size == (3000 + 1) * 210
    got = tables.read_diviner_prp(path)
    for name in ("tri_clon", "tri_clat", "temp_avg", "temp_max", "ice_depth"):
        assert got[name].shape == (3000,)
        assert np.allclose(got[name], truth[name], atol=1e-2)
    assert (got["ice_depth"] == tables.ICE_DEPTH_TOO_DEEP).any() and (got["ice_depth"] == 0).any()
    assert tables.read_diviner_prp(path, max_rows=10)["temp_avg"].shape == (10,)


def test_diviner_prp_fallback_by_header_names(tmp_path):
    path = tmp_path / "odd.tab"
    path.write_text("tri_clat, tri_clon, temp_avg, temp_max, ice_depth\n"
                    "-89.5, 10.0, 40.0, 90.0, 0.0\n-88.0, 20.0, 120.0, 200.0, -999.0\n", encoding="ascii")
    got = tables.read_diviner_prp(path)
    assert list(got["tri_clat"]) == [-89.5, -88.0] and list(got["ice_depth"]) == [0.0, -999.0]


def test_grs_table_and_nearest_bin(tmp_path):
    path = tmp_path / "h2o_sr_5x5.tab"
    write_synthetic_grs(path)
    t = tables.read_grs_table(path)
    assert t["lat"].size == 36 * 72 == 2592
    assert np.isnan(t["value"][np.abs(t["lat"]) > 75]).all()
    b = tables.nearest_bin(t, 18.44, 77.45)
    assert b["lat"] == 17.5 and b["lon"] == 77.5 and abs(b["value"] - 3.75) < 1e-9
    assert tables.nearest_bin(t, 47.2, 184.3)["value"] == pytest.approx(2.0 + 4.75)
    assert tables.nearest_bin(t, -1.9, 359.9)["lon"] == 357.5


# ------------------------------------------------------------------ grid and export

def test_polygon_fraction_and_grid(tmp_path):
    pytest.importorskip("shapely")
    land = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [
            [[0, 0], [20, 0], [20, 10], [0, 10], [0, 0]]]}},
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [
            [[-180, -90], [180, -90], [180, -80], [-180, -80], [-180, -90]]]}}]}
    ice = {"type": "FeatureCollection", "features": [land["features"][1]]}
    (tmp_path / "land.geojson").write_text(json.dumps(land))
    (tmp_path / "ice.geojson").write_text(json.dumps(ice))
    g = grid_mod.build(tmp_path / "land.geojson", tmp_path / "ice.geojson", cell_deg=5.0, sub=4)
    assert g.shape == (36, 72)
    assert g.index.size == 4 * 2 + 72 * 2                      # 20x10 degree box + two polar rows
    row, col = grid_mod.cell_of(5.0, 10.0, 5.0)
    assert g.land_frac[row, col] == 1.0 and g.ice_frac[row, col] == 0.0
    assert g.land_frac[grid_mod.cell_of(-85, 0, 5.0)] == 1.0 and g.ice_frac[grid_mod.cell_of(-85, 0, 5.0)] == 1.0
    assert g.land_frac[grid_mod.cell_of(40, 100, 5.0)] == 0.0
    assert set(np.round(g.lat, 2)) == {2.5, 7.5, -82.5, -87.5}
    assert grid_mod.cell_of(89.99, -180.0) == (0, 0) and grid_mod.cell_of(-89.99, 179.99) == (359, 719)
    assert float(grid_mod.row_lat(0)) == 89.75 and float(grid_mod.col_lon(0)) == -179.75


def test_export_roundtrip(tmp_path):
    index = np.array([5, 9, 700, 100000], dtype=np.uint32)
    feats = [to_binary.Feature("a", np.array([0.0, 0.5, 1.0, np.nan]), 0.0, 1.0, "fraction"),
             to_binary.Feature("b", np.array([0.0, 6.0, 12.0, 24.0]), 0.0, 24.0, "hours/day")]
    meta = to_binary.write_grid(tmp_path, index, (360, 720), 0.5, feats)
    assert (tmp_path / "grid.bin").stat().st_size == 8 and (tmp_path / "grid_index.bin").stat().st_size == 16
    assert meta["features"][1]["offset"] == 4
    meta2, index2, got = to_binary.read_grid(tmp_path)
    assert list(index2) == list(index) and meta2["grid"]["n_cells"] == 4
    assert np.allclose(got["a"][:3], [0.0, 0.5, 1.0], atol=1 / 254) and np.isnan(got["a"][3])
    assert np.allclose(got["b"], [0.0, 6.0, 12.0, 24.0], atol=24 / 254)
    raw = np.fromfile(tmp_path / "grid.bin", dtype=np.uint8)
    assert raw[3] == 255 and raw[0] == 0 and raw[2] == 254


# ------------------------------------------------------------------ target profiles on synthetic raw data

def test_profiles_from_synthetic_raw_data(project):
    from analog_finder.targets import profiles

    write_synthetic_lola(project / "data" / "raw" / "moon" / "lola", n=1001, scale=480.0)
    write_synthetic_mola(project / "data" / "raw" / "mars" / "mola", res=8)
    write_synthetic_prp(project / "data" / "raw" / "moon" / "diviner" / "dlre_prp_south.tab", n=20000)
    write_synthetic_grs(project / "data" / "raw" / "mars" / "grs" / "h2o_sr_5x5.tab")

    out = profiles.build_profiles(log=lambda s: None)
    assert out["missing_inputs"] == []
    assert out["selfcheck"] == {"moon_lola": "ok", "mars_mola": "ok"}
    assert set(out["targets"]) == {t["id"] for t in config.targets()["targets"]}

    mm = out["targets"]["mons_mouton"]
    assert mm["terrain_1km"]["elev_max_m"] > 5000 and mm["terrain_1km"]["relief_p5_p95_m"] > 2000
    assert mm["terrain_1km"]["step_m"] == pytest.approx(4 * 480.0, rel=0.01)
    assert mm["sun"]["max_elevation_deg_flat_horizon"] == pytest.approx(6.94, abs=0.01)
    sh = out["targets"]["shackleton_crater"]
    assert sh["terrain_1km"]["elev_min_m"] < -2500
    ridge = out["targets"]["shackleton_ridge"]
    assert ridge["thermal_ice"]["n_triangles"] > 0
    assert 0.0 <= ridge["thermal_ice"]["frac_ice_stable_within_1m"] <= 1.0
    assert ridge["thermal_ice"]["temp_avg_min_K"] >= 30.0

    jez = out["targets"]["jezero"]
    assert jez["terrain_source"] == "megt90n000eb.img"
    assert jez["terrain_1km"]["slope_mean_deg"] == pytest.approx(2.0, abs=0.05)     # the synthetic tilt
    assert jez["terrain_1km"]["frac_slope_lt8"] == 1.0
    assert jez["water"]["h2o_weight_percent"] == pytest.approx(3.75)
    assert out["targets"]["phoenix"]["water"]["h2o_weight_percent"] == pytest.approx(2.0 + 6.75)
    json.dumps(out)                                              # JSON-safe: no NaN, no numpy types


def test_selfcheck_catches_a_flipped_image(project):
    from analog_finder.io import pds
    from analog_finder.targets import profiles

    lbl = write_synthetic_lola(project / "data" / "raw" / "moon" / "lola", n=1001, scale=480.0)
    img_path = lbl.with_suffix(".img")
    flipped = np.fromfile(img_path, dtype="<i2").reshape(1001, 1001)[:, ::-1]
    flipped.tofile(img_path)
    problems = profiles.selfcheck_moon(pds.read_image(lbl))
    assert problems and any("Mons Mouton" in p or "Shackleton" in p for p in problems)


def test_profiles_report_missing_inputs(project):
    from analog_finder.targets import profiles

    out = profiles.build_profiles(log=lambda s: None)
    assert len(out["missing_inputs"]) == 4
    assert "terrain_1km" not in out["targets"]["jezero"]
    assert out["targets"]["shackleton_ridge"]["sun"]["max_elevation_deg_flat_horizon"] < 2.0
