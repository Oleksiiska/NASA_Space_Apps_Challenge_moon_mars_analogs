# Moon–Mars Analog Finder

NASA Space Apps Challenge 2026, challenge "Identify Earth Locations that Analog the
Permanent Moon Base Locations and Mars".

Where on Earth can a team test what it will do at the Shackleton–de Gerlache ridge, at Mons
Mouton, in Jezero crater or on Arcadia Planitia? The Earth's land is cut into 0.5 degree cells.
Every cell and every Moon or Mars target gets the same measures (terrain at a 1 km step, cold,
ice, bare ground, low Sun, minerals, volcanoes, impact structures). A cell is a good analog
*for a given test task* when its measures are close to the target's. Sites that agencies
already use as analogs only check the ranking. What the Earth cannot reproduce (gravity,
pressure, radiation, cryogenic cold) is shown next to every candidate and never mixed into
the score.

This is a screening tool, not an engineering assessment or a site-selection recommendation.

- Web page: `webapp/index.html` (one self-contained file; open it in a browser)
- Method, formulas and validation: [`docs/methodology.md`](docs/methodology.md)
- Current validation figures: [`data/processed/validation.md`](data/processed/validation.md)
- Data sources, citations and licences: [`docs/data_sources.md`](docs/data_sources.md)

## Result in short

- 88,883 land cells, 12 targets (5 Moon, 7 Mars), 7 test tasks, 46 per-cell criteria.
- Known analog sites rank well above a random place: median percentile 0.77 over all tasks
  (random: 0.50). Without the two tasks that use the volcano and impact lists, which contain
  many of the sites themselves, the median is 0.70 and only 21 % of the sites reach the top
  20 %: the 55 km cell is much larger than a real site. See `docs/methodology.md`, section 6.
- Changing every weight by up to ±25 % keeps 75–99 % of the top 5 % cells in place.

## What the page does

- Map of all land cells coloured by the score of the chosen task and target; 10 best regions (at least 600 km apart); sliders for every weight and switches for the hard filters.
- **Low-Sun window** map mode: for any month, hours per day with the Sun 0–5 degrees up, with cells under snow that month hatched.
- Card of any cell: score, rank, data coverage, contribution of each criterion, stability under ±25 % weight changes, the cell's values with their source, its slope classes next to the target's, a 12-month low-Sun calendar, nearby known analogs, and "new" when none is within 1,000 km. A cell without a score says why (which filter, or how little data).
- "Where the known analogs land": the percentile of every known site for the current settings.
- "What Earth cannot reproduce" next to every candidate, never inside the score.
- **Check a place**: type any of 7,342 cities to see how its cell scores for every task, why it fails, and the nearest strong candidate; a short glossary explains the terms.
- **Getting there**: distance to the nearest major road (also a hard filter for rover mobility) and the CO₂ of one passenger's flight from a chosen city (UK DESNZ 2025 factors).
- Spotlight: the Volyn anorthosite massif of the Korosten pluton (Ukraine), a match to the lunar highlands in rock type but not in landscape.
- Export of the 10 regions and the 100 best cells as CSV or GeoJSON (on the published site), English and Ukrainian, light and dark themes, phone layout.

## Layout

```
pipeline/
  config/sources.yaml    every dataset: official resource, URL, files, sizes, citation, licence
  config/targets.yaml    12 Moon and Mars targets with coordinates and sources
  config/tasks.yaml      7 test tasks: weights of the criteria and hard filters
  analog_finder/
    fetch/               downloads: NASA PDS, Earthdata, NASA POWER, Copernicus DEM, context tables
    io/                  readers: PDS3 images and tables, SRTM tiles, HDF4 / NetCDF inspection
    prep/                Earth land grid, feature layers, reference layers
    features/            terrain, Sun geometry, MODIS and EMIT surface layers, volcano / impact / dryness layers
    targets/             feature "fingerprints" of the Moon and Mars targets
    scoring.py           criteria and task scores
    validate.py          known-analog validation, weight sensitivity, export for the web page
    ml/pu.py             experimental machine-learning layer (branch ml-layer)
    pipeline_all.py      the `all` command
    export/              compact binary grid
  scripts/               generator of docs/data_sources.md
  tests/                 84 tests; they need no downloads (the ML tests run only with scikit-learn)
webapp/
  template.html          the page; build_app.py embeds data/processed into index.html
data/
  raw/                   downloads (not committed, except the land mask and the two context tables)
  interim/               intermediate layers (not committed)
  processed/             grid, target profiles, criteria and validation: everything the page reads
  reference/             known analogs, targets, spotlight places, what Earth cannot reproduce
docs/                    methodology.md, data_sources.md
.github/workflows/ci.yml tests and a full `all` run on every push
```

## Quick start (Windows)

