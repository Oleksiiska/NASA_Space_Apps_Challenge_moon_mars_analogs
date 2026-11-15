import json

import numpy as np
import pytest

from analog_finder import scoring
from analog_finder.features import context as ctx

from test_scoring import make_cells

WIKI = """Intro
===10 Ma or more===
{| class="wikitable sortable"
!Name
!Location
!Country
!Diameter  (km)
!Age (million years)
!Coordinates
|-
|[[Sudbury Basin|Sudbury]]
|[[Ontario]]
|Canada
|{{sort|.01300|130}}
|{{sort|.18490|1849}}
|{{coord|46|36|N|81|11|W|name=Sudbury}}
|-
|[[Gweni-Fada crater|Gweni-Fada]]
|Ennedi
|Chad
|22
|less than 383
|
|-
|[[Jinlin Crater|Jinlin]]
|Guangdong
|China
|{{0|00}}0.9
|<&nbsp;10
|{{coord|23.3|111.8}}
|}

== Inferred impact events ==
{| class="wikitable"
|-
|[[Shiva crater|Shiva]]
|ocean
|India
|500
|66
|{{coord|18|N|70|E}}
|}
"""


def test_parse_coord_forms():
    assert ctx.parse_coord("{{coord|46|36|N|81|11|W|name=Sudbury}}") == pytest.approx((46.6, -81.18333), abs=1e-4)
    assert ctx.parse_coord("{{coord|23.3|111.8}}") == pytest.approx((23.3, 111.8))
    assert ctx.parse_coord("{{coord|27|0|S|27|30|E||name=Vredefort}}") == pytest.approx((-27.0, 27.5))
    assert ctx.parse_coord("{{coord|10|20|30|N|5|0|0|W}}") == pytest.approx((10 + 20 / 60 + 30 / 3600, -5.0))
    assert ctx.parse_coord("{{coord|abc}}") is None


def test_parse_wikipedia_keeps_confirmed_rows_only():
    rows = ctx.parse_wikipedia_impacts(WIKI)
    names = [r["name"] for r in rows]
    assert names == ["Sudbury", "Gweni-Fada", "Jinlin"]                  # the inferred table is ignored
    assert rows[0]["diameter_km"] == 130 and rows[2]["diameter_km"] == pytest.approx(0.9)
    assert rows[1]["lat"] is None


def test_merge_takes_missing_coordinates_by_name_and_skips_unconfirmed():
    rows = ctx.parse_wikipedia_impacts(WIKI)
    wd = ctx.parse_wikidata_impacts({"results": {"bindings": [
        {"itemLabel": {"value": "Gweni-Fada crater"}, "lat": {"value": "17.4"}, "lon": {"value": "21.75"}},
        {"itemLabel": {"value": "Shiva crater"}, "lat": {"value": "18"}, "lon": {"value": "70"}},
    ]}})
    out = ctx.merge_impacts(rows, wd)
    assert [r["name"] for r in out] == ["Sudbury", "Gweni-Fada", "Jinlin"]
    assert out[1]["lat"] == pytest.approx(17.4) and out[1]["diameter_km"] == 22
    assert ctx.norm_name("Nördlinger Ries crater") == ctx.norm_name("Nordlinger Ries")


def test_nearest_km_is_zero_inside_the_cell_and_wraps_the_date_line():
    lat, lon = np.array([0.25, 0.25]), np.array([0.25, 179.75])
    d = ctx.nearest_km(lat, lon, np.array([0.4]), np.array([0.1]), half_deg=0.25)
    assert d[0] == pytest.approx(0.0, abs=1e-6)
    d2 = ctx.nearest_km(lat[1:], lon[1:], np.array([0.25]), np.array([-179.9]), half_deg=0.25)
    assert d2[0] == pytest.approx(0.1 * 111.19, rel=0.01)                 # across 180 degrees, not around the globe
    r = ctx.nearest_km(lat[:1], lon[:1], np.array([0.25]), np.array([2.25]), radius_km=np.array([100.0]), half_deg=0.25)
    assert r[0] == pytest.approx(1.75 * 111.19 - 100.0, rel=0.01)           # from the cell edge to the rim


def test_proximity_and_context_criteria():
    p = scoring.proximity(np.array([0.0, 25.0, 87.5, 150.0, 400.0, np.nan]))
    assert p[:5] == pytest.approx([1.0, 1.0, 0.5, 0.0, 0.0]) and np.isnan(p[5])
    cells = make_cells()
    assert scoring.no_data(scoring.shared_criteria(cells)) == ["dryness", "volcanic", "impact"]
    cells = make_cells(extra={"volcano_dist_km": np.zeros(6, np.float32), "impact_dist_km": np.full(6, 500, np.float32)})
    sh = scoring.shared_criteria(cells)
    assert scoring.no_data(sh) == ["dryness"] and (sh["volcanic"] == 1).all() and (sh["impact"] == 0).all()


def test_reference_lists_are_valid():
    for path in (ctx.volcanoes_csv(), ctx.impacts_csv()):
        rows = ctx._read_csv(path)
        assert len(rows) > 50
        assert all(-90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180 for r in rows)
