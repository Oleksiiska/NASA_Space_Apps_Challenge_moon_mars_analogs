"""Build webapp/index.html: one self-contained page with the scores of data/processed embedded.

Run from the pipeline folder:  python ../webapp/build_app.py [processed_dir] [out.html]
"""
import base64, csv, gzip, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pipeline"))
from analog_finder import config  # noqa: E402
from analog_finder.prep import reference  # noqa: E402

RAW = ["elev_mean_m", "relief_m", "slope_mean_deg", "slope_lt8", "rough_p50_m", "lst_day_mean_k", "lst_night_min_k", "lst_diurnal_k",
       "ndvi_mean", "snow_free_months", "lowsun_best_h", "ice_frac",
       "volc_dist_km", "volc_basalt_dist_km", "impact_dist_km", "impact_diam_km", "precip_mm_yr",
       "lst_night_mean_k", "lowsun_best_month", "road_dist_km"] + [f"slope_h{k}" for k in range(9)] + [f"snow_m{m:02d}" for m in range(1, 13)]
# features missing from grid.json are skipped


def fmt_temp(d):
    if "mean" in d and "record_low" in d:
        return f"mean {d['mean']} K, record low {d['record_low']} K"
    if "equator_range" in d:
        return f"{d['equator_range'][0]}-{d['equator_range'][1]} K at the equator, polar cold traps {d['polar_cold_traps']} K"
    return f"mean {d['mean']} K, daily range {d['typical_diurnal_range'][0]}-{d['typical_diurnal_range'][1]} K"


