"""Experimental machine-learning layer: positive-unlabeled (PU) learning from the known analog sites.

The formula of ``scoring.py`` says what makes a good analog from physics and the test task. This layer asks a
different question: which Earth cells look like the places agencies already chose? It learns that from the
known sites, so it can only repeat their pattern, including the habits behind it (accessibility, tradition).
It is kept apart from the formula, shown as an experimental map mode, and judged on sites it did not see.

Method
------
* Features: the Earth-only measures of every cell (terrain, temperature, vegetation, snow, minerals, dryness,
  low Sun, glaciers). Latitude and longitude are left out, and so are the volcano and impact distances and the
  road distance: those come from lists that contain many of the analog sites, so the model would just learn the
  lists back.
* Positives: cells of the known sites marked ``validate=yes`` for one world (sites for "both" count for each).
  Unlabeled: every other land cell. There are no true negatives.
* Bagged PU classifier (Mordelet and Vert 2014): many times, take all positives and a random sample of the
  unlabeled cells as if they were negatives, fit a small gradient-boosted tree model, and score the cells that
  were not in the sample. The average over bags is the ML score (0-1).
* Evaluation: spatial leave-one-site-out. Each site and everything within ``EXCLUDE_KM`` of it is removed from
  training; the model trained on the rest scores all cells; the site's percentile among all land cells is
  recorded. The formula percentile of the same site (mean over its tasks and main targets, among all land cells)
  is put next to it.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import config, scoring
from ..prep import layers

FEATURES = (["elev_mean_m", "relief_m", "slope_mean_deg", "slope_lt8", "slope_lt15", "rough_p50_m"]
            + [f"slope_h{k}" for k in range(9)]
            + ["lst_day_mean_k", "lst_night_mean_k", "lst_day_max_k", "lst_night_min_k", "lst_diurnal_k",
               "ndvi_mean", "ndvi_max", "snow_cover_pct", "snow_free_months", "precip_mm_yr", "precip_log_mm", "bare_px_frac",
               "lowsun_best_h", "lowsun_mean_h", "ice_frac",
               "min_calcite", "min_chlorite", "min_dolomite", "min_goethite", "min_gypsum", "min_hematite",
               "min_illite_muscovite", "min_kaolinite", "min_montmorillonite", "min_vermiculite", "min_quartz_feldspar"])
LEFT_OUT = ("lat", "lon", "volc_dist_km", "volc_basalt_dist_km", "impact_dist_km", "impact_diam_km", "road_dist_km",
            "volcano_dist_km", "holocene_volcano_dist_km")
EXCLUDE_KM = 300.0
N_BAGS = 40
UNLABELED_PER_POSITIVE = 20
SOURCE = "Experimental PU-learning layer (scikit-learn HistGradientBoosting), computed by ml/pu.py"


def _sklearn():
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
    except ImportError as e:
        raise ImportError('scikit-learn is not installed. Run: pip install -e "pipeline[ml]"') from e
    return HistGradientBoostingClassifier


def feature_matrix(cells: scoring.Cells, names: Optional[list[str]] = None) -> tuple[np.ndarray, list[str]]:
    """(n_cells, n_features) float32 with NaN for missing values; features absent from the grid are skipped."""
    names = [n for n in (names or FEATURES) if n in cells.f]
    return np.stack([cells.f[n].astype(np.float32) for n in names], axis=1), names


def _haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def positive_cells(cells: scoring.Cells, analogs: list[dict], world: str) -> dict[int, list[str]]:
    """Cell position -> ids of the validating sites of one world in that cell."""
    out: dict[int, list[str]] = {}
    for a in analogs:
        if a["world"] in (world, "both"):
            k = cells.site_position(a["lat"], a["lon"])
            if k >= 0:
                out.setdefault(k, []).append(a["id"])
    return out


def pu_bagging(X: np.ndarray, pos: np.ndarray, train_mask: Optional[np.ndarray] = None, n_bags: int = N_BAGS,
               ratio: int = UNLABELED_PER_POSITIVE, seed: int = 0) -> np.ndarray:
    """Bagged PU scores for all rows of X. ``pos``: indices of positives; ``train_mask``: rows allowed in training."""
    HGB = _sklearn()
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    allowed = np.ones(n, bool) if train_mask is None else train_mask.copy()
    is_pos = np.zeros(n, bool)
    is_pos[pos] = True
    pos_train = np.flatnonzero(is_pos & allowed)
    unl = np.flatnonzero(~is_pos & allowed)
    if pos_train.size < 3 or unl.size < 10:
        raise ValueError("too few positives or unlabeled cells to train")
    k = min(unl.size, ratio * pos_train.size)
    total = np.zeros(n)
    count = np.zeros(n)
    for b in range(n_bags):
        neg = rng.choice(unl, size=k, replace=False)
        idx = np.concatenate([pos_train, neg])
        y = np.concatenate([np.ones(pos_train.size), np.zeros(k)])
        w = np.where(y == 1, k / pos_train.size, 1.0)              # balance the two classes
        model = HGB(max_depth=3, max_iter=150, learning_rate=0.08, min_samples_leaf=5, l2_regularization=1.0,
                    random_state=int(rng.integers(1 << 31)))
        model.fit(X[idx], y, sample_weight=w)
        out_of_bag = np.ones(n, bool)
        out_of_bag[neg] = False                                     # a cell is scored only by bags that did not train on it
        p = model.predict_proba(X)[:, 1]
        total[out_of_bag] += p[out_of_bag]
        count[out_of_bag] += 1
    with np.errstate(invalid="ignore"):
        return (total / np.maximum(count, 1)).astype(np.float32)


def percentile_of(scores: np.ndarray, k: int) -> float:
    ok = scores[np.isfinite(scores)]
    v = scores[k]
    return float(((ok < v).sum() + 0.5 * (ok == v).sum()) / ok.size)


def leave_one_site_out(cells: scoring.Cells, X: np.ndarray, pos_cells: dict[int, list[str]], n_bags: int = 20,
                       exclude_km: float = EXCLUDE_KM, seed: int = 1, log: Callable[[str], None] = print) -> list[dict]:
    """Percentile of every positive cell when it and everything within ``exclude_km`` were hidden from training."""
    pos = np.array(sorted(pos_cells), dtype=np.int64)
    rows = []
    for j, k in enumerate(pos):
        d = _haversine_km(cells.lat[k], cells.lon[k], cells.lat, cells.lon)
        train = d > exclude_km
        s = pu_bagging(X, pos, train_mask=train, n_bags=n_bags, seed=seed + j)
        rows.append({"cell": int(k), "sites": pos_cells[int(k)], "lat": round(float(cells.lat[k]), 2), "lon": round(float(cells.lon[k]), 2),
                     "ml_percentile": round(percentile_of(s, int(k)), 3),
                     "positives_left_for_training": int((train[pos]).sum())})
        log(f"  held out {', '.join(pos_cells[int(k)])}: percentile {rows[-1]['ml_percentile']:.2f}")
    return rows


def formula_percentiles(cells: scoring.Cells, profiles: dict, analogs: list[dict], world: str) -> dict[str, float]:
    """Mean formula percentile of every site of one world over its tasks and main targets.

    Same yardstick as the ML layer: the percentile is taken among ALL land cells (scores only, no hard filters),
    and a cell without a score counts as the lowest. validation.md ranks among scored cells only, which is harder,
    so its numbers are not comparable with these.
    """
    tasks = {t["id"]: t for t in config.tasks()["tasks"]}
    shared = scoring.shared_criteria(cells)
    acc: dict[str, list[float]] = {}
    for tid, task in tasks.items():
        if world not in task["worlds"]:
            continue
        for tg in [k for k, t in profiles.items() if t["world"] == world and t.get("mvp")]:
            sc, _, _ = scoring.task_score(task, scoring.criteria_for(cells, profiles[tg], shared), world, cells, check_constraints=False)
            if not np.isfinite(sc).any():
                continue
            s = np.where(np.isfinite(sc), sc, -1.0)
            srt = np.sort(s)
            for a in analogs:
                if a["world"] not in (world, "both") or tid not in a["tasks"]:
                    continue
                k = cells.site_position(a["lat"], a["lon"])
                if k < 0:
                    continue
                lo, hi = np.searchsorted(srt, s[k], "left"), np.searchsorted(srt, s[k], "right")
                acc.setdefault(a["id"], []).append(float((lo + hi) / 2 / srt.size))
    return {k: float(np.mean(v)) for k, v in acc.items()}


def _stats(v: list[float]) -> dict:
    a = np.array([x for x in v if x is not None and math.isfinite(x)])
    if not a.size:
        return {"n": 0}
    return {"n": int(a.size), "median": round(float(np.median(a)), 3), "top20": round(float((a >= 0.8).mean()), 3),
            "top10": round(float((a >= 0.9).mean()), 3)}


def run(processed_dir: Optional[Path] = None, n_bags: int = N_BAGS, loso_bags: int = 20,
        log: Callable[[str], None] = print) -> dict:
    from ..prep import reference
    pdir = Path(processed_dir) if processed_dir else config.processed_dir()
    cells = scoring.load_cells(pdir)
    X, names = feature_matrix(cells)
    analogs = reference.read_analogs(validate_only=True)
    profiles = json.loads((pdir / "target_profiles.json").read_text(encoding="utf-8"))["targets"]
    grid = cells.meta["grid"]
    report = {"features": names, "left_out": list(LEFT_OUT), "n_bags": n_bags, "exclude_km": EXCLUDE_KM,
              "unlabeled_per_positive": UNLABELED_PER_POSITIVE, "worlds": {}}
    items = []
    for world in ("moon", "mars"):
        pos_cells = positive_cells(cells, analogs, world)
        pos = np.array(sorted(pos_cells), dtype=np.int64)
        log(f"{world}: {len(pos)} positive cells from {sum(len(v) for v in pos_cells.values())} sites; {len(names)} features")
        scores = pu_bagging(X, pos, n_bags=n_bags, seed=7 if world == "moon" else 8)
        loso = leave_one_site_out(cells, X, pos_cells, n_bags=loso_bags, log=log)
        formula = formula_percentiles(cells, profiles, analogs, world)
        for r in loso:
            fs = [formula[s] for s in r["sites"] if s in formula]
            r["formula_percentile"] = round(float(np.mean(fs)), 3) if fs else None
        report["worlds"][world] = {"positives": len(pos), "sites": sum(len(v) for v in pos_cells.values()),
                                   "held_out": loso, "ml": _stats([r["ml_percentile"] for r in loso]),
                                   "formula_same_sites": _stats([r["formula_percentile"] for r in loso])}
        full = np.full(grid["n_lat"] * grid["n_lon"], np.nan, dtype=np.float32)
        full[cells.index.astype(np.int64)] = scores
        items.append(layers.LayerFeature(f"ml_{world}", full.reshape(grid["n_lat"], grid["n_lon"]), 0.0, 1.0, "score",
                                         f"Experimental: how much the cell looks like the known {world} analog sites (PU learning)", SOURCE))
        w = report["worlds"][world]
        log(f"  {world}: held-out median percentile ML {w['ml'].get('median')} vs formula {w['formula_same_sites'].get('median')} "
            f"(top 20 %: {w['ml'].get('top20')} vs {w['formula_same_sites'].get('top20')})")
    layers.save_layer("ml_pu", items, grid["cell_deg"])
    (pdir / "ml_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (pdir / "ml_report.md").write_text(report_markdown(report), encoding="utf-8")
    return report


def report_markdown(r: dict) -> str:
    lines = ["# Experimental ML layer: positive-unlabeled learning", "",
             "The model learns which Earth cells look like the known analog sites. It can only repeat the pattern of "
             "places agencies already chose, including the reasons that have nothing to do with the Moon or Mars "
             "(access, tradition), so it is shown apart from the physics-based formula and never mixed into it.", "",
             f"- Features ({len(r['features'])}): " + ", ".join(r["features"]) + ".",
             "- Left out on purpose: " + ", ".join(r["left_out"]) + " (location, and lists that contain the sites themselves).",
             f"- Bagged PU classifier: {r['n_bags']} bags, {r['unlabeled_per_positive']} unlabeled cells per positive in each bag, "
             "gradient-boosted trees of depth 3.",
             f"- Evaluation: each site and everything within {r['exclude_km']:.0f} km of it is hidden from training; the site's "
             "percentile among all land cells is recorded. The formula column is the same site's mean percentile over its tasks "
             "and main targets, also among all land cells (scores only; a cell without a score counts as the lowest), so both "
             "columns use the same yardstick. validation.md ranks among scored cells only and is not comparable.", "",
             "| World | held-out sites | ML median percentile | ML top 20 % | formula median | formula top 20 % |",
             "|---|---|---|---|---|---|"]
    for w, d in r["worlds"].items():
        m, f = d["ml"], d["formula_same_sites"]
        lines.append(f"| {w} | {m.get('n')} | {m.get('median')} | {m.get('top20', 0):.0%} | {f.get('median')} | {f.get('top20', 0):.0%} |")
    for w, d in r["worlds"].items():
        lines += ["", f"## {w}: held-out sites", "", "| Sites in the cell | ML percentile | formula percentile |", "|---|---|---|"]
        for h in sorted(d["held_out"], key=lambda x: -x["ml_percentile"]):
            lines.append(f"| {', '.join(h['sites'])} | {h['ml_percentile']} | {h['formula_percentile']} |")
    lines += ["", "## How to read this", "",
              "- Few positives (about 20 cells per world) and no true negatives: the scores are unstable and mostly say how much a cell resembles the landscapes and climates already in the list.",
              "- A high ML score next to a low formula score means: looks like places people already use, but does not match the target for the task. The opposite means: physically similar, but unlike the usual choices; these are the candidates the challenge asks for.",
              ""]
    return "\n".join(lines)
