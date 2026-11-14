import math

import numpy as np
import pytest

from analog_finder.io import pds

from conftest import MOON_R, moon_xy, write_synthetic_lola, write_synthetic_mola


def test_label_parsing_lola(tmp_path):
    lbl = write_synthetic_lola(tmp_path, n=101, scale=240.0)
    label = pds.parse_label(lbl)
    assert label["PDS_VERSION_ID"] == "PDS3"
    # as in the real LDEM labels, the file and IMAGE objects are nested in UNCOMPRESSED_FILE
    file_obj = label["UNCOMPRESSED_FILE"]
    assert file_obj["^IMAGE"] == "LDEM_75S_240M.IMG" and file_obj["RECORD_BYTES"] == 202
    img = file_obj["IMAGE"]
    assert img["LINES"] == 101 and img["SAMPLE_TYPE"] == "LSB_INTEGER"
    assert img["SCALING_FACTOR"] == 0.5 and img["OFFSET"] == 1737400.0
    assert pds._find(label, "^IMAGE") == "LDEM_75S_240M.IMG" and pds._block(label, "IMAGE") is img
    proj = label["IMAGE_MAP_PROJECTION"]
    assert proj["MAP_SCALE"] == 240
    assert proj["CENTER_LATITUDE"] == -90
    assert proj["WESTERNMOST_LONGITUDE"] == "N/A"
    assert label["_units"]["MAP_SCALE"] == "m/pix"
    assert "PLANETARY_RADIUS" in file_obj["DESCRIPTION"]          # multi-line string kept whole


def test_read_lola_values_and_file_lookup_ignores_case(tmp_path):
    lbl = write_synthetic_lola(tmp_path, n=1001, scale=480.0)
    img = pds.read_image(lbl)                                   # label points to an upper-case name
    assert img.shape == (1001, 1001)
    assert img.data.dtype == np.dtype("<i2")
    assert img.scale == 0.5 and img.offset == 1737400.0
    r, c = img.geo.rowcol(-89.67, 129.78)
    assert img.height()[int(round(r)), int(round(c))] < -3000   # Shackleton pit
    r, c = img.geo.rowcol(-84.6, 31.0)
    assert img.height()[int(round(r)), int(round(c))] > 5500    # Mons Mouton
    assert abs(img.physical()[int(round(r)), int(round(c))] - (MOON_R + 6000)) < 100


def test_polar_stereographic_matches_independent_formula_and_pyproj(tmp_path):
    lbl = write_synthetic_lola(tmp_path, n=3812 // 4, scale=240.0)
    geo = pds.read_image(lbl).geo
    assert geo.kind == "polar_stereo" and geo.pole == -1 and geo.scale_m == 240.0
    pyproj = pytest.importorskip("pyproj")
    tr = pyproj.Transformer.from_crs(
        "+proj=longlat +R=1737400 +no_defs", "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +no_defs",
        always_xy=True)
    c = (geo.shape[0] - 1) / 2.0
    for lat, lon in [(-89.684, 196.739), (-89.67, 129.78), (-88.5, 272.9), (-87.0, 0.0), (-87.0, 90.0)]:
        x, y = geo.xy(lat, lon)
        x_ref, y_ref = tr.transform(lon, lat)
        assert abs(x - x_ref) < 0.5 and abs(y - y_ref) < 0.5
        x2, y2 = moon_xy(lat, lon)
        assert abs(x - x2) < 1e-6 and abs(y - y2) < 1e-6
        row, col = geo.rowcol(lat, lon)
        assert abs(col - (c + x_ref / 240.0)) < 1e-3 and abs(row - (c - y_ref / 240.0)) < 1e-3
        lat2, lon2 = geo.latlon(row, col)
        assert abs(lat2 - lat) < 1e-6 and abs((lon2 - lon + 180) % 360 - 180) < 1e-5
    # longitude 0 is up, 90 E is to the right
    r0, c0 = geo.rowcol(-87.0, 0.0)
    r90, c90 = geo.rowcol(-87.0, 90.0)
    assert r0 < c and abs(c0 - c) < 1e-6
    assert c90 > c and abs(r90 - c) < 1e-6


def test_real_lola_geometry_from_label_values():
    """The numbers of the real ldem_75s_240m label: 3812 px at 240 m, pole at the centre."""
    geo = pds.Georef("polar_stereo", (3812, 3812), 1737400.0, scale_m=240.0, pole=-1)
    row, col = geo.rowcol(-90.0, 0.0)
    assert row == 1905.5 and col == 1905.5                      # equals LINE/SAMPLE_PROJECTION_OFFSET
    row, _ = geo.rowcol(-75.0, 0.0)                             # top edge is the 75 S parallel
    assert abs(row - (-0.5)) < 2.0
    dx, dy = geo.pixel_size_m(-89.68)
    assert abs(dx - 240.0) < 0.01


def test_read_mola_and_cylindrical_georef(tmp_path):
    lbl = write_synthetic_mola(tmp_path, res=8)
    img = pds.read_image(lbl)
    assert img.data.dtype == np.dtype(">i2")
    assert img.scale == 1.0 and img.offset == 0.0
    geo = img.geo
    assert geo.kind == "cylindrical" and geo.res == 8.0 and geo.max_lat == 90.0 and geo.west_lon == 0.0
    lat, lon = geo.latlon(0, 0)
    assert abs(lat - (90 - 1 / 16)) < 1e-9 and abs(lon - 1 / 16) < 1e-9     # first pixel centre
    row, col = geo.rowcol(18.65, 226.2)
    assert img.height()[int(round(row)), int(round(col))] > 20000           # Olympus Mons
    row, col = geo.rowcol(-42.7, 70.0)
    assert img.height()[int(round(row)), int(round(col))] < -7500           # Hellas
    dx, dy = geo.pixel_size_m(60.0)
    deg = math.pi * 3396000.0 / 180.0
    assert abs(dy - deg / 8) < 1e-6 and abs(dx - deg / 8 * 0.5) < 1e-6
    rs, cs, clipped = geo.window(18.44, 77.45, 40000.0)
    assert not clipped and rs.stop - rs.start >= 10


def test_real_mola_16ppd_first_pixel():
    """Real megt90n000eb: 16 px/deg, first sample centre at 0.03125 E, 89.96875 N."""
    geo = pds.Georef("cylindrical", (2880, 5760), 3396000.0, res=16.0, max_lat=90.0, west_lon=0.0)
    lat, lon = geo.latlon(0, 0)
    assert abs(lat - 89.96875) < 1e-9 and abs(lon - 0.03125) < 1e-9
    row, col = geo.rowcol(0.0, 180.0)
    assert abs(row - 1439.5) < 1e-9 and abs(col - 2879.5) < 1e-9             # map centre between pixels


def test_truncated_image_is_reported(tmp_path):
    lbl = write_synthetic_lola(tmp_path, n=101, scale=240.0)
    img_path = tmp_path / "ldem_75s_240m.img"
    img_path.write_bytes(img_path.read_bytes()[:1000])
    with pytest.raises(ValueError, match="incomplete"):
        pds.read_image(lbl)


def test_mola_tile_name():
    assert pds.mola_tile_bounds("megt90n180gb.img") == (90.0, 180.0, 64.0)
    assert pds.mola_tile_bounds("megt00n000gb.img") == (0.0, 0.0, 64.0)
    assert pds.mola_tile_bounds("megt44s090hb.img") == (-44.0, 90.0, 128.0)
    assert pds.mola_tile_bounds("megt90n000eb") == (90.0, 0.0, 16.0)
    assert pds.mola_tile_bounds("ldem_16.img") is None
