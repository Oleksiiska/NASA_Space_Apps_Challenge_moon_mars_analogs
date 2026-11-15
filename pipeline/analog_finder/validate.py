"""Validation of the ranking against known analog sites, and export of the scores for the web app.

Known analogs are never used to set weights or thresholds. They are only looked up: for every site marked ``validate=yes`` and
every task it is listed for, the score of its cell is turned into a percentile among all ranked cells of that task and target.
A site picked at random would land near 0.5 (and in the top 20 % one time in five).

Two caveats shown in every report: a site is a few hundred metres to a few kilometres across and a cell is about 55 km; and
criteria without data yet (volcanic, impact, dryness) are missing from the tasks that use them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from . import config, scoring
from .export import to_binary

SCHEMA = 1
CONTEXT_CRITERIA = ("volcanic", "impact")     # built from point lists that include many analog sites themselves


def _targets(profiles: dict, world: str, mvp_only: bool = True) -> list[str]:
    return [k for k, t in profiles.items() if t["world"] == world and (t.get("mvp") or not mvp_only)]


def _percentiles(score: np.ndarray) -> np.ndarray:
    ok = np.isfinite(score)
    out = np.full(score.shape, np.nan)
    if ok.any():
        srt = np.sort(score[ok])
        lo = np.searchsorted(srt, score[ok], side="left")
        hi = np.searchsorted(srt, score[ok], side="right")
        out[ok] = (lo + hi) / 2.0 / ok.sum()
    return out


def validate(cells: scoring.Cells, profiles: dict, analogs: list[dict], tasks: Optional[dict] = None) -> dict:
    """Percentile of every validating analog for every task and main target of its world, with and without hard filters."""
    tasks = tasks or {t["id"]: t for t in config.tasks()["tasks"]}
    shared = scoring.shared_criteria(cells)
    cons = scoring.constraints(cells)
    records = []
    skipped: dict[str, str] = {}
    for tid, task in tasks.items():
        for world in task["worlds"]:
            for tg in _targets(profiles, world):
                crit = scoring.criteria_for(cells, profiles[tg], shared)
                sc_free, cov, info = scoring.task_score(task, crit, world, cells, check_constraints=False)
                if not np.isfinite(sc_free).any():
                    skipped[tid] = "no cell has enough data (missing: " + ", ".join(info["no_data"]) + ")"
                    continue
                sc_filt, _, _ = scoring.task_score(task, crit, world, cells, check_constraints=True)
                p_free, p_filt = _percentiles(sc_free), _percentiles(sc_filt)
                for a in analogs:
                    if a["world"] not in (world, "both") or tid not in a["tasks"]:
                        continue
                    k = cells.site_position(a["lat"], a["lon"])
                    rec = {"analog": a["id"], "task": tid, "target": tg, "world": world, "in_grid": k >= 0,
                           "coverage": round(float(cov[k]), 2) if k >= 0 else None}
                    for tag, p in (("percentile", p_free), ("percentile_filtered", p_filt)):
                        rec[tag] = round(float(p[k]), 3) if k >= 0 and np.isfinite(p[k]) else None
                    rec["failed_filters"] = [c for c in task.get("constraints", []) if c in cons and c not in task.get("constraints_off", [])
                                             and k >= 0 and not cons[c][k]]
                    records.append(rec)
    ctx = sorted(t for t, d in tasks.items() if any(d["weights"].get(c, 0) > 0 for c in CONTEXT_CRITERIA))
    return {"schema": SCHEMA, "records": records, "skipped_tasks": skipped, "summary": summarize(records, ctx)}


def sensitivity(cells: scoring.Cells, profiles: dict, tasks: Optional[dict] = None, n_draws: int = 30,
                top_frac: float = 0.05, spread: float = 0.25, seed: int = 1) -> dict:
    """Stability of the ranking when every weight of a task is changed by up to +-25 %.

    For each task and main target: share of the baseline top 5 % cells that stay in the top 5 % after each random change of
    the weights (mean over draws). 1.0 = the same cells every time. Also the share of top cells in dense vegetation
    (NDVI over 0.4), which should be near zero.
    """
    tasks = tasks or {t["id"]: t for t in config.tasks()["tasks"]}
    rng = np.random.default_rng(seed)
    shared = scoring.shared_criteria(cells)
    ndvi = cells.f["ndvi_mean"]
    rows = []
    for tid, task in tasks.items():
        for world in task["worlds"]:
            for tg in _targets(profiles, world):
                crit = scoring.criteria_for(cells, profiles[tg], shared)
                base, _, _ = scoring.task_score(task, crit, world, cells)
                ok = np.isfinite(base)
                if ok.sum() < 100:
                    continue
                k = max(10, int(top_frac * ok.sum()))
                top = np.argsort(-np.nan_to_num(base, nan=-1))[:k]
                overlaps = []
                for _ in range(n_draws):
                    w = {n: v * (1 + rng.uniform(-spread, spread)) for n, v in task["weights"].items()}
                    sc, _, _ = scoring.task_score(task, crit, world, cells, weights=w)
                    top2 = set(np.argsort(-np.nan_to_num(sc, nan=-1))[:k].tolist())
                    overlaps.append(len(top2.intersection(top.tolist())) / k)
                dense = float(np.mean(ndvi[top] > 0.4)) if np.isfinite(ndvi[top]).any() else None
                rows.append({"task": tid, "target": tg, "top_cells": int(k), "mean_overlap": round(float(np.mean(overlaps)), 3),
                             "min_overlap": round(float(np.min(overlaps)), 3), "share_dense_vegetation": None if dense is None else round(dense, 3)})
    by_task = {}
    for t in sorted({r["task"] for r in rows}):
        rr = [r for r in rows if r["task"] == t]
        by_task[t] = {"mean_overlap": round(float(np.mean([r["mean_overlap"] for r in rr])), 3),
                      "share_dense_vegetation": round(float(np.mean([r["share_dense_vegetation"] or 0 for r in rr])), 3)}
    return {"spread": spread, "draws": n_draws, "top_fraction": top_frac, "rows": rows, "by_task": by_task}


def summarize(records: list[dict], context_tasks: Optional[list[str]] = None) -> dict:
    def stats(key: str, rows: list[dict]) -> dict:
        v = np.array([r[key] for r in rows if r[key] is not None], dtype=float)
        return {"pairs": len(rows), "scored": int(v.size),
                "median_percentile": round(float(np.median(v)), 3) if v.size else None,
                "share_top20": round(float((v >= 0.8).mean()), 3) if v.size else None,
                "share_top10": round(float((v >= 0.9).mean()), 3) if v.size else None,
                "share_above_median": round(float((v > 0.5).mean()), 3) if v.size else None}
    out = {"random_expectation": {"median_percentile": 0.5, "share_top20": 0.2, "share_top10": 0.1},
           "all": {"scores_only": stats("percentile", records), "with_filters": stats("percentile_filtered", records)},
           "context_tasks": list(context_tasks or []),
           "by_task": {}}
    indep = [r for r in records if r["task"] not in set(context_tasks or [])]
    out["independent"] = {"scores_only": stats("percentile", indep), "with_filters": stats("percentile_filtered", indep)}
    for t in sorted({r["task"] for r in records}):
        rows = [r for r in records if r["task"] == t]
        out["by_task"][t] = {"scores_only": stats("percentile", rows), "with_filters": stats("percentile_filtered", rows)}
    return out


def report_markdown(result: dict) -> str:
    s = result["summary"]
    a = s["all"]["scores_only"]
    f = s["all"]["with_filters"]
    lines = ["# Validation against known analog sites", "",
             "Each site is a cell of the 0.5 degree grid; its score is turned into a percentile among all ranked cells "
             "(1.0 = best cell on Earth for that task and target). A random site would get a median of 0.5 and land in the top 20 % one time in five. "
             "Known analogs were not used to set any weight or threshold.", "",
             f"- Scores only: {a['scored']} of {a['pairs']} site-task-target pairs scored, median percentile {a['median_percentile']}, "
             f"top 20 % in {a['share_top20']:.0%}, top 10 % in {a['share_top10']:.0%}.",
             f"- With the hard filters of each task: {f['scored']} pairs left, median {f['median_percentile']}, top 20 % in {f['share_top20']:.0%}. "
             "Filters remove sites whose 55 km cell is mostly vegetated although the site itself is bare (impact craters in forest, volcanic islands) and the ice-sheet cell of the McMurdo Dry Valleys. The road filter of rover mobility is off by default and not applied here.",
             f"- Independent part: the tasks {', '.join(s.get('context_tasks', [])) or '(none)'} use the volcano and impact lists, and those lists contain many "
             "of the analog sites themselves, so their high percentiles show that the layers work, not that the method finds analogs on its own. "
             f"Without them: {s['independent']['scores_only']['scored']} pairs, median percentile {s['independent']['scores_only']['median_percentile']}, "
             f"top 20 % in {s['independent']['scores_only']['share_top20']:.0%}, top 10 % in {s['independent']['scores_only']['share_top10']:.0%}.", "",
             "| Task | pairs | median percentile | top 20 % | top 10 % |", "|---|---|---|---|---|"]
    for t, d in s["by_task"].items():
        x = d["scores_only"]
        lines.append(f"| {t} | {x['scored']} | {x['median_percentile']} | {x['share_top20']:.0%} | {x['share_top10']:.0%} |")
    for t, why in result["skipped_tasks"].items():
        lines.append(f"| {t} | 0 | not ranked: {why} | | |")
    lines += ["", "## Per site", "", "| Site | Task | Target | Percentile | With filters | Failed filters |", "|---|---|---|---|---|---|"]
    for r in sorted(result["records"], key=lambda r: (r["task"], r["analog"], r["target"])):
        lines.append(f"| {r['analog']} | {r['task']} | {r['target']} | {r['percentile']} | {r['percentile_filtered']} | {', '.join(r['failed_filters']) or ''} |")
    sens = result.get("sensitivity")
    if sens:
        lines += ["", "## Stability when the weights change", "",
                  f"Every weight of a task was changed at random by up to +-{int(sens['spread'] * 100)} % ({sens['draws']} draws). "
                  f"Share of the baseline top {int(sens['top_fraction'] * 100)} % cells that stay in the top {int(sens['top_fraction'] * 100)} % (1.0 = unchanged), "
                  "and the share of those top cells under dense vegetation (NDVI over 0.4; should be near zero, though the bare-ground filter removes dense vegetation by construction).", "",
                  "| Task | stays in top 5 % | dense vegetation in top |", "|---|---|---|"]
        for t, d in sens["by_task"].items():
            lines.append(f"| {t} | {d['mean_overlap']:.0%} | {d['share_dense_vegetation']:.0%} |")
        lines += ["", "No spatial hold-out is run: no weight or threshold is fitted to the known sites, so every site is already unseen by the method."]
    lines += ["", "## How to read this", "",
              "- A cell is about 55 km across; a site is much smaller. A flat Martian plain (Arcadia) is rarely matched by a whole cell.",
              "- Earth cannot reach lunar or Martian cold, vacuum or radiation. Cold, thermal range and low Sun are ranked in the useful direction only.",
              "- Volcanic fields and impact structures enter as distance to the nearest listed point or rim; dryness comes from NASA POWER precipitation when its layer was built.",
              ""]
    return "\n".join(lines)


# ------------------------------------------------------------------ export for the web app

def export_scores(cells: scoring.Cells, profiles: dict, out_dir: Optional[Path] = None) -> dict:
    """Write criteria.bin (uint8, 0..254 = score 0..1, 255 = no data) and criteria.json.

    Layout: the shared criteria first, then the three target-matched criteria of every target, then one byte per cell of
    hard-filter bits. The page computes weighted sums from these; weights come from tasks.yaml and the sliders.
    """
    out_dir = Path(out_dir) if out_dir else config.processed_dir()
    shared = scoring.shared_criteria(cells)
    blocks, meta = [], []

    def add(name: str, values: np.ndarray, target: Optional[str] = None) -> None:
        q = np.where(np.isfinite(values), np.rint(np.clip(values, 0, 1) * 254), 255).astype(np.uint8)
        meta.append({"name": name, "target": target, "offset": len(blocks) * cells.n})
        blocks.append(q)

    for name in scoring.SHARED:
        if name in shared:
            add(name, shared[name])
    for tg, prof in profiles.items():
        for name, v in scoring.matched_criteria(cells, prof["terrain_1km"]).items():
            add(name, v, tg)
    cons = scoring.constraints(cells)
    bits = np.zeros(cells.n, dtype=np.uint8)
    names = list(cons)
    for i, c in enumerate(names):
        bits |= (cons[c].astype(np.uint8) << i)
    blocks.append(bits)
    doc = {"schema": SCHEMA, "n_cells": cells.n, "scale": "uint8 0..254 -> 0..1, 255 no data", "criteria": meta,
           "constraint_bits": {c: i for i, c in enumerate(names)}, "constraints_not_checked": [c for c in scoring.NOT_CHECKED if c not in cons],
           "road_max_km": scoring.ROAD_MAX_KM,
           "constraint_offset": len(meta) * cells.n, "min_coverage": scoring.MIN_COVERAGE,
           "no_data_yet": scoring.no_data(shared), "composition_worlds": ["mars"],
           "tasks": config.tasks()["tasks"]}
    np.concatenate(blocks).tofile(out_dir / "criteria.bin")
    with open(out_dir / "criteria.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return doc


def run(processed_dir: Optional[Path] = None, log=print) -> dict:
    from .prep import reference
    pdir = Path(processed_dir) if processed_dir else config.processed_dir()
    cells = scoring.load_cells(pdir)
    prof_path = pdir / "target_profiles.json"
    if not prof_path.exists():
        raise FileNotFoundError(f"{prof_path} not found. Run: python -m analog_finder profiles")
    profiles = json.loads(prof_path.read_text(encoding="utf-8"))["targets"]
    missing = [f for f in ("lst_day_mean_k", "ndvi_mean", "snow_free_months", "slope_h0", "min_calcite") if f not in cells.f]
    if missing:
        raise RuntimeError("grid.bin lacks " + ", ".join(missing) + ". Run: terrain, surface, merge")
    result = validate(cells, profiles, reference.read_analogs(validate_only=True))
    log("Sensitivity to +-25 % weight changes ...")
    result["sensitivity"] = sensitivity(cells, profiles)
    (pdir / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (pdir / "validation.md").write_text(report_markdown(result), encoding="utf-8")
    doc = export_scores(cells, profiles, pdir)
    s = result["summary"]["all"]
    log(f"Validation: {s['scores_only']['scored']} of {s['scores_only']['pairs']} pairs scored, "
        f"median percentile {s['scores_only']['median_percentile']} (random 0.5), top 20 %: {s['scores_only']['share_top20']:.0%} (random 20 %)")
    ind = result["summary"]["independent"]["scores_only"]
    log(f"  without the tasks that use the volcano and impact lists: {ind['scored']} pairs, median {ind['median_percentile']}, "
        f"top 20 %: {ind['share_top20']:.0%}")
    for t, why in result["skipped_tasks"].items():
        log(f"  task {t} cannot be ranked: {why}")
    for t, d in result["sensitivity"]["by_task"].items():
        log(f"  {t}: {d['mean_overlap']:.0%} of the top 5 % stays when weights change by 25 %; dense vegetation in the top: {d['share_dense_vegetation']:.0%}")
    log(f"Wrote validation.json, validation.md, criteria.bin ({len(doc['criteria'])} criteria) and criteria.json to {pdir}")
    return result
