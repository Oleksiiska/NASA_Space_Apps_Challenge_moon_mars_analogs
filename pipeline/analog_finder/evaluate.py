"""Evaluation harness: one set of numbers for the ranking, and a comparison with a saved baseline.

Use it to tell whether a change to the method (a new layer, another similarity measure, other weights) made the ranking
better, worse, or changed nothing that can be told apart from noise.

    python -m analog_finder evaluate                    # compare with data/processed/eval_baseline.json
    python -m analog_finder evaluate --save-baseline    # make the current method the new baseline

Metrics (all at the level of sites, because pairs of the same site are not independent):

* ``pos_pct``: percentile of each known analog (``validate=yes`` in known_analogs.csv) in the ranking of the tasks it is
  listed for, with the hard filters on, as the web app shows it. A site that is filtered out or has too little data gets 0:
  the app does not show it. Mean over the site's task-target pairs, then mean over sites. A random site gets 0.5.
* ``auc``: chance that a known analog ranks above a place that is clearly not an analog (data/reference/negative_sites.csv:
  rainforest, farmland, wetland), in the same task and target ranking. 0.5 = no separation, 1.0 = perfect. The negatives
  are mostly vegetated, so this is an easy test: it catches regressions, it does not prove that the ranking is good.
* ``top20``: share of sites whose percentile is at least 0.8.
* Red flags: share of the top 1 % cells of a task that are mostly glacier (``ice_frac`` over 0.5), never free of snow, or
  under dense vegetation (NDVI over 0.4). Field work on a landing or rover analog cannot happen on an ice sheet
  (``isru_ice`` is exempt from the glacier flag), and geology needs exposed ground.
* ``tasks_ranked``: tasks that have at least one ranked cell.

``--holdout`` scores the sites of data/reference/holdout_analogs.csv instead: analogs that were collected after the method
was tuned on known_analogs.csv, with their tasks fixed from their sources before any score was seen. Check them once a
change is finished; tuning on them would make them one more training set.

Every metric comes with a 95 % bootstrap interval over sites. The comparison with the baseline is paired (the same sites
before and after), which is much tighter than comparing two intervals. With 17 sites, a change that the paired interval
does not separate from zero is noise.

Known analogs are not used to fit anything here. Once you start changing the method while looking at these numbers, they
stop being an independent test: keep a few new sites aside and check them only at the end.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

import numpy as np

from . import config, scoring
from .validate import _percentiles, _targets

SCHEMA = 1
N_BOOT = 2000
TOP_FRAC = 0.01
NO_GLACIER_TASKS = ("landing", "mobility", "eva_geology", "low_sun_ops", "caves", "biosignatures")


def holdout_path() -> Path:
    return config.reference_dir() / "holdout_analogs.csv"


def negatives_path() -> Path:
    return config.reference_dir() / "negative_sites.csv"


def read_negatives(path: Optional[Path] = None) -> list[dict]:
    with open(path or negatives_path(), "r", encoding="utf-8-sig", newline="") as f:
        return [{**r, "lat": float(r["lat"]), "lon": float(r["lon"])} for r in csv.DictReader(f)]


def rankings(cells: scoring.Cells, profiles: dict, tasks: dict) -> dict[tuple[str, str, str], np.ndarray]:
    """Score with hard filters for every task, world and main target; NaN = not ranked."""
    shared = scoring.shared_criteria(cells)
    out = {}
    for tid, task in tasks.items():
        for world in task["worlds"]:
            for tg in _targets(profiles, world):
                crit = scoring.criteria_for(cells, profiles[tg], shared)
                out[(tid, world, tg)], _, _ = scoring.task_score(task, crit, world, cells, check_constraints=True)
    return out


def _strict_pct(score: np.ndarray) -> np.ndarray:
    """Percentile among ranked cells; cells that are not ranked get 0 (the app does not show them)."""
    return np.nan_to_num(_percentiles(score), nan=0.0)


def site_values(cells: scoring.Cells, ranks: dict, analogs: list[dict], negatives: list[dict]) -> dict[str, dict]:
    """Per validating site: mean percentile and mean AUC against the negatives over its task-target pairs."""
    pct_cache = {k: _strict_pct(v) for k, v in ranks.items()}
    neg_pos = [cells.position(n["lat"], n["lon"]) for n in negatives]
    neg_pos = [k for k in neg_pos if k >= 0]
    out = {}
    for a in analogs:
        k = cells.position(a["lat"], a["lon"])
        pcts, aucs = [], []
        for (tid, world, tg), p in pct_cache.items():
            if a["world"] not in (world, "both") or tid not in a["tasks"]:
                continue
            v = float(p[k]) if k >= 0 else 0.0
            pcts.append(v)
            if neg_pos:
                n = p[neg_pos]
                aucs.append(float(np.mean((v > n) + 0.5 * (v == n))))
        if pcts:
            out[a["id"]] = {"pct": float(np.mean(pcts)), "auc": float(np.mean(aucs)) if aucs else float("nan"),
                            "pairs": len(pcts), "in_grid": k >= 0}
    return out


def red_flags(cells: scoring.Cells, ranks: dict, top_frac: float = TOP_FRAC) -> dict[str, dict]:
    """Per task: share of the top cells that are mostly glacier, never free of snow, or under dense vegetation (NDVI over
    0.4; field geology needs exposed ground). Mean over targets."""
    ice = cells.f["ice_frac"]
    snow = cells.f.get("snow_free_months")
    ndvi = cells.f.get("ndvi_mean")
    acc: dict[str, list] = {}
    for (tid, _, _), sc in ranks.items():
        ok = np.isfinite(sc)
        if not ok.any():
            continue
        k = max(10, int(top_frac * ok.sum()))
        top = np.argsort(-np.nan_to_num(sc, nan=-1.0))[:k]
        glacier = float(np.mean(ice[top] > 0.5))
        no_thaw = float(np.mean(snow[top] == 0)) if snow is not None else float("nan")
        green = float(np.mean(ndvi[top] > 0.4)) if ndvi is not None else float("nan")
        acc.setdefault(tid, []).append((glacier, no_thaw, green))
    return {t: {"glacier": round(float(np.mean([x[0] for x in v])), 3), "never_snow_free": round(float(np.mean([x[1] for x in v])), 3),
                "dense_vegetation": round(float(np.mean([x[2] for x in v])), 3)} for t, v in sorted(acc.items())}


def _boot_ci(x: np.ndarray, rng: np.random.Generator, n_boot: int = N_BOOT, stat=np.mean) -> list[float]:
    if x.size == 0:
        return [float("nan"), float("nan")]
    b = [stat(rng.choice(x, x.size)) for _ in range(n_boot)]
    return [round(float(v), 3) for v in np.percentile(b, [2.5, 97.5])]


def evaluate(cells: scoring.Cells, profiles: dict, analogs: list[dict], negatives: list[dict],
             tasks: Optional[dict] = None, seed: int = 0) -> dict:
    tasks = tasks or {t["id"]: t for t in config.tasks()["tasks"]}
    ranks = rankings(cells, profiles, tasks)
    sites = site_values(cells, ranks, analogs, negatives)
    rng = np.random.default_rng(seed)
    pct = np.array([s["pct"] for s in sites.values()])
    auc = np.array([s["auc"] for s in sites.values() if np.isfinite(s["auc"])])
    flags = red_flags(cells, ranks)
    glacier = [v["glacier"] for t, v in flags.items() if t in NO_GLACIER_TASKS]
    green = [v["dense_vegetation"] for v in flags.values()]
    ranked = sorted({tid for (tid, _, _), sc in ranks.items() if np.isfinite(sc).any()})
    metrics = {
        "pos_pct": {"value": round(float(pct.mean()), 3), "ci95": _boot_ci(pct, rng)},
        "auc": {"value": round(float(auc.mean()), 3), "ci95": _boot_ci(auc, rng)},
        "top20": {"value": round(float((pct >= 0.8).mean()), 3), "ci95": _boot_ci((pct >= 0.8).astype(float), rng)},
        "glacier_in_top": {"value": round(float(np.mean(glacier)), 3) if glacier else None},
        "green_in_top": {"value": round(float(np.mean(green)), 3) if green else None},
        "tasks_ranked": {"value": len(ranked), "of": len(tasks)},
    }
    neg_in = sum(cells.position(n["lat"], n["lon"]) >= 0 for n in negatives)
    return {"schema": SCHEMA, "n_sites": len(sites), "n_negatives": int(neg_in), "metrics": metrics,
            "red_flags": flags, "tasks_ranked": ranked, "sites": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                                                                     for kk, vv in v.items()} for k, v in sites.items()}}


def compare(cur: dict, base: dict, seed: int = 0, n_boot: int = N_BOOT) -> dict:
    """Paired change per metric over the sites both runs share: mean change and its 95 % bootstrap interval."""
    common = sorted(set(cur["sites"]) & set(base["sites"]))
    rng = np.random.default_rng(seed)
    out = {}
    for key, get in (("pos_pct", lambda s: s["pct"]), ("auc", lambda s: s["auc"]), ("top20", lambda s: float(s["pct"] >= 0.8))):
        d = np.array([get(cur["sites"][s]) - get(base["sites"][s]) for s in common], dtype=float)
        d = d[np.isfinite(d)]
        ci = _boot_ci(d, rng, n_boot)
        verdict = "better" if ci[0] > 0 else "worse" if ci[1] < 0 else "no clear change"
        if d.size and np.allclose(d, 0):
            verdict = "same"
        out[key] = {"delta": round(float(d.mean()), 3) if d.size else None, "ci95": ci, "verdict": verdict}
    moved = sorted(((cur["sites"][s]["pct"] - base["sites"][s]["pct"], s) for s in common), key=lambda x: -abs(x[0]))
    out["sites_moved_most"] = [{"site": s, "delta_pct": round(float(d), 3)} for d, s in moved[:5] if abs(d) > 1e-6]
    out["sites_only_in_current"] = sorted(set(cur["sites"]) - set(base["sites"]))
    out["sites_only_in_baseline"] = sorted(set(base["sites"]) - set(cur["sites"]))
    return out


def format_report(cur: dict, cmp: Optional[dict] = None, base: Optional[dict] = None) -> str:
    m = cur["metrics"]
    lines = [f"Sites: {cur['n_sites']} known analogs, {cur['n_negatives']} negatives. Random ranking: pos_pct 0.5, auc 0.5, top20 0.2.", ""]
    head = f"{'metric':16s} {'current':>8s}  {'95% CI':15s}"
    if base:
        head += f" {'baseline':>9s} {'change':>8s}  {'paired 95% CI':17s} verdict"
    lines.append(head)
    for key in ("pos_pct", "auc", "top20"):
        ci = m[key]["ci95"]
        row = f"{key:16s} {m[key]['value']:8.3f}  [{ci[0]:.3f}, {ci[1]:.3f}] "
        if base and cmp:
            c = cmp[key]
            row += f" {base['metrics'][key]['value']:9.3f} {c['delta']:+8.3f}  [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]  {c['verdict']}"
        lines.append(row)
    g = m["glacier_in_top"]["value"]
    row = f"{'glacier_in_top':16s} {g if g is not None else float('nan'):8.3f}  (lower is better; tasks other than isru_ice)"
    if base:
        row += f"  baseline {base['metrics']['glacier_in_top']['value']}"
    lines.append(row)
    gv = m.get("green_in_top", {}).get("value")
    row = f"{'green_in_top':16s} {gv if gv is not None else float('nan'):8.3f}  (lower is better; NDVI over 0.4, all tasks)"
    if base:
        row += f"  baseline {base['metrics'].get('green_in_top', {}).get('value')}"
    lines.append(row)
    row = f"{'tasks_ranked':16s} {m['tasks_ranked']['value']:8d}  of {m['tasks_ranked']['of']}"
    if base:
        row += f"  baseline {base['metrics']['tasks_ranked']['value']}"
    lines.append(row)
    lines += ["", "Red flags in the top 1 % of each task (share of cells):",
              f"  {'task':14s} {'glacier':>8s} {'never snow-free':>16s} {'dense vegetation':>17s}"]
    for t, v in cur["red_flags"].items():
        lines.append(f"  {t:14s} {v['glacier']:8.0%} {v['never_snow_free']:16.0%} {v.get('dense_vegetation', float('nan')):17.0%}")
    if cmp and cmp["sites_moved_most"]:
        lines += ["", "Sites that moved most: " + ", ".join(f"{x['site']} {x['delta_pct']:+.3f}" for x in cmp["sites_moved_most"])]
    if cmp and (cmp["sites_only_in_current"] or cmp["sites_only_in_baseline"]):
        lines.append(f"Site list changed: new {cmp['sites_only_in_current']}, gone {cmp['sites_only_in_baseline']}. Only shared sites are compared.")
    return "\n".join(lines)


def run(processed_dir: Optional[Path] = None, save_baseline: bool = False, baseline: Optional[Path] = None,
        holdout: bool = False, log=print) -> dict:
    from .prep import reference
    pdir = Path(processed_dir) if processed_dir else config.processed_dir()
    cells = scoring.load_cells(pdir)
    profiles = json.loads((pdir / "target_profiles.json").read_text(encoding="utf-8"))["targets"]
    if holdout:
        cur = evaluate(cells, profiles, reference.read_analogs(holdout_path(), validate_only=True), read_negatives())
        (pdir / "eval_holdout.json").write_text(json.dumps(cur, indent=1), encoding="utf-8")
        log("HOLD-OUT SITES (data/reference/holdout_analogs.csv). Look at them only to check a finished method, never to tune it.\n")
        log(format_report(cur))
        log("\nPer site (percentile, 1.0 = best cell on Earth; 0 = filtered out or no data):")
        for k, v in sorted(cur["sites"].items(), key=lambda kv: -kv[1]["pct"]):
            log(f"  {k:22s} {v['pct']:.3f}  ({v['pairs']} task-target pairs)")
        return cur
    cur = evaluate(cells, profiles, reference.read_analogs(validate_only=True), read_negatives())
    (pdir / "eval_current.json").write_text(json.dumps(cur, indent=1), encoding="utf-8")
    bpath = Path(baseline) if baseline else pdir / "eval_baseline.json"
    if save_baseline:
        bpath.write_text(json.dumps(cur, indent=1), encoding="utf-8")
        log(format_report(cur))
        log(f"\nSaved as the baseline: {bpath}")
        return cur
    if not bpath.exists():
        log(format_report(cur))
        log(f"\nNo baseline at {bpath}. Save one with: python -m analog_finder evaluate --save-baseline")
        return cur
    base = json.loads(bpath.read_text(encoding="utf-8"))
    cmp = compare(cur, base)
    log(format_report(cur, cmp, base))
    return {**cur, "comparison": cmp}
