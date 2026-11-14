"""Write data/reference/cities.csv (city search of the web page) from Natural Earth populated places.

Run from the repository root after `python -m analog_finder fetch aux`:
    python pipeline/scripts/make_cities.py
"""
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
src = root / "data" / "raw" / "earth" / "naturalearth" / "ne_10m_populated_places.geojson"
out = root / "data" / "reference" / "cities.csv"
data = json.loads(src.read_text(encoding="utf-8"))
rows = []
for ft in data["features"]:
    p = ft["properties"]
    name = (p.get("NAME_EN") or p.get("NAME") or "").strip()
    if not name:
        continue
    rows.append({"name": name, "name_uk": (p.get("NAME_UK") or "").strip(), "country": (p.get("ADM0NAME") or "").strip(),
                 "lat": round(float(p["LATITUDE"]), 3), "lon": round(float(p["LONGITUDE"]), 3), "pop": int(p.get("POP_MAX") or 0)})
rows.sort(key=lambda r: -r["pop"])
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "name_uk", "country", "lat", "lon", "pop"])
    w.writeheader()
    w.writerows(rows)
print(f"{out}: {len(rows)} places")
