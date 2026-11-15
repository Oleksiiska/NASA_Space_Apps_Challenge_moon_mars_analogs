import numpy as np
import pytest

from analog_finder import evaluate

from test_scoring import make_cells


def _lonlat(cells, k):
    return float(cells.lat[k]), float(cells.lon[k])


def test_site_values_percentile_and_auc():
    cells = make_cells(n=6)
    score = np.array([0.9, 0.1, 0.5, np.nan, 0.3, 0.2], np.float32)   # cell 3 is not ranked
    ranks = {("t", "moon", "x"): score}
    la, lo = _lonlat(cells, 0)
    la3, lo3 = _lonlat(cells, 3)
    lan, lon_n = _lonlat(cells, 1)
    analogs = [{"id": "best", "world": "moon", "tasks": ["t"], "lat": la, "lon": lo},
               {"id": "hidden", "world": "moon", "tasks": ["t"], "lat": la3, "lon": lo3},
               {"id": "other_task", "world": "moon", "tasks": ["u"], "lat": la, "lon": lo}]
    negatives = [{"id": "n", "lat": lan, "lon": lon_n}]
    v = evaluate.site_values(cells, ranks, analogs, negatives)
    assert v["best"]["pct"] == pytest.approx(0.9) and v["best"]["auc"] == 1.0
    assert v["hidden"]["pct"] == 0.0 and v["hidden"]["auc"] == 0.0         # filtered out = not shown = 0
    assert "other_task" not in v


def test_red_flags_counts_glacier_in_top_cells():
    ice = np.array([1, 1, 0, 0, 0, 0], np.float32)
    cells = make_cells(n=6, extra={"ice_frac": ice})
    score = np.array([0.9, 0.8, 0.1, 0.1, 0.1, 0.1], np.float32)
    flags = evaluate.red_flags(cells, {("landing", "moon", "x"): score}, top_frac=0.01)
    assert flags["landing"]["glacier"] == pytest.approx(2 / 6, abs=1e-3)             # at least 10 cells -> all 6 taken


def _run(pcts):
    return {"metrics": {}, "sites": {f"s{i}": {"pct": p, "auc": p} for i, p in enumerate(pcts)}}


def test_compare_verdicts():
    rng = np.random.default_rng(3)
    base = _run(list(rng.uniform(0.2, 0.8, 20)))
    same = evaluate.compare(base, base)
    assert same["pos_pct"]["verdict"] == "same" and same["pos_pct"]["delta"] == 0
    up = _run([s["pct"] + 0.1 for s in base["sites"].values()])
    assert evaluate.compare(up, base)["pos_pct"]["verdict"] == "better"
    noisy = _run([s["pct"] + d for s, d in zip(base["sites"].values(), rng.normal(0, 0.2, 20))])
    assert evaluate.compare(noisy, base)["pos_pct"]["verdict"] in ("no clear change", "better", "worse")
    down = _run([s["pct"] - 0.1 for s in base["sites"].values()])
    assert evaluate.compare(down, base)["pos_pct"]["verdict"] == "worse"


def test_negatives_file_is_valid():
    rows = evaluate.read_negatives()
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)) >= 30
    assert all(-90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180 for r in rows)


def test_sites_for_both_worlds_count_for_moon_and_mars():
    cells = make_cells(n=6)
    score = np.linspace(0.1, 0.9, 6).astype(np.float32)
    ranks = {("t", "moon", "x"): score, ("t", "mars", "y"): score}
    la, lo = _lonlat(cells, 5)
    v = evaluate.site_values(cells, ranks, [{"id": "b", "world": "both", "tasks": ["t"], "lat": la, "lon": lo}], [])
    assert v["b"]["pairs"] == 2


def test_holdout_file_is_valid_and_apart_from_known_analogs():
    from analog_finder.prep import reference
    hold = reference.read_analogs(evaluate.holdout_path())
    assert len(hold) >= 8 and not reference.check_analogs(hold)
    known = {a["id"] for a in reference.read_analogs()}
    assert not known & {a["id"] for a in hold}
