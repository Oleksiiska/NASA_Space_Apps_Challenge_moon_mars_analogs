"""Generate docs/data_sources.md from pipeline/config/sources.yaml plus fixed text.

Run from the repository root:  python pipeline/scripts/make_sources_doc.py
"""
import sys
from pathlib import Path

import yaml

root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2])
src = yaml.safe_load(open(f"{root}/pipeline/config/sources.yaml", encoding="utf-8"))

HEAD = """# Data sources, attribution and licences

Every dataset of the project, the official challenge resource it comes from, and the
text to cite. The machine-readable version is `pipeline/config/sources.yaml`; file names
and sizes of the NASA PDS files were read from the PDS directory listings on {checked}.

NASA does not endorse any non-U.S. Government entity and is not responsible for
information on non-U.S. Government websites. For ESA, CSA, JAXA and other non-U.S.
Government sources the data-use terms of that source apply.

## How the official challenge resources are used

| Official resource | What the project takes from it | Role |
| --- | --- | --- |
| NASA Earthdata Search | SRTMGL30 (terrain), MOD11C3 (surface temperature), MOD13C2 (NDVI), MOD10CM (snow), EMIT L3ASA (minerals); MCD12C1 (land cover) is downloaded but not used | Core: features of every Earth cell |
| NASA Worldview | GIBS imagery layers: true colour, temperature, snow | Map background and visual check of the top candidates; nothing is downloaded into the pipeline |
| NASA Planetary Data System (PDS) | Mars: MOLA MEGDR topography, Odyssey GRS water map | Core: fingerprints of the Martian targets |
| NASA Lunar Reconnaissance Orbiter (PDS Geosciences) | LOLA gridded data: south polar elevation, slope and roughness maps | Core: terrain of the lunar targets |
| NASA LRO Diviner Lunar Data | Polar Resource Product: temperatures and depth of stable ice | Core: the "cold" and "ice" criteria |
| ESA Copernicus Data Space Ecosystem | Copernicus DEM GLO-90 for high latitudes; Sentinel-1 and Sentinel-2 for the top candidates | Core for polar analogs, detail otherwise |
| CSA RADARSAT-1, RCM, SAR Python Tutorial | Radar images of Arctic analogs; the tutorial as a code template | Detail and optional; not part of the downloads yet |
| ESA Open Science Catalog | Search for ESA products on permafrost, snow, surface temperature | Optional |
| JAXA G-Portal | GCOM-C/SGLI, GCOM-W/AMSR2, GSMaP precipitation | Optional: independent check of temperature, snow and aridity |

## Datasets in the manifest

Access: `open` needs no account; `earthdata_login` needs the free NASA Earthdata Login.
"""

