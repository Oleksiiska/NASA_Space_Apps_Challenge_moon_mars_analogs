import numpy as np
import pytest

from analog_finder import scoring
from analog_finder.features import roads


def test_nearest_distances_on_the_grid():
    d = roads.nearest([{"lat": 39.75, "lon": 20.25}], 0.5)        # centre of the cell at row 100, column 400
    assert d[100, 400] == pytest.approx(0.0, abs=1e-3)
    assert d[98, 400] == pytest.approx(111.2, rel=0.01)           # one degree north
    assert d[0, 0] == roads.MAX_KM                                  # far away: capped


def test_nearest_wraps_at_the_date_line():
    d = roads.nearest([{"lat": 0.25, "lon": 179.9}], 0.5)
    assert d[179, 0] < 40                                           # the cell centred at -179.75 is about 38 km away


def test_road_points_skip_ferries_and_densify():
    data = {"features": [
        {"properties": {"type": "Major Highway"}, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
        {"properties": {"type": "Ferry Route"}, "geometry": {"type": "LineString", "coordinates": [[10.0, 10.0], [11.0, 10.0]]}},
        {"properties": {"type": "Road"}, "geometry": {"type": "MultiLineString", "coordinates": [[[20.0, 20.0], [20.05, 20.0]]]}}]}
    pts = roads.road_points(data)
    lons = sorted(p["lon"] for p in pts if abs(p["lat"] - 0.05) < 1e-9)
    assert len(lons) >= 10 and lons[0] == pytest.approx(0.05) and lons[-1] == pytest.approx(1.05)
    assert not any(9.9 < p["lat"] < 10.2 for p in pts)
    assert any(abs(p["lat"] - 20.05) < 1e-9 for p in pts)


def test_road_access_filter_appears_with_the_road_layer():
    from test_scoring import make_cells
    cells = make_cells()
    assert "road_access" not in scoring.constraints(cells)
    cells.f["road_dist_km"] = np.array([0, 49, 51, 300, np.nan, 10], np.float32)
    assert scoring.constraints(cells)["road_access"].tolist() == [True, True, False, False, True, True]