Python 3.11 to 3.13, 64-bit. In PowerShell, from the repository folder:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e "pipeline[geo,earth,formats,dev]"
python -m pytest pipeline
python -m analog_finder all
```

`all` runs every step that is not done yet. A fresh clone already has the processed grid, so
nothing is downloaded: it builds the volcano and impact layers from the tables in the
repository, scores every task, writes the validation and rebuilds `webapp/index.html`
(a few seconds). If PowerShell refuses to run `Activate.ps1`, use `cmd` and
`.venv\Scripts\activate.bat`.

## Experimental ML layer (branch `ml-layer`)

```powershell
pip install -e "pipeline[ml]"
python -m analog_finder ml
python -m analog_finder merge
python -m analog_finder web
```

`ml` trains a bagged positive-unlabeled classifier on the known analog sites (39 Earth measures; location and the
volcano, impact and road lists are left out because those lists contain the sites themselves) and checks it on
every site hidden together with everything within 300 km. It takes 5–10 minutes. The page then gets a third map
mode, "ML (experimental)". Results are in `data/processed/ml_report.md`: on the same yardstick (percentile among
all land cells) the formula finds the known lunar analog sites better than the model (median 0.91 against 0.90,
top 20 % in 82 % against 59 %), and the model finds the known Martian ones better (0.85 against 0.65, 58 % against
20 %). The model learns the pattern of past choices, so it is shown apart and never mixed into the score.

## Rebuilding from the raw data

Needed only to recompute the grid from the original files. `python -m analog_finder all --fetch`
does all of it in order; the steps one by one:

### 1. Moon and Mars files from NASA PDS (no login, 1.6 GB)

```powershell
python -m analog_finder fetch pds
python -m analog_finder check
python -m analog_finder profiles
```

`check` compares every file size with the manifest. `profiles` writes
`data/processed/target_profiles.json` after testing the georeferencing against four landmarks
(the floor of Shackleton and the top of Mons Mouton, Olympus Mons and Hellas).

### 2. Earth products from NASA Earthdata (free Earthdata Login, about 3.5 GB)

```powershell
python -m analog_finder fetch earth --dry-run
python -m analog_finder fetch earth --year 2023
```

The real run asks for your Earthdata Login in the terminal; `earthaccess` stores it in your
user profile, not in this repository. MCD12C1 (land cover, 1.2 GB) is downloaded but not used.

### 3. Earth feature layers

```powershell
python -m analog_finder terrain
python -m analog_finder surface
python -m analog_finder fetch aux
python -m analog_finder context
python -m analog_finder merge
```

`terrain` reads the 27 SRTMGL30 tiles, `surface` the monthly MODIS files and the EMIT file,
`context` the volcano and impact tables (and the POWER boxes, see step 4). Each product checks
itself against known places and stops if a file is read wrongly. `merge` adds the layers to
`data/processed/grid.bin`. `python -m analog_finder inspect FILE` lists the variables of any
HDF4 or NetCDF file.

### 4. Dryness from NASA POWER (no login, about an hour)

```powershell
python -m analog_finder fetch power-grid --dry-run
python -m analog_finder fetch power-grid
python -m analog_finder context --only dryness
python -m analog_finder merge
```

One request per 10 × 10 degree box with land; boxes already saved are skipped, so the command
can be stopped and started again. Until this step is done, the `dryness` criterion of the
biosignatures task is shown as "no data yet".

### 5. Score, validate, build the page

```powershell
python -m analog_finder score
python -m analog_finder web
```

### Optional

- `python -m analog_finder fetch power` and `fetch copdem`: climate (NASA POWER) and Copernicus DEM tiles at the known analog sites only, for site cards and Antarctic detail. Not used by the ranking.
- `python -m analog_finder grid`: rebuilds the land grid and the low-Sun features from scratch (about 3 minutes); then rerun `merge`.
- `python -m analog_finder reference`: rewrites the GeoJSON layers and `analogs_grid.csv` after editing `known_analogs.csv` or `targets.yaml`.
- `python pipeline/scripts/make_sources_doc.py`: regenerates `docs/data_sources.md` after editing `sources.yaml`.

## Conventions

- Earth longitudes run from -180 to 180. Moon and Mars longitudes in `targets.yaml` are east-positive, 0 to 360.
- Grid row 0 is the northernmost row, column 0 starts at 180 W. A cell is kept when at least 20 % of it is land.
- Binary grids: `value = min + q / 254 * (max - min)`, `q = 255` means no data (see `export/to_binary.py`).
- Terrain of all three worlds is compared at about 1 km: SRTMGL30 (926 m), MOLA MEGDR 64 pixels per degree (926 m), LOLA 240 m averaged 4 × 4 (960 m).
- "Low Sun" means the Sun 0 to 5 degrees above a flat horizon. At the lunar south pole it never climbs higher than about 2 degrees.
- Known analogs validate the ranking; they are never used to tune it.

## What is not done yet

- No detail below the 55 km cell (smaller windows, 30 m DEMs for the top candidates), no side-by-side images of Earth and target, no protected-area layer (the WDPA data may not be redistributed). The machine-learning layer is experimental and lives on the `ml-layer` branch.
- No maps of the Moon and Mars on the page; targets are chosen from a list.

## Use of AI

Space Apps asks every team to say where and how AI was used. In this project Claude
(Anthropic) wrote, from the team's plan and under the team's review: the data pipeline
(download scripts, file readers, feature and scoring code, validation, tests), the web page,
the documentation, and the reference tables. The coordinates and uses in the reference tables
were collected from the sources named in each row; rows marked `approx` or `to confirm` were
not checked against a source. Every number on the page and in the documents is computed by
the code from the listed datasets, not written by hand. The team chose the targets,
the test tasks and their weights, and checked the results.

## Data and licences

Code: MIT (see `LICENSE`). Data keep the terms of their providers; citations for every
dataset are in `docs/data_sources.md`. NASA does not endorse any non-U.S. Government
entity; for ESA, CSA, JAXA and other non-U.S. Government sources the data-use terms of
that source apply.
