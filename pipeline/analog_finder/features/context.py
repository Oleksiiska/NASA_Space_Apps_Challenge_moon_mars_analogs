"""Geological context of Earth cells: distance to the nearest volcano and to the nearest impact structure.

Inputs (``python -m analog_finder fetch context``, no login):

* Smithsonian Global Volcanism Program, Holocene and Pleistocene volcanoes (point per volcano or volcanic field).
* Impact structures: the Wikipedia list of confirmed structures (compiled from the Earth Impact Database). Only about half
  of its rows carry coordinates; the others take them from the Wikidata item of the same name ("impact crater" with
  coordinates on Earth). Wikidata items that are not in the confirmed list (proposed or disputed structures such as Shiva
  or Wilkes Land) are left out.

The cleaned point lists are written to ``data/reference/volcanoes.csv`` and ``data/reference/impact_structures.csv`` and
kept in the repository, so the layer can be rebuilt without the downloads.

Features on the 0.5 degree grid (great-circle distance in km from the nearest spot of the cell, 0 when inside it):

* ``volcano_dist_km``  to the nearest volcano point. A volcanic field is one point, so large fields read farther away than
  they are.
* ``holocene_volcano_dist_km``  the same for Holocene volcanoes only (fresh lava flows, open lava tubes).
* ``impact_dist_km``   to the rim of the nearest impact structure (centre distance minus radius, never below 0); the radius
  is known only for the Wikipedia rows, Wikidata rows count as points.

Both lists are incomplete (buried and eroded structures, undated volcanic fields) and say nothing about how well exposed a
structure is: they are context for the geology tasks, not a geological map.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np

from .. import config
from ..prep import layers

CELL_DEG = 0.5
EARTH_R_KM = 6371.0
MAX_KM = 1000.0          # distances beyond are stored as 1000 km (uint8 step of about 4 km)
SOURCE_VOLC = "Smithsonian GVP Volcanoes of the World (Holocene and Pleistocene), computed by features/context.py"
SOURCE_IMP = "Wikipedia list of impact structures (Earth Impact Database) and Wikidata, computed by features/context.py"


# --------------------------------------------------------------------------- parsing

def read_gvp(paths: Iterable[Path]) -> list[dict]:
    """Volcano points from GVP GeoJSON files: name, lat, lon, period, type."""
    out = []
    for p in paths:
        period = "holocene" if "holocene" in Path(p).name.lower() else "pleistocene"
        for f in json.loads(Path(p).read_text(encoding="utf-8"))["features"]:
            pr = f.get("properties") or {}
            lon, lat = (f.get("geometry") or {}).get("coordinates", [pr.get("Longitude"), pr.get("Latitude")])[:2]
            if lat is None or lon is None:
                continue
            out.append({"name": pr.get("Volcano_Name", ""), "lat": float(lat), "lon": float(lon), "period": period,
                        "type": pr.get("Primary_Volcano_Type", "")})
    return out


def _dms(parts: list[str]) -> float:
    v = 0.0
    for k, x in enumerate(parts[:3]):
        v += float(x) / 60 ** k
    return v


def parse_coord(template: str) -> Optional[tuple[float, float]]:
    """{{coord|...}} in its decimal, d|N|d|E, d|m|N|d|m|E or d|m|s|N|d|m|s|E forms -> (lat, lon)."""
    inner = template.strip("{} \n").split("|")[1:]
    args = [a.strip() for a in inner if a.strip() and "=" not in a]
    hemis = [i for i, a in enumerate(args) if a.upper() in ("N", "S", "E", "W")]
    try:
        if len(hemis) >= 2:
            i, j = hemis[0], hemis[1]
            lat = _dms(args[:i]) * (-1 if args[i].upper() == "S" else 1)
            lon = _dms(args[i + 1:j]) * (-1 if args[j].upper() == "W" else 1)
        elif len(args) >= 2:
            lat, lon = float(args[0]), float(args[1])
        else:
            return None
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _cell_text(cell: str) -> str:
    cell = re.sub(r"\{\{sort\|[^|}]*\|([^}]*)\}\}", r"\1", cell)          # {{sort|key|shown}} -> shown
    cell = re.sub(r"\{\{0\|[^}]*\}\}", "", cell)                           # {{0|00}} padding
    cell = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", cell)          # [[target|label]] -> label
    return cell.strip()


def parse_wikipedia_impacts(text: str) -> list[dict]:
    """Rows of the confirmed-structure tables: name, lat, lon (None when the row has no coordinates), diameter_km."""
    text = re.split(r"\n==\s*Inferred impact events", text)[0]
    out = []
    for table in re.findall(r"\{\|.*?\n\|\}", text, flags=re.S):
        for row in table.split("\n|-")[1:]:
            cells = [c[1:] for c in row.split("\n") if c.startswith("|") and not c.startswith("|}")]
            m = re.search(r"\{\{[Cc]oord\|[^}]*\}\}", row)
            if len(cells) < 4:
                continue
            ll = parse_coord(m.group(0)) if m else None
            d = re.search(r"\d+(?:\.\d+)?", _cell_text(cells[3]))
            out.append({"name": _cell_text(cells[0]), "lat": ll[0] if ll else None, "lon": ll[1] if ll else None,
                        "diameter_km": float(d.group(0)) if d else None, "source": "wikipedia"})
    return out


def parse_wikidata_impacts(doc: dict) -> list[dict]:
    out = []
    for b in doc["results"]["bindings"]:
        out.append({"name": b.get("itemLabel", {}).get("value", ""), "lat": float(b["lat"]["value"]),
                    "lon": float(b["lon"]["value"]), "diameter_km": None, "source": "wikidata"})
    return out


def haversine_km(lat1, lon1, lat2, lon2):
    r = np.pi / 180.0
    a = np.sin((lat2 - lat1) * r / 2) ** 2 + np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lon2 - lon1) * r / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def norm_name(name: str) -> str:
    """'Gweni-Fada crater' and 'Gweni-Fada' -> 'gwenifada'; drops words such as crater, impact, structure."""
    n = re.sub(r"\(.*?\)", "", name.lower())
    n = re.sub(r"\b(crater|craters|impact|structure|meteor|meteorite|basin|ring|astrobleme|dome)\b", "", n)
    return re.sub(r"[^a-z0-9]", "", n.replace("ö", "o").replace("ä", "a").replace("ü", "u").replace("é", "e"))


def merge_impacts(confirmed: list[dict], extra: list[dict]) -> list[dict]:
    """Confirmed rows with coordinates; rows without them take the coordinates of the extra item of the same name."""
    by_name: dict[str, dict] = {}
    for e in extra:
        by_name.setdefault(norm_name(e["name"]), e)
    out = []
    for r in confirmed:
        if r["lat"] is not None:
            out.append(r)
            continue
        e = by_name.get(norm_name(r["name"]))
        if e is not None:
            out.append({**r, "lat": e["lat"], "lon": e["lon"], "source": "wikipedia+wikidata coordinates"})
    return out


# --------------------------------------------------------------------------- reference lists

def volcanoes_csv() -> Path:
    return config.reference_dir() / "volcanoes.csv"


def impacts_csv() -> Path:
    return config.reference_dir() / "impact_structures.csv"


def _write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else (f"{r[k]:.4f}" if k in ("lat", "lon") else r[k])) for k in cols})


def _read_csv(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["lat"], r["lon"] = float(r["lat"]), float(r["lon"])
        if "diameter_km" in r:
            r["diameter_km"] = float(r["diameter_km"]) if r["diameter_km"] else None
    return rows


def update_reference(raw_dir: Optional[Path] = None, log: Callable[[str], None] = print) -> tuple[list[dict], list[dict]]:
    """Parse the downloads into the two reference CSVs; fall back to the CSVs already in the repository."""
    raw = Path(raw_dir) if raw_dir else config.resolve(config.dataset("earth_gvp_volcanoes")["dest"])
    gvp = sorted(raw.glob("gvp_*.geojson"))
    if gvp:
        volc = read_gvp(gvp)
        _write_csv(volcanoes_csv(), volc, ["name", "lat", "lon", "period", "type"])
        log(f"  {len(volc)} volcanoes from {', '.join(p.name for p in gvp)} -> {volcanoes_csv().name}")
    elif volcanoes_csv().exists():
        volc = _read_csv(volcanoes_csv())
        log(f"  {len(volc)} volcanoes from {volcanoes_csv().name} (no download found)")
    else:
        raise FileNotFoundError("No volcano list. Run: python -m analog_finder fetch context")
    wp, wd = raw / "impacts_wikipedia.wiki", raw / "impacts_wikidata.json"
    if wp.exists():
        a = parse_wikipedia_impacts(wp.read_text(encoding="utf-8"))
        b = parse_wikidata_impacts(json.loads(wd.read_text(encoding="utf-8"))) if wd.exists() else []
        imp = merge_impacts(a, b)
        _write_csv(impacts_csv(), imp, ["name", "lat", "lon", "diameter_km", "source"])
        n_wp = sum(r["lat"] is not None for r in a)
        log(f"  {len(imp)} of {len(a)} confirmed impact structures located ({n_wp} with coordinates in Wikipedia, "
            f"{len(imp) - n_wp} from Wikidata by name) -> {impacts_csv().name}")
        missing = [r["name"] for r in a if r["lat"] is None and norm_name(r["name"]) not in {norm_name(e["name"]) for e in b}]
        if missing:
            log(f"  without coordinates, left out: {', '.join(missing)}")
    elif impacts_csv().exists():
        imp = _read_csv(impacts_csv())
        log(f"  {len(imp)} impact structures from {impacts_csv().name} (no download found)")
    else:
        raise FileNotFoundError("No impact list. Run: python -m analog_finder fetch context")
    return volc, imp


# --------------------------------------------------------------------------- distance layers

def nearest_km(lat: np.ndarray, lon: np.ndarray, plat: np.ndarray, plon: np.ndarray,
               radius_km: Optional[np.ndarray] = None, half_deg: float = 0.0, chunk: int = 2048) -> np.ndarray:
    """Distance from each cell (centre lat, lon, half size ``half_deg``) to the nearest point, minus the point's radius.

    The distance is measured to the nearest spot of the cell, so a point inside the cell is at 0 km; never below 0.
    """
    out = np.empty(lat.size, dtype=np.float32)
    rad = np.zeros(plat.size) if radius_km is None else np.nan_to_num(radius_km)
    for s in range(0, lat.size, chunk):
        la, lo = lat[s:s + chunk, None], lon[s:s + chunk, None]
        dlon = (plon[None, :] - lo + 180.0) % 360.0 - 180.0
        qla = la + np.clip(plat[None, :] - la, -half_deg, half_deg)        # nearest spot of the cell to each point
        qlo = lo + np.clip(dlon, -half_deg, half_deg)
        d = haversine_km(qla, qlo, plat[None, :], plon[None, :]) - rad[None, :]
        out[s:s + chunk] = np.maximum(d.min(axis=1), 0.0)
    return out


def distance_grids(volc: list[dict], imp: list[dict], cell_deg: float = CELL_DEG) -> dict[str, np.ndarray]:
    n_lat, n_lon = int(round(180 / cell_deg)), int(round(360 / cell_deg))
    lat = 90.0 - (np.arange(n_lat) + 0.5) * cell_deg
    lon = -180.0 + (np.arange(n_lon) + 0.5) * cell_deg
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    la, lo = la.ravel(), lo.ravel()
    h = cell_deg / 2.0
    v = nearest_km(la, lo, np.array([p["lat"] for p in volc]), np.array([p["lon"] for p in volc]), half_deg=h)
    holo = [p for p in volc if p.get("period") == "holocene"]
    vh = nearest_km(la, lo, np.array([p["lat"] for p in holo]), np.array([p["lon"] for p in holo]), half_deg=h)
    radius = np.array([(p["diameter_km"] or 0.0) / 2.0 for p in imp])
    i = nearest_km(la, lo, np.array([p["lat"] for p in imp]), np.array([p["lon"] for p in imp]), radius, half_deg=h)
    return {"volcano_dist_km": np.minimum(v, MAX_KM).reshape(n_lat, n_lon),
            "holocene_volcano_dist_km": np.minimum(vh, MAX_KM).reshape(n_lat, n_lon),
            "impact_dist_km": np.minimum(i, MAX_KM).reshape(n_lat, n_lon)}


def _at(grid: np.ndarray, lat: float, lon: float) -> float:
    cd = 180.0 / grid.shape[0]
    r = int((90.0 - lat) / cd)
    c = int((lon + 180.0) / cd)
    return float(grid[r, c])


def build_layer(log: Callable[[str], None] = print) -> Path:
    cell = config.cell_deg()
    volc, imp = update_reference(log=log)
    g = distance_grids(volc, imp, cell)
    problems = []
    for what, lat, lon, ok, label in (
        ("volcano_dist_km", 35.58, -111.63, lambda d: d < 20, "S P Crater, San Francisco Volcanic Field"),
        ("volcano_dist_km", 19.42, -155.29, lambda d: d < 5, "Kilauea"),
        ("volcano_dist_km", 48.85, 2.35, lambda d: d > 150, "Paris"),
        ("impact_dist_km", 48.88, 10.57, lambda d: d < 5, "Ries"),
        ("impact_dist_km", 35.03, -111.02, lambda d: d < 5, "Meteor Crater"),
        ("impact_dist_km", 46.6, -81.18, lambda d: d < 5, "Sudbury"),
    ):
        v = _at(g[what], lat, lon)
        if not ok(v):
            problems.append(f"{what} at {label} ({lat}, {lon}) is {v:.0f} km, which is not plausible")
    if problems:
        raise RuntimeError("Context layer self-check failed:\n  " + "\n  ".join(problems))
    log("Context self-check: ok (S P Crater and Kilauea near volcanoes, Paris far; Ries, Meteor Crater, Sudbury on impacts)")
    items = [
        layers.LayerFeature("volcano_dist_km", g["volcano_dist_km"], 0.0, MAX_KM, "km",
                            "Distance from the cell to the nearest Holocene or Pleistocene volcano (one point per "
                            "volcano or volcanic field).", SOURCE_VOLC),
        layers.LayerFeature("holocene_volcano_dist_km", g["holocene_volcano_dist_km"], 0.0, MAX_KM, "km",
                            "Distance from the cell to the nearest Holocene volcano (active in the last 11,700 years: "
                            "young, little eroded lava).", SOURCE_VOLC),
        layers.LayerFeature("impact_dist_km", g["impact_dist_km"], 0.0, MAX_KM, "km",
                            "Distance from the cell to the rim of the nearest known impact structure.", SOURCE_IMP),
    ]
    return layers.save_layer("earth_context", items, cell)
