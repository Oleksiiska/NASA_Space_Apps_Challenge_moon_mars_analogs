import json

import numpy as np
import pytest

from analog_finder import scoring, validate
from analog_finder.export import to_binary

HIST_NAMES = scoring.HIST


def make_cells(n=6, extra=None):
    """Six cells in a row on a 360 x 720 grid; only the features the scoring reads."""
    idx = (100 * 720 + np.arange(n)).astype(np.uint32)
    z = np.zeros(n, dtype=np.float32)
    nan = np.full(n, np.nan, dtype=np.float32)
    f = {k: z.copy() for k in ["lowsun_best_h", "ice_frac", "relief_m", "rough_p50_m", "slope_lt8", "snow_free_months"]}
    f.update({k: z.copy() for k in HIST_NAMES})
    f["slope_h0"] = np.ones(n, dtype=np.float32)
    f.update({"lst_day_mean_k": np.full(n, 300, np.float32), "lst_night_mean_k": np.full(n, 285, np.float32),
              "lst_diurnal_k": np.full(n, 15, np.float32), "ndvi_mean": np.full(n, 0.02, np.float32),
              "slope_lt8": np.ones(n, np.float32), "snow_free_months": np.full(n, 12, np.float32)})
    for k in scoring.ALTERATION:
        f[k] = nan.copy()
    f.update(extra or {})
    meta = {"grid": {"cell_deg": 0.5, "n_lat": 360, "n_lon": 720, "row0_lat_center": 89.75, "col0_lon_center": -179.75}}
    lat = 89.75 - 100 * 0.5 + 0 * z
    return scoring.Cells(index=idx, lat=lat, lon=-179.75 + np.arange(n) * 0.5, f=f, meta=meta)


def test_pct_rank_ties_and_nan():
    r = scoring.pct_rank(np.array([1.0, 2.0, 2.0, 4.0, np.nan]))
    assert r[0] == pytest.approx(0.125) and r[1] == r[2] == pytest.approx(0.5) and r[3] == pytest.approx(0.875)
    assert np.isnan(r[4])


def test_log_match_is_one_at_the_target_and_falls_with_ratio():
    c = np.array([0.0, 100.0, 400.0, 1600.0])
    s = scoring._log_match(c, 400.0, 50.0)
    assert s[2] == pytest.approx(1.0) and s[1] > s[0] and s[3] < 1.0 and s.max() <= 1.0


def test_target_matches_a_cell_with_its_own_fingerprint():
    h = np.array([0.5, 0.3, 0.1, 0.05, 0.05, 0, 0, 0, 0])
    extra = {k: np.full(6, h[i], np.float32) for i, k in enumerate(HIST_NAMES)}
    cells = make_cells(extra={**extra, "relief_m": np.full(6, 800, np.float32), "rough_p50_m": np.full(6, 20, np.float32)})
    m = scoring.matched_criteria(cells, {"slope_hist": h.tolist(), "relief_p5_p95_m": 800.0, "roughness_rms_p50_m": 20.0})
    for k in scoring.MATCHED:
        assert np.allclose(m[k], 1.0, atol=1e-5)
    other = scoring.matched_criteria(cells, {"slope_hist": [0, 0, 0, 0, 0, 0, 0, 0, 1], "relief_p5_p95_m": 5000.0, "roughness_rms_p50_m": 300.0})
    assert (other["slope_hist"] < 0.1).all() and (other["relief"] < 0.2).all()


def test_task_score_uses_available_criteria_and_reports_coverage():
    cells = make_cells()
    crit = {"a": np.array([1, 0.5, np.nan, 1, 1, 1], np.float32), "b": np.array([0, 0.5, 1, np.nan, 1, 1], np.float32)}
    task = {"weights": {"a": 0.6, "b": 0.4, "c": 0.0}}
    s, cov, info = scoring.task_score(task, crit, "mars", cells, min_coverage=0.3, check_constraints=False)
    assert s[0] == pytest.approx(0.6) and s[1] == pytest.approx(0.5)
    assert s[2] == pytest.approx(1.0) and cov[2] == pytest.approx(0.4)        # only b has data: 0.4 of the weight
    assert s[3] == pytest.approx(1.0) and cov[3] == pytest.approx(0.6)        # only a
    assert info["no_data"] == ["c"]
    s2, _, _ = scoring.task_score(task, crit, "mars", cells, min_coverage=0.5, check_constraints=False)
    assert np.isnan(s2[2]) and not np.isnan(s2[3])


