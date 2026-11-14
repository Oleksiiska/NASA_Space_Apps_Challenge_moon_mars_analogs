import csv
import json
import shutil

import numpy as np
import pytest

from analog_finder import config
from analog_finder.export import to_binary
from analog_finder.fetch import earth
from analog_finder.prep import grid as grid_mod
from analog_finder.prep import reference

from conftest import REPO

ANALOGS = REPO / "data" / "reference" / "known_analogs.csv"


def test_known_analogs_table_is_consistent(project):
    rows = reference.read_analogs(ANALOGS)
    assert len(rows) >= 30
    assert reference.check_analogs(rows) == []
    by_id = {r["id"]: r for r in rows}

    h = by_id["haughton"]
    assert abs(h["lat"] - 75.383) < 0.01 and abs(h["lon"] + 89.667) < 0.01
    assert h["coord_quality"] == "verified" and h["validate"] and "low_sun_ops" in h["tasks"]
    assert by_id["neemo"]["validate"] is False and by_id["neemo"]["tasks"] == []
    assert by_id["dallol"]["kind"] == ["hydrothermal", "evaporite"]

    for r in rows:
        if r["coord_quality"] == "approx":          # an approximate point says so in its notes
            assert "memory" in r["notes"].lower(), r["id"]
        if not r["use_checked"]:                    # an unread source is flagged in the text
            assert "to confirm" in r["used_by"], r["id"]
    only = reference.read_analogs(ANALOGS, validate_only=True)
    assert len(only) == sum(r["validate"] for r in rows) and all(r["validate"] for r in only)

    # the same file feeds `fetch power` and `fetch copdem`
    points = earth.read_points(ANALOGS)
    assert len(points) == len(rows) and points[0]["id"] == rows[0]["id"]


def test_check_analogs_reports_problems(project):
    bad = [
        {"id": "a", "lat": 95.0, "lon": 10.0, "world": "venus", "coord_quality": "verified", "coord_source": "",
         "tasks": ["nope"], "validate": True},
        {"id": "a", "lat": 10.0, "lon": 10.0, "world": "moon", "coord_quality": "guess", "coord_source": "",
         "tasks": [], "validate": True},
    ]
    problems = "\n".join(reference.check_analogs(bad))
    for needle in ("out of range", "world must be", "need coord_source", "unknown task ids", "duplicate id",
                   "coord_quality must be", "at least one task"):
        assert needle in problems, needle


def test_read_points_tolerates_a_bom(tmp_path):
    path = tmp_path / "points.csv"
    path.write_bytes("﻿id,lat,lon\nkyiv,50.45,30.52\nbroken,x,y\n".encode("utf-8"))
    assert earth.read_points(path) == [{"id": "kyiv", "lat": 50.45, "lon": 30.52}]


def test_targets_geojson(project):
    gj = reference.targets_geojson()
    assert [f["properties"]["id"] for f in gj["features"]] == [t["id"] for t in config.targets()["targets"]]
    ridge = gj["features"][0]
    assert ridge["geometry"]["coordinates"] == [-163.261, -89.684]          # 196.739 E -> -163.261
    assert ridge["properties"]["lon_e"] == 196.739 and ridge["properties"]["radius_km"] == 15.0
    assert all(-180.0 <= f["geometry"]["coordinates"][0] <= 180.0 for f in gj["features"])
    assert {f["properties"]["world"] for f in gj["features"]} == {"moon", "mars"}
    json.dumps(gj)


def test_committed_layers_match_their_sources(project):
    """targets.geojson and known_analogs.geojson are generated files: they must follow the YAML and the CSV."""
    hint = "run `python -m analog_finder reference` and commit the result"
    with open(REPO / "data" / "reference" / "targets.geojson", encoding="utf-8") as f:
        assert json.load(f) == reference.targets_geojson(), hint
    with open(REPO / "data" / "reference" / "known_analogs.geojson", encoding="utf-8") as f:
        assert json.load(f) == reference.analogs_geojson(reference.read_analogs(ANALOGS)), hint


def test_write_reference_with_a_small_grid(project):
    shutil.copy(ANALOGS, project / "data" / "reference" / "known_analogs.csv")
    n_lon = 720
    cells = sorted(r * n_lon + c for r, c in (grid_mod.cell_of(75.383333, -89.666667), grid_mod.cell_of(31.97194, -106.96472)))
    index = np.array(cells, dtype=np.uint32)                     # Haughton first (further north), then Kilbourne Hole
    feats = [to_binary.Feature("lowsun_best_h", np.array([4.35, 0.94]), 0.0, 24.0, "hours/day"),
             to_binary.Feature("lowsun_best_month", np.array([8.0, 12.0]), 1.0, 12.0, "month")]
    to_binary.write_grid(project / "data" / "processed", index, (360, n_lon), 0.5, feats)

    written = reference.write_reference(log=lambda s: None)
    assert {p.name for p in written} == {"targets.geojson", "known_analogs.geojson", "analogs_grid.csv"}
    with open(project / "data" / "processed" / "analogs_grid.csv", encoding="utf-8", newline="") as f:
        table = {r["id"]: r for r in csv.DictReader(f)}
    assert table["haughton"]["in_grid"] == "yes" and table["haughton"]["cell_index"] == "0"
    assert float(table["haughton"]["lowsun_best_h"]) == pytest.approx(4.35, abs=0.06)
    assert table["haughton"]["lowsun_best_month"] == "8"
    assert table["kilbourne_hole"]["cell_index"] == "1" and table["kilbourne_hole"]["lowsun_best_month"] == "12"
    assert table["atacama"]["in_grid"] == "no" and table["atacama"]["lowsun_best_h"] == ""
    with open(project / "data" / "reference" / "known_analogs.geojson", encoding="utf-8") as f:
        gj = json.load(f)
    assert len(gj["features"]) == len(table)
    assert gj["features"][0]["geometry"]["coordinates"] == [-111.6318, 35.5822]


def test_write_reference_without_analogs_or_grid(project):
    written = reference.write_reference(log=lambda s: None)
    assert [p.name for p in written] == ["targets.geojson"]


def test_every_dataset_is_documented():
    text = (REPO / "docs" / "data_sources.md").read_text(encoding="utf-8")
    for ds in config.sources()["datasets"]:
        assert f"`{ds['id']}`" in text, f"{ds['id']} is missing in docs/data_sources.md"
