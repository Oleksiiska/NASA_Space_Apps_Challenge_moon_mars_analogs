import io
import math
import zipfile

import numpy as np
import pytest

from analog_finder.export import to_binary
from analog_finder.features import earth_terrain, terrain
from analog_finder.io import srtm
from analog_finder.prep import layers

DY = earth_terrain.EARTH_RADIUS_M * math.radians(srtm.PIXEL_DEG)


def write_tile(path, z, name_corner=(20.0, 40.0), with_header=True):
    """Write a synthetic SRTMGL30-style zip: big-endian int16 .dem and a text .hdr (ULXMAP = centre of the first pixel)."""
    rows, cols = z.shape
    ul_lon, ul_lat = name_corner
    dem = np.where(np.isnan(z), -9999, np.rint(z)).astype(">i2").tobytes()
    hdr = (f"BYTEORDER      M\nLAYOUT         BIL\nNROWS          {rows}\nNCOLS          {cols}\nNBANDS         1\nNBITS          16\n"
           f"ULXMAP         {ul_lon + srtm.PIXEL_DEG / 2}\nULYMAP         {ul_lat - srtm.PIXEL_DEG / 2}\n"
           f"XDIM           {srtm.PIXEL_DEG}\nYDIM           {srtm.PIXEL_DEG}\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        stem = path.name.split(".")[0]
        zf.writestr(f"{stem}.dem", dem)
        if with_header:
            zf.writestr(f"{stem}.hdr", hdr)
    return path


def test_tile_names():
    assert srtm.tile_corner("e020n40.SRTMGL30.dem.zip") == (40, 20)
    assert srtm.tile_corner("W020N40.SRTMGL30.dem.zip") == (40, -20)
    assert srtm.tile_corner("w180s10.SRTMGL30.dem.zip") == (-10, -180)
    assert srtm.tile_corner("e100n90.SRTMGL30.dem.zip") == (90, 100)
    with pytest.raises(ValueError):
        srtm.tile_corner("topo30.zip")


def test_read_tile_nodata_byteorder_and_geometry(tmp_path):
    z = np.arange(120 * 240, dtype=np.float64).reshape(120, 240) % 3000
    z[:10, :10] = np.nan
    t = srtm.read_tile(write_tile(tmp_path / "e020n40.SRTMGL30.dem.zip", z))
    assert t.z.shape == (120, 240) and t.ul_lat == 40 and t.ul_lon == 20
    assert np.isnan(t.z[:10, :10]).all() and t.z[50, 50] == z[50, 50]
    assert srtm.pixel_of(t, 39.5, 21.0) == (60, 120)
    # the header must agree with the name
    bad = write_tile(tmp_path / "e060n40.SRTMGL30.dem.zip", z, name_corner=(20.0, 40.0))
    with pytest.raises(ValueError, match="west edge"):
        srtm.read_tile(bad)
    # without a header the 4800-column default applies and an odd size is rejected
    with pytest.raises(ValueError):
        srtm.read_tile(write_tile(tmp_path / "e100n40.SRTMGL30.dem.zip", np.zeros((100, 100)), name_corner=(100.0, 40.0),
                                  with_header=False))


def test_cell_features_flat_and_tilted_plane():
    n = 60
    rows, cols = 2 * n, 4 * n                                    # 2 x 4 cells of 0.5 degrees
    flat = earth_terrain.tile_cell_features(np.full((rows, cols), 1500.0, dtype=np.float32), 40.0)
    assert flat["elev_mean_m"].shape == (2, 4) and np.allclose(flat["elev_mean_m"], 1500.0)
    assert np.allclose(flat["slope_mean_deg"], 0.0) and np.allclose(flat["relief_m"], 0.0)
    assert np.allclose(flat["slope_lt8"], 1.0) and np.allclose(flat["slope_h0"], 1.0)

    # a plane rising towards the south at exactly 12 degrees: independent of the east-west pixel width
    z = (np.tan(math.radians(12.0)) * np.arange(rows)[:, None] * DY + np.zeros((1, cols))).astype(np.float32)
    f = earth_terrain.tile_cell_features(z, 40.0)
    assert np.allclose(f["slope_mean_deg"], 12.0, atol=0.05)
    assert np.allclose(f["slope_lt8"], 0.0) and np.allclose(f["slope_lt15"], 1.0)
    assert np.allclose(f["slope_h4"], 1.0, atol=1e-6)            # class 10-15 deg
    hist = np.stack([f[f"slope_h{k}"] for k in range(len(terrain.SLOPE_EDGES) - 1)])
    assert np.allclose(hist.sum(axis=0), 1.0)
    assert np.allclose(f["relief_m"], (95 - 5) / 100 * (n * DY * math.tan(math.radians(12))), rtol=0.1)


def test_cells_with_too_little_land_are_empty():
    n = 60
    z = np.full((n, 2 * n), 100.0, dtype=np.float32)
    z[:, :n] = np.nan                                            # left cell: all sea
    z[:, n: n + 50] = np.nan                                     # right cell: 50 of 60 columns sea, 10 land
    f = earth_terrain.tile_cell_features(z, 10.0)
    assert np.isnan(f["elev_mean_m"][0, 0]) and np.isnan(f["slope_mean_deg"][0, 0])
    assert np.isnan(f["elev_mean_m"][0, 1])                      # 10 land columns, border pixels lost: under 20 % valid


def test_selfcheck_catches_wrong_tiles(tmp_path):
    everest = np.full((6000, 4800), 100.0, dtype=np.float32)    # a tile at 80 E, 40 N holds Everest at 27.99 N, 86.93 E
    tile = srtm.Tile(z=everest, ul_lat=40.0, ul_lon=60.0, name="e060n40.SRTMGL30.dem.zip")
    problems = earth_terrain.selfcheck({tile.name: tile})
    assert problems and "Everest" in problems[0]
    r, c = srtm.pixel_of(tile, 27.99, 86.93)
    tile.z[r, c] = 7900.0
    assert not any("Everest" in p for p in earth_terrain.selfcheck({tile.name: tile}))


def test_build_layer_and_merge_into_grid(project):
    n_lat, n_lon = 360, 720
    src = project / "data" / "raw" / "earth" / "srtmgl30"
    src.mkdir(parents=True)
    z = np.full((120, 240), 800.0)                               # 1 x 0.5 degree... 2 x 4 cells at 20 E, 40 N
    write_tile(src / "e020n40.SRTMGL30.dem.zip", z, name_corner=(20.0, 40.0))
    path = earth_terrain.build_layer(src, log=lambda s: None)
    assert path.name == "earth_terrain.npz"
    meta, feats = layers.load_layer(path)
    by = {f.name: f for f in feats}
    assert set(by) == set(earth_terrain.SPEC) and by["elev_mean_m"].values.shape == (n_lat, n_lon)
    r0, c0 = int((90 - 40) / 0.5), int((20 + 180) / 0.5)
    assert np.allclose(by["elev_mean_m"].values[r0: r0 + 2, c0: c0 + 4], 800.0)
    assert np.isnan(by["elev_mean_m"].values[0, 0])

    # merge into an existing grid that holds two land cells: one inside the tile, one outside
    inside, outside = r0 * n_lon + c0, 5 * n_lon + 5
    index = np.array(sorted([inside, outside]), dtype=np.uint32)
    base = [to_binary.Feature("land_frac", np.ones(2), 0.0, 1.0, "fraction"),
            to_binary.Feature("elev_mean_m", np.array([1.0, 1.0]), 0.0, 10.0, "m")]   # same name: must be replaced
    to_binary.write_grid(project / "data" / "processed", index, (n_lat, n_lon), 0.5, base, extra={"min_land_frac": 0.2})
    layers.merge_into_grid(log=lambda s: None)
    meta2, index2, got = to_binary.read_grid(project / "data" / "processed")
    assert list(index2) == list(index) and meta2["min_land_frac"] == 0.2
    names = [f["name"] for f in meta2["features"]]
    assert names[:2] == ["land_frac", "elev_mean_m"] and "slope_h8" in names and len(names) == 2 + len(earth_terrain.SPEC) - 1
    k = int(np.searchsorted(index2, inside))
    assert got["elev_mean_m"][k] == pytest.approx(800.0, abs=7000 / 254)
    assert np.isnan(got["elev_mean_m"][1 - k]) and np.isnan(got["slope_mean_deg"][1 - k])
    assert got["slope_mean_deg"][k] == pytest.approx(0.0, abs=0.2)