def build(pdir: Path, out: Path):
    crit = json.loads((pdir / "criteria.json").read_text(encoding="utf-8"))
    grid = json.loads((pdir / "grid.json").read_text(encoding="utf-8"))
    val = json.loads((pdir / "validation.json").read_text(encoding="utf-8"))
    prof = json.loads((pdir / "target_profiles.json").read_text(encoding="utf-8"))["targets"]
    n = crit["n_cells"]
    cbytes = np.fromfile(pdir / "criteria.bin", dtype=np.uint8)
    gbytes = np.fromfile(pdir / "grid.bin", dtype=np.uint8)
    index = np.fromfile(pdir / "grid_index.bin", dtype="<u4").astype(np.int64)
    blocks = [cbytes]
    raw_meta = []
    off = cbytes.size
    for name in RAW:
        f = next((x for x in grid["features"] if x["name"] == name), None)
        if f is None:
            continue
        blocks.append(gbytes[f["offset"]: f["offset"] + n])
        raw_meta.append({"name": name, "offset": off, "min": f["min"], "max": f["max"], "unit": f.get("unit", "")})
        off += n
    rows = (index // grid["grid"]["n_lon"]).astype("<u2")
    cols = (index % grid["grid"]["n_lon"]).astype("<u2")
    rc_off = off
    blocks += [np.frombuffer(rows.tobytes(), np.uint8), np.frombuffer(cols.tobytes(), np.uint8)]
    blob = gzip.compress(np.concatenate(blocks).tobytes(), 9, mtime=0)  # mtime=0: same input, same bytes

    tg = config.targets()["targets"]
    targets = []
    for t in tg:
        lon = t["lon_e"] if t["lon_e"] <= 180 else t["lon_e"] - 360
        targets.append({"id": t["id"], "world": t["world"], "name": t["name"], "name_uk": t.get("name_uk", t["name"]),
                        "lat": t["lat"], "lon": lon, "mvp": bool(t.get("mvp")), "role": t.get("role", ""),
                        "has_profile": t["id"] in prof})
    analogs = []
    for a in reference.read_analogs():
        analogs.append({k: a[k] for k in ("id", "name", "name_uk", "country", "lat", "lon", "world", "tasks", "kind", "coord_quality")}
                       | {"validate": bool(a["validate"]), "notes": (a.get("notes") or "")[:260]})
    tfacts = {}
    for k, t in prof.items():
        tt = t.get("terrain_1km", {})
        d = {"slope": tt.get("slope_mean_deg"), "relief": tt.get("relief_p5_p95_m"), "rough": tt.get("roughness_rms_p50_m"),
             "flat": tt.get("frac_slope_lt8"), "hist": [round(float(x), 4) for x in tt.get("slope_hist", [])] or None}
        if "thermal_ice" in t:
            ti = t["thermal_ice"]
            d |= {"t_mean": ti.get("temp_avg_mean_K"), "t_min": ti.get("temp_avg_min_K"), "ice1m": ti.get("frac_ice_stable_within_1m")}
        if "sun" in t:
            d["sun_max"] = t["sun"].get("max_elevation_deg_flat_horizon")
        if "water" in t:
            d["h2o"] = t["water"].get("h2o_weight_percent")
        tfacts[k] = d
    lowsun = []
    lp = pdir / "lowsun_by_latitude.csv"
    if lp.exists():
        with open(lp, encoding="utf-8") as f:
            rows_ls = list(csv.DictReader(f))
        if len(rows_ls) == grid["grid"]["n_lat"]:
            lowsun = [[round(float(r[f"m{m:02d}"]), 2) for m in range(1, 13)] for r in rows_ls]
    spots = []
    sp_path = HERE.parent / "data" / "reference" / "spotlights.csv"
    if sp_path.exists():
        with open(sp_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                spots.append({k: r[k] for k in ("id", "name", "name_uk", "country", "world", "why", "why_uk", "source")}
                             | {"lat": float(r["lat"]), "lon": float(r["lon"])})
    cities = []
    cp = HERE.parent / "data" / "reference" / "cities.csv"
    if cp.exists():
        with open(cp, encoding="utf-8") as f:
            cities = [[r["name"], r["name_uk"], r["country"], float(r["lat"]), float(r["lon"]), int(r["pop"])] for r in csv.DictReader(f)]
    gaps = json.loads((HERE.parent / "data" / "reference" / "environment_gaps.json").read_text(encoding="utf-8"))
    quant = []
    for q in gaps["quantities"]:
        vals = {}
        for w in ("earth", "moon", "mars"):
            v = q[w]
            vals[w] = fmt_temp(v) if isinstance(v, dict) else v
        quant.append({"id": q["id"], "name": q["name"], "name_uk": q.get("name_uk", q["name"]), "unit": q.get("unit", ""),
                      "values": vals, "reproducible": q["reproducible_on_earth"], "workaround": q.get("workaround", ""),
                      "note": q.get("note", "")})
    meta = {"n": n, "grid": grid["grid"], "criteria": crit["criteria"], "constraint_bits": crit["constraint_bits"],
            "constraint_offset": crit["constraint_offset"], "constraints_not_checked": crit["constraints_not_checked"],
            "min_coverage": crit["min_coverage"], "no_data_yet": crit["no_data_yet"], "tasks": crit["tasks"],
            "constraints_doc": config.tasks().get("constraints", {}), "raw": raw_meta, "rc_offset": rc_off,
            "targets": [t for t in targets if t["has_profile"]], "analogs": analogs, "gaps": quant,
            "tfacts": tfacts, "lowsun": lowsun, "spotlights": spots, "cities": cities, "road_max_km": crit.get("road_max_km", 50), "sensitivity": val.get("sensitivity", {}).get("by_task", {}), "validation": val["summary"], "validation_skipped": val["skipped_tasks"]}
    html = (HERE / "template.html").read_text(encoding="utf-8")
    html = html.replace("/*META*/null", json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*BLOB*/\"\"", '"' + base64.b64encode(blob).decode() + '"')
    out.write_text(html, encoding="utf-8")
    print(f"{out}: {out.stat().st_size / 1e6:.2f} MB (blob {len(blob) / 1e6:.2f} MB gzip)")


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else config.processed_dir()
    o = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "index.html"
    build(p, o)
