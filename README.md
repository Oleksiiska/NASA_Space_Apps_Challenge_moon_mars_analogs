# Moon and Mars analog finder: data layer

NASA Space Apps Challenge 2026, challenge "Identify Earth Locations that Analog the
Permanent Moon Base Locations and Mars".

This repository holds the data layer of the project: a manifest of every dataset and
the official challenge resource it comes from, download scripts, readers for the
planetary file formats, the Earth grid, and the first computed layers. The ranking and
the web app are built on top of it.

The idea in one paragraph: the Earth's land is cut into 0.5 degree cells. Every cell and
every Moon or Mars target gets the same set of features (terrain at a 1 km step, cold,
ice, bare ground, low Sun and so on). A cell is a good analog *for a given test task*
when its features are close to the target's. Sites that agencies already use as analogs
are kept apart and serve only to check the ranking. What the Earth cannot reproduce
(gravity, pressure, radiation) is shown next to every candidate and never mixed into
the score.

## Layout

```
pipeline/
  config/sources.yaml    every dataset: official resource, URL, files, sizes, citation, licence
  config/targets.yaml    12 Moon and Mars targets with coordinates and sources
  config/tasks.yaml      7 test tasks and the weight of each criterion
  analog_finder/
    fetch/               downloads: NASA PDS, Earthdata, NASA POWER, Copernicus DEM
    io/                  readers: PDS3 images with their labels, Diviner and GRS tables
    prep/                Earth land grid; map layers of targets and known analogs
    features/            terrain (slope, relief, roughness) and Sun geometry
    targets/             feature "fingerprints" of the Moon and Mars targets
    export/              compact binary grid for the browser
  tests/                 68 tests; they need no downloads
data/
  raw/                   downloads (not committed, see .gitignore)
  interim/               scratch space
  processed/             outputs that the web app reads
  reference/             hand-kept tables: known analogs, targets, what Earth cannot reproduce
docs/data_sources.md     attribution and licences
```

## Already computed

These files need no downloads and are ready to use.

| File | Content |
| --- | --- |
| `data/processed/grid.json`, `grid.bin`, `grid_index.bin` | 0.5 degree grid, 88,883 land cells, 5 features: `land_frac`, `ice_frac`, `lowsun_best_h`, `lowsun_mean_h`, `lowsun_best_month` |
| `data/processed/lowsun_by_latitude.csv` | Hours per day with the Sun 0 to 5 degrees above the horizon, by latitude and month |
| `data/processed/analogs_grid.csv` | Grid cell and grid features at each known analog site |
| `data/reference/known_analogs.csv`, `.geojson` | 39 sites already used as Moon or Mars analogs; 28 with coordinates read from a source, 11 approximate |
| `data/reference/targets.geojson` | The 12 targets as map points |
| `data/reference/environment_gaps.json` | Gravity, pressure, day length, radiation, temperature on Earth, the Moon and Mars |

The format of the binary grid is described at the top of
`pipeline/analog_finder/export/to_binary.py` and repeated inside `grid.json`:
`value = min + q / 254 * (max - min)`, `q = 255` means no data.

## Quick start on Windows

Python 3.10 or newer, 64-bit (3.11 to 3.13 have ready-made packages for everything below).
In PowerShell, from the project folder:

```powershell
python -m venv .venv          # or: py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e "pipeline[geo,dev]"
python -m pytest pipeline
python -m analog_finder sources
```

If PowerShell refuses to run `Activate.ps1`, use the classic prompt (`cmd`) and
`.venv\Scripts\activate.bat` instead.

### 1. Moon and Mars files from NASA PDS (no login)

```powershell
python -m analog_finder fetch pds
python -m analog_finder check
python -m analog_finder profiles
```

`fetch pds` downloads 13 data files and their labels, 1.6 GB in total, into
`data/raw/moon` and `data/raw/mars`. It can be interrupted and started again: finished
files are skipped and a partial file continues from where it stopped. `check` compares
every file size with the manifest. `profiles` writes
`data/processed/target_profiles.json`: terrain at a 1 km step for every target,
temperatures and ice stability from Diviner for the lunar targets, water content from
GRS for the Martian ones.

