import json

import numpy as np
import pytest

from analog_finder import scoring
from analog_finder.features import earth_context as ec
from analog_finder.fetch import earth


def test_read_volcanoes_skips_submarine_and_flags_basaltic(tmp_path):
    p = tmp_path / "v.csv"
    p.write_text("Number,Volcano Name,Country,Region,Latitude,Longitude,Elev,Type,Status,Last Known\n"
                 "1,Alpha,X,R,10.0,20.0,100,Shield volcano,Holocene,D1\n"
                 '2,"Beta, North",X,R,-5.5,30.25,100,Stratovolcano,Historical,D1\n'
                 "3,Gamma,X,R,0,0,-200,Submarine volcano,Holocene,U\n"
                 "4,Delta,X,R,bad,0,0,Cinder cone,Holocene,U\n", encoding="utf-8")
    v = ec.read_volcanoes(p)
    assert [x["name"] for x in v] == ["Alpha", "Beta, North"]
    assert v[0]["basaltic"] and not v[1]["basaltic"]


def test_read_impacts(tmp_path):
    p = tmp_path / "i.csv"
    p.write_text("crater_name,state,country,target_rock,diameter_km,age_millions_years_ago,exposed,drilled,bolid_type,latitude,longitude,url,notes\n"
                 "A,,C,S,24,15,True,False,,48.88,10.58,u,\n", encoding="utf-8")
    i = ec.read_impacts(p)
    assert i == [{"name": "A", "lat": 48.88, "lon": 10.58, "diameter_km": 24.0}]


def test_nearest_distances_on_the_grid():
    # point at the centre of the cell (row 100, col 400): lat 39.75, lon 20.25
    d, k = ec.nearest([{"lat": 39.75, "lon": 20.25}])
    assert d[100, 400] == pytest.approx(0.0, abs=1e-3) and k[100, 400] == 0
    assert d[98, 400] == pytest.approx(111.2, rel=0.01)           # one degree north
    assert d[0, 0] == ec.MAX_KM and k[0, 0] == -1                   # far away: capped
    d2, _ = ec.nearest([{"lat": 39.75, "lon": 20.25}], radius_km=[60.0])
    assert d2[98, 400] == pytest.approx(51.2, rel=0.02)            # distance to the rim
    assert d2[100, 401] == 0.0                                      # inside the structure


def test_nearest_wraps_at_the_date_line():
    d, _ = ec.nearest([{"lat": 0.25, "lon": 179.9}])
    assert d[179, 0] < 40                                           # cell centred at -179.75 is ~38 km away


def test_power_points_and_grid_mapping():
    data = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0.0, 10.0, 300]},
         "properties": {"parameter": {"PRECTOTCORR": {"JAN": 1, "ANN": 2.0}}}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0.0, 10.5, 300]},
         "properties": {"parameter": {"PRECTOTCORR": {"ANN": 4.0}}}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0.625, 10.0, 300]},
         "properties": {"parameter": {"PRECTOTCORR": {"ANN": -999.0}}}}]}
    pts = ec.power_points(data)
    assert pts[0] == (10.0, 0.0, 2.0) and np.isnan(pts[2][2])
    g = ec.points_to_grid(pts)
    r = int((90 - 10.25) / 0.5)
    c = int((0.25 + 180) / 0.5)                                     # cell centre 10.25 N, 0.25 E -> nearest column lon 0.0
    assert g[r, c] == pytest.approx(3.0)                            # mean of the rows at 10.0 and 10.5
    with pytest.raises(ValueError):
        ec.power_points({"messages": ["error"]})


def test_missing_power_column_falls_back_to_the_neighbour():
    # no point at longitude 0 (the POWER regional API leaves it out); the cell centred at 0.25 E uses 0.625 E
    pts = [(51.5, 0.625, 2.0), (52.0, 0.625, 4.0), (51.5, -0.625, 6.0), (52.0, -0.625, 6.0)]
    g = ec.points_to_grid(pts)
    r = int((90 - 51.75) / 0.5)
    assert g[r, int((0.25 + 180) / 0.5)] == pytest.approx(3.0)
    assert g[r, int((-0.25 + 180) / 0.5)] == pytest.approx(6.0)


def test_power_points_reads_a_saved_file(tmp_path):
    f = tmp_path / "box.json"
    f.write_text(json.dumps({"features": [{"geometry": {"coordinates": [5, 5]}, "properties": {"parameter": {"PRECTOTCORR": {"ANN": 0.1}}}}]}))
    assert ec.power_points(json.loads(f.read_text())) == [(5.0, 5.0, 0.1)]


def test_dryness_score():
    s = scoring.dryness_score(np.array([10.0, 25.0, 1000.0, 3000.0, np.nan, 158.1]))
    assert s[0] == 1 and s[1] == pytest.approx(1.0) and s[2] == pytest.approx(0.0) and s[3] == 0
    assert np.isnan(s[4]) and s[5] == pytest.approx(0.5, abs=0.01)


def test_power_boxes_only_where_land():
    idx = np.array([0, 100 * 720 + 400], dtype=np.uint32)          # 89.75 N 179.75 W and 39.75 N 20.25 E
    assert earth.power_boxes(10.0, idx) == [(30.0, 20.0), (80.0, -180.0)]
    assert len(earth.power_boxes(10.0)) == 18 * 36


def test_context_criteria_appear_only_with_their_features():
    from test_scoring import make_cells
    cells = make_cells()
    assert "volcanic" not in scoring.shared_criteria(cells)
    cells.f.update({"volc_dist_km": np.array([0, 50, 300, 0, 0, 0], np.float32),
                    "volc_basalt_dist_km": np.array([300, 300, 300, 0, 0, 0], np.float32),
                    "impact_dist_km": np.zeros(6, np.float32), "precip_mm_yr": np.full(6, 25.0, np.float32)})
    sh = scoring.shared_criteria(cells)
    assert sh["volcanic"][0] == pytest.approx(0.6) and sh["volcanic"][3] == pytest.approx(1.0)
    assert sh["volcanic"][1] == pytest.approx(0.6 * np.exp(-1), rel=1e-3)
    assert (sh["impact"] == 1).all() and (sh["dryness"] == 1).all()
    assert scoring.no_data_yet(sh) == []


def test_road_points_skip_ferries_and_densify():
    data = {"features": [
        {"properties": {"type": "Major Highway"}, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
        {"properties": {"type": "Ferry Route"}, "geometry": {"type": "LineString", "coordinates": [[10.0, 10.0], [11.0, 10.0]]}},
        {"properties": {"type": "Road"}, "geometry": {"type": "MultiLineString", "coordinates": [[[20.0, 20.0], [20.05, 20.0]]]}}]}
    pts = ec.road_points(data)
    lons = sorted(p["lon"] for p in pts if abs(p["lat"] - 0.05) < 1e-9)
    assert len(lons) >= 10 and lons[0] == pytest.approx(0.05) and lons[-1] == pytest.approx(1.05)   # 111 km densified, 0.1 deg bins
    assert not any(9.9 < p["lat"] < 10.2 for p in pts)                                              # ferry left out
    assert any(abs(p["lat"] - 20.05) < 1e-9 for p in pts)


def test_road_access_filter_appears_with_the_road_layer():
    from test_scoring import make_cells
    cells = make_cells()
    assert "road_access" not in scoring.constraints(cells)
    cells.f["road_dist_km"] = np.array([0, 49, 51, 300, np.nan, 10], np.float32)
    ok = scoring.constraints(cells)["road_access"]
    assert ok.tolist() == [True, True, False, False, True, True]