def test_composition_is_unknown_on_the_moon():
    cells = make_cells()
    crit = {"composition": np.ones(6, np.float32), "x": np.full(6, 0.5, np.float32)}
    task = {"weights": {"composition": 0.5, "x": 0.5}}
    sm, cm, im = scoring.task_score(task, crit, "moon", cells, check_constraints=False)
    sr, cr, _ = scoring.task_score(task, crit, "mars", cells, check_constraints=False)
    assert "composition" in im["no_data"] and sm[0] == pytest.approx(0.5) and cm[0] == pytest.approx(0.5)
    assert sr[0] == pytest.approx(0.75)


def test_constraints_remove_cells_and_unknown_passes():
    cells = make_cells(extra={"ndvi_mean": np.array([0.02, 0.6, np.nan, 0.02, 0.02, 0.02], np.float32),
                              "slope_lt8": np.array([1, 1, 1, 0.0, 1, 1], np.float32)})
    task = {"weights": {"x": 1.0}, "constraints": ["bare_ground_min", "flat_patch_exists", "road_access"]}
    s, _, info = scoring.task_score(task, {"x": np.ones(6, np.float32)}, "mars", cells)
    assert np.isnan(s[1]) and np.isnan(s[3]) and s[0] == 1 and s[2] == 1
    assert info["constraints_not_checked"] == ["road_access"]


def test_rank_of():
    s = np.array([0.1, 0.5, 0.9, np.nan], np.float32)
    assert scoring.rank_of(s, 2) == pytest.approx(2.5 / 3)
    assert np.isnan(scoring.rank_of(s, 3)) and np.isnan(scoring.rank_of(s, -1))


def test_position_of_a_point():
    cells = make_cells()
    k = cells.position(89.75 - 100 * 0.5, -179.75 + 2 * 0.5)
    assert k == 2
    assert cells.position(-60.0, 0.0) == -1


def test_summarize_and_report():
    recs = [{"analog": "a", "task": "t", "target": "x", "world": "mars", "percentile": 0.9, "percentile_filtered": 0.9, "failed_filters": [], "in_grid": True, "coverage": 1.0},
            {"analog": "b", "task": "t", "target": "x", "world": "mars", "percentile": 0.3, "percentile_filtered": None, "failed_filters": ["bare_ground_min"], "in_grid": True, "coverage": 1.0}]
    s = validate.summarize(recs)
    assert s["all"]["scores_only"]["median_percentile"] == pytest.approx(0.6)
    assert s["all"]["with_filters"]["scored"] == 1
    text = validate.report_markdown({"summary": s, "records": recs, "skipped_tasks": {"caves": "no data"}})
    assert "caves" in text and "bare_ground_min" in text


def test_export_layout(tmp_path):
    cells = make_cells()
    prof = {"t1": {"terrain_1km": {"slope_hist": [1, 0, 0, 0, 0, 0, 0, 0, 0], "relief_p5_p95_m": 10.0, "roughness_rms_p50_m": 1.0}}}
    doc = validate.export_scores(cells, prof, tmp_path)
    raw = np.fromfile(tmp_path / "criteria.bin", dtype=np.uint8)
    assert raw.size == cells.n * (len(doc["criteria"]) + 1)
    names = [(c["name"], c["target"]) for c in doc["criteria"]]
    assert ("slope_hist", "t1") in names and ("cold", None) in names
    bits = raw[doc["constraint_offset"]:]
    assert (bits & (1 << doc["constraint_bits"]["bare_ground_min"])).all()
    off = next(c["offset"] for c in doc["criteria"] if c["name"] == "slope_hist")
    assert raw[off] == 254                                                      # perfect histogram match
    off = next(c["offset"] for c in doc["criteria"] if c["name"] == "composition")
    assert (raw[off: off + cells.n] == 255).all()                               # no EMIT values: unknown, not zero
    json.loads((tmp_path / "criteria.json").read_text())


def test_snow_free_window_survives_quantisation():
    cells = make_cells(extra={"snow_free_months": np.array([0, 0.992, 1, 12, np.nan, 0.4], np.float32)})
    ok = scoring.constraints(cells)["snow_free_window"]
    assert ok.tolist() == [False, True, True, True, False, False]


def test_site_position_takes_the_nearest_land_cell_for_an_island():
    import numpy as np
    from analog_finder import scoring
    g = {"cell_deg": 0.5, "n_lat": 360, "n_lon": 720, "row0_lat_center": 89.75, "col0_lon_center": -179.75}
    rows, cols = np.array([43, 43]), np.array([386, 400])          # two land cells near 68.25 N
    index = rows * 720 + cols
    cells = scoring.Cells(index=index, lat=89.75 - rows * 0.5, lon=-179.75 + cols * 0.5, f={}, meta={"grid": g})
    assert cells.site_position(68.2, 13.2) == 0                     # own cell is land
    assert cells.site_position(68.2, 13.7) == 0                     # sea cell next to it: nearest land cell, ~20 km
    assert cells.site_position(68.2, 16.0) == -1                    # nothing within 60 km