`profiles` first tests the georeferencing against four known landmarks (the floor of
Shackleton and the top of Mons Mouton on the Moon, Olympus Mons and Hellas on Mars). If
it reports a problem, do not use the numbers: the image is being read mirrored or
shifted.

To try the chain on a small download first (33 MB, Mars only), pick two datasets by id.
Mars terrain then comes from the coarser 3.7 km map until the 926 m tiles arrive:

```powershell
python -m analog_finder fetch pds --only mars_mola_megdr_16 mars_grs_h2o
python -m analog_finder profiles
```

### 2. Earth products from NASA Earthdata (free Earthdata Login)

```powershell
pip install -e "pipeline[earth]"
python -m analog_finder fetch earth --dry-run
python -m analog_finder fetch earth --year 2023
```

The dry run lists the granules and their size without logging in. The real run asks for
your Earthdata Login in the terminal; the `earthaccess` library stores it in your user
profile, not in this repository. Products: SRTMGL30 (terrain), MOD11C3 (surface
temperature), MOD13C2 (NDVI), MOD10CM (snow), MCD12C1 (land cover), EMIT L3ASA (minerals).

### 2b. Earth feature layers (after step 2)

```powershell
pip install -e "pipeline[formats]"
python -m analog_finder terrain
python -m analog_finder surface
python -m analog_finder merge
```

`terrain` reads SRTMGL30 (27 tiles) and computes slope, relief and roughness for every
0.5 degree cell. `surface` reads the monthly MODIS files and the EMIT netCDF file and
writes surface temperature, NDVI, snow and mineral layers; each product has a
self-check against known places (Sahara hot, Greenland snowy, Amazon green, ...) and
stops with a message if a file is read wrongly. `merge` adds all layers to
`data/processed/grid.bin`. `python -m analog_finder inspect FILE` shows the variables
inside any HDF4 or NetCDF file.

Mineral abundances (EMIT) exist only for bare surfaces between 55 N and 54.5 S; cells
elsewhere stay empty, and the ranking must treat an empty feature as unknown, not as zero.

### 2b'. Volcanic and impact context (no login)

```powershell
python -m analog_finder fetch context
python -m analog_finder context
python -m analog_finder merge
```

`fetch context` downloads the Smithsonian GVP volcano lists and the Wikipedia/Wikidata lists of
confirmed impact structures (4 MB). `context` writes `data/reference/volcanoes.csv` and
`impact_structures.csv` (kept in the repository, so it also runs without the downloads) and the
distance from every cell to the nearest volcano and impact rim. The `volcanic` and `impact`
criteria give full score within 25 km and none beyond 150 km. They say nothing about how well a
structure is exposed.

### 2b''. Precipitation for the dryness criterion (Earthdata Login)

```powershell
python -m analog_finder fetch earth --only earth_imerg_monthly --year 2023
python -m analog_finder surface --only precip
python -m analog_finder merge
```

12 monthly GPM IMERG files (214 MB) from GES DISC. The first download may stop with "EULA acceptance failure": approve
"NASA GESDISC DATA ARCHIVE" under Applications > Authorized Apps in your Earthdata profile and run it again.

### 2c. Ranking and validation

```powershell
python -m analog_finder score
```

`score` computes, for every task in `pipeline/config/tasks.yaml` and every main target, how
close each Earth cell is (terrain is matched to the target's fingerprint; cold, thermal
range, low Sun, ground ice, bare ground, snow-free months and minerals are ranked in the
useful direction, because Earth cannot reach lunar or Martian values). It then looks up the
known analog sites and writes `data/processed/validation.md` (percentile of every site; a
random site would get a median of 0.5) and `criteria.bin` / `criteria.json`, the per-cell
scores for the web app. The known analogs are never used to set weights.

Tasks that need data not in the grid yet (volcanic fields and caves, impact structures,
dryness) are scored from the criteria that exist; `caves` cannot be ranked until a volcano
layer is added. Check `validation.md` before quoting any number.

### 2d. Did a change make the ranking better?