TAIL = """
## Reference tables written for the project

| File | Where the content comes from |
| --- | --- |
| `data/reference/known_analogs.csv` | Site list and coordinates: the Wikipedia articles "Terrestrial analogue site" and "List of impact structures on Earth" and the articles of single sites (text under CC BY-SA 4.0), Cavalazzi et al. 2019 (Astrobiology 19:553) for Dallol. Uses: USGS, NASA NTRS, Europlanet, CORDIS and National Park Service pages. Each row names its own sources in `coord_source` and `use_source`. |
| `pipeline/config/targets.yaml`, `data/reference/targets.geojson` | Coordinates from the USGS Gazetteer of Planetary Nomenclature, the LROC site, the PDS Orbital Data Explorer landing-site table and Wikipedia; the source of each target is in its `source` field. |
| `data/reference/environment_gaps.json` | NASA Planetary Fact Sheets (NSSDCA); Hassler et al. 2014 (Science 343, 1244797) for Mars radiation; Zhang et al. 2020 (Science Advances 6, eaaz1334) for lunar radiation; UNSCEAR 2008 for the Earth background. |
| `data/processed/grid.*`, `lowsun_by_latitude.csv` | Land and ice masks from Natural Earth; the low-Sun hours are computed from solar geometry in `features/sun.py` and were checked against the pvlib library. |

### Columns of known_analogs.csv

| Column | Meaning |
| --- | --- |
| `id`, `name`, `name_uk`, `country` | Identifier and names |
| `lat`, `lon` | Degrees, north and east positive |
| `world` | Which world the site stands in for: `moon`, `mars` or `both` |
| `tasks` | Test tasks the site is relevant to, ids from `config/tasks.yaml`, separated by `;` |
| `kind` | Type of site, separated by `;` (volcanic, impact, polar_desert, evaporite, habitat and so on) |
| `validate` | `yes` when the site is a natural landscape that the ranking should be able to find again; `no` for habitats, underwater sites and field schools |
| `used_by` | Who uses the site and for what |
| `coord_quality` | `verified`: the coordinates were read from `coord_source`; `approx`: written from memory, to be refined |
| `coord_source`, `use_source` | Pages the coordinates and the use were taken from |
| `use_checked` | `no` when the page in `use_source` was found but not read yet; `used_by` then ends with "(to confirm)" |
| `notes` | Scale of the site, caveats |

## Known limits of the data

- The Natural Earth ice mask (1:50 million) is too coarse for small ice-free areas: the cell of the McMurdo Dry Valleys comes out as fully ice-covered. Use the MODIS snow and land-cover products for such places.
- SRTMGL30 covers 90 N to 60 S. North of 60 N, where real SRTM ends, the values come from a coarser source (GTOPO30, to be confirmed), so Arctic terrain is smoother than elsewhere. Antarctica (south of 60 S) has no terrain: use Copernicus DEM for single sites such as the McMurdo Dry Valleys.
- EMIT L3ASA: the file covers 55 N to 54.5 S and only bare, dust-source surfaces; elsewhere the mineral features are empty. Its cell centres sit a quarter cell away from the project grid and are averaged 2 x 2.
- The volcano list is an earlier version of the Global Volcanism Program database (1,571 volcanoes, 1,420 on land). A volcanic field is one point, so distance to it is only a proxy for volcanic terrain nearby.
- The impact table lists 189 confirmed structures; the distance is measured to a circular rim of the listed diameter.
- NASA POWER precipitation comes from the MERRA-2 reanalysis on a 0.5 x 0.625 degree grid and is least reliable in mountains and over small deserts.
- The GRS water map has 5 degree bins, about 300 km on Mars: it describes a region, not a landing site.
- The LOLA files of the manifest cover 75 S to the pole, which is enough for the lunar targets of `targets.yaml` and nothing else.
- Sun elevations assume a flat horizon. Real horizons at the lunar pole and in mountains change the lighting a lot.

## Short form for the submission

Data: NASA PDS (LRO LOLA, LRO Diviner, MGS MOLA, Mars Odyssey GRS); NASA EOSDIS LP DAAC
and NSIDC DAAC through Earthdata (SRTMGL30, MOD11C3, MOD13C2, MOD10CM, EMIT L3ASA); NASA
POWER (precipitation, if the dryness layer was built); Smithsonian Global Volcanism
Program; Earth Impact Database (PASSC, University of New Brunswick); Natural Earth.
"""

def size(ds):
    files = ds.get("files") or []
    total = sum(f.get("bytes") or 0 for f in files)
    if not files:
        return "chosen at download time"
    return f"{len(files)} file(s), {total / 1e6:,.1f} MB"

out = [HEAD.format(checked=src["checked"])]
for world, title in (("moon", "Moon"), ("mars", "Mars"), ("earth", "Earth")):
    out.append(f"\n### {title}\n")
    for ds in src["datasets"]:
        if ds["world"] != world:
            continue
        where = ds.get("base_url") or f"Earthdata short name `{ds.get('short_name')}`, version {ds.get('version')}"
        out.append(f"**{ds['title']}** (`{ds['id']}`)\n")
        out.append(f"- Official resource: {ds['official_resource']}. Agency: {ds['agency']}. Access: `{ds['access']}`.")
        out.append(f"- Source: {where}")
        out.append(f"- Size: {size(ds)}. Saved to `{ds['dest']}`. Used for: {', '.join(ds.get('used_for', []))}.")
        out.append(f"- Citation: {' '.join(str(ds['citation']).split())}")
        out.append(f"- Licence: {ds['license']}.\n")
out.append(TAIL)
open(f"{root}/docs/data_sources.md", "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("written", sum(len(x) for x in out), "chars")