```powershell
python -m analog_finder evaluate --save-baseline   # once, before the change
# ... change scoring.py, tasks.yaml, add a layer ...
python -m analog_finder evaluate                   # compare with the baseline
```

`evaluate` prints a few numbers with 95 % bootstrap intervals over sites: the percentile of
the known analogs as the web app shows them (filtered out = 0), the AUC of known analogs
against clearly non-analog places (`data/reference/negative_sites.csv`), and red flags such
as glaciers in the top 1 % of a landing task. Against the baseline it gives a paired change
per metric and a verdict: `better`, `worse` or `no clear change`. With about 18 sites, a
change the paired interval does not separate from zero is noise. Results go to
`data/processed/eval_current.json`; the baseline is `data/processed/eval_baseline.json`.
After a change is accepted, save it as the new baseline. The more you tune while looking at
these numbers, the less they say about unseen sites.

`python -m analog_finder evaluate --holdout` scores `data/reference/holdout_analogs.csv`: 9 sites
collected after the tuning, with tasks fixed from their sources before any score was seen. Run it
only to check a finished method; tuning on them would turn them into one more training set.

### 2e. Web app

```powershell
python ../webapp/build_app.py                      # from the pipeline folder, after `score`
python -m http.server 8765 --directory ../webapp   # then open http://localhost:8765/index.html
```

### 3. Point data for the known analog sites

```powershell
python -m analog_finder fetch power
python -m analog_finder fetch copdem --dry-run
```

`fetch power` asks the NASA POWER service for the climate at each site of
`data/reference/known_analogs.csv` (no login). `fetch copdem` downloads Copernicus DEM
tiles around the same sites; it matters for high latitudes, which SRTM does not cover.
Both accept `--points other.csv` with the columns `id`, `lat`, `lon`.

### 4. Rebuild the computed layers

```powershell
python -m analog_finder grid
python -m analog_finder reference
```

`grid` rebuilds the land grid and the low-Sun features (about 3 minutes). `reference`
rewrites the two GeoJSON layers and `analogs_grid.csv` after you edit
`known_analogs.csv` or `targets.yaml`.

## Conventions

- Earth longitudes run from -180 to 180. Moon and Mars longitudes in `targets.yaml` are east-positive, 0 to 360.
- Grid row 0 is the northernmost row, column 0 starts at 180 W. A cell is kept when at least 20% of it is land.
- Terrain of all three worlds is compared at the same step of about 1 km: SRTMGL30 for the Earth (926 m), MOLA MEGDR 64 pixels per degree for Mars (926 m), LOLA 240 m averaged 4 by 4 for the Moon (960 m).
- "Low Sun" means the Sun between 0 and 5 degrees above a flat horizon. At the lunar south pole it never climbs higher than about 2 degrees.
- Known analogs validate the ranking; they are never used to tune it.

## What is not done yet

- Dryness is precipitation only (GPM IMERG 2023), not an aridity index; a 55 km cell around a salt basin (Dallol,
  Tirez) also holds the wetter hills around it.
- Volcanic and impact criteria are distances to point lists; tropical volcanoes under forest rank high in the caves
  and EVA tasks (28-38 % dense vegetation in their top 5 %).
- The code was tested on synthetic files that follow the real labels, because the build machine could not reach the NASA servers. The first run on real files is the real test: read what `check` and `profiles` print.

## Use of AI

Space Apps asks every team to say where and how AI was used. For this repository: the
data layer (download scripts, readers, feature code, tests, configuration and reference
tables) was written with Claude (Anthropic) from the team's plan, and the coordinates
and facts in the reference tables were collected by it from the sources listed in each
row. Rows marked `approx` or `to confirm` were not checked against a source. Copy this
note into the submission and extend it with whatever else the team uses AI for.

## Data and licences

Code: MIT (see `LICENSE`). Data keep the terms of their providers; citations for every
dataset are in `docs/data_sources.md`. NASA does not endorse any non-U.S. Government
entity; for ESA, CSA, JAXA and other non-U.S. Government sources the data-use terms of
that source apply.
