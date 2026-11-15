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
  many of the sites themselves, the median is 0.66 and only 17 % of the sites reach the top
  20 %: the 55 km cell is much larger than a real site. See `docs/methodology.md`, section 6.
- As the page shows them (a site removed by a filter counts as 0), the 32 known sites average the
  0.615 percentile, and they outrank 38 clearly unsuitable places with an AUC of 0.92; 9 hold-out
  sites collected after the tuning give 0.617 and 0.92 (`python -m analog_finder evaluate`).
- Changing every weight by up to ±25 % keeps 86–99 % of the top 5 % cells in place.

## What the page does

- Map of all land cells coloured by the score of the chosen task and target; 10 best regions (at least 600 km apart); sliders for every weight and switches for the hard filters.
- **Low-Sun window** map mode: for any month, hours per day with the Sun 0–5 degrees up, with cells under snow that month hatched; a play button runs through the year.
- Low Sun is kept out of the similarity score (it depends only on latitude and season). Each candidate shows its usable window instead, e.g. 4.4 h a day in July, and tasks that need lunar-like light can require at least 2 h of it.
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
    fetch/               downloads: NASA PDS, Earthdata, NASA POWER points, Copernicus DEM, context lists
    io/                  readers: PDS3 images and tables, SRTM tiles, HDF4 / NetCDF inspection
    prep/                Earth land grid, feature layers, reference layers
    features/            terrain, Sun geometry, MODIS, EMIT and IMERG surface layers, volcano / impact / road layers
    targets/             feature "fingerprints" of the Moon and Mars targets
    scoring.py           criteria and task scores
    validate.py          known-analog validation, weight sensitivity, export for the web page
    evaluate.py          metrics of the ranking against a baseline, hold-out sets
    ml/                  resemblance to the known analog sites (PU learning, shown in the cell card)
    pipeline_all.py      the `all` command
    export/              compact binary grid
  scripts/               generator of docs/data_sources.md
  tests/                 they need no downloads
webapp/
  template.html          the page; build_app.py embeds data/processed into index.html
data/
  raw/                   downloads (not committed, except the Natural Earth land and glacier masks)
  interim/               intermediate layers (not committed)
  processed/             grid, target profiles, criteria and validation: everything the page reads
  reference/             known analogs, targets, spotlight places, what Earth cannot reproduce
docs/                    methodology.md, data_sources.md
.github/workflows/ci.yml tests and a full `all` run on every push
.github/workflows/deploy.yml  after the tests pass on analog-finder: upload the page to the demo server
deploy/                  Caddy web server (Caddyfile, docker-compose.yml)
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
user profile, not in this repository. MCD12C1 (land cover, 1.2 GB) gives the share of bare 5 km pixels used by the bare-ground filter.

### 3. Earth feature layers

```powershell
python -m analog_finder terrain
python -m analog_finder surface
python -m analog_finder fetch aux
python -m analog_finder context
python -m analog_finder merge
```

`terrain` reads the 27 SRTMGL30 tiles, `surface` the monthly MODIS files and the EMIT file,
`context` the volcano, impact and road lists (step 4). Each product checks
itself against known places and stops if a file is read wrongly. `merge` adds the layers to
`data/processed/grid.bin`. `python -m analog_finder inspect FILE` lists the variables of any
HDF4 or NetCDF file.

### 4. Volcano, impact and road context (no login)

```powershell
python -m analog_finder fetch context
python -m analog_finder fetch aux
python -m analog_finder context
python -m analog_finder merge
```

`fetch context` downloads the Smithsonian GVP volcano lists (Holocene and Pleistocene) and the
Wikipedia/Wikidata lists of confirmed impact structures (4 MB). `context` writes
`data/reference/volcanoes.csv` and `impact_structures.csv` (kept in the repository, so it also runs
without the downloads) and the distance from every cell to the nearest volcano and impact rim. The
`volcanic` and `impact` criteria give full score within 25 km and none beyond 150 km; they say nothing
about how well a structure is exposed. With `fetch aux` done it also adds the distance to a major
Natural Earth road (the `road_access` switch of rover mobility and the "getting there" part of the card).

### 4b. Precipitation for the dryness criterion (Earthdata Login)

```powershell
python -m analog_finder fetch earth --only earth_imerg_monthly --year 2023
python -m analog_finder surface --only precip
python -m analog_finder merge
```

12 monthly GPM IMERG files (214 MB) from GES DISC. The first download may stop with "EULA acceptance
failure": approve "NASA GESDISC DATA ARCHIVE" under Applications > Authorized Apps in your Earthdata
profile and run it again.

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

### Did a change make the ranking better?

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
`--holdout2` does the same for `data/reference/holdout2_analogs.csv` (8 sites collected on 15 November 2026, before
the experiments they guard). Every metric also has an `_ind` version over the tasks that do not use the volcano and
impact lists (those lists contain many of the sites, so caves and EVA geology rank them high by construction).


## Conventions

- Earth longitudes run from -180 to 180. Moon and Mars longitudes in `targets.yaml` are east-positive, 0 to 360.
- Grid row 0 is the northernmost row, column 0 starts at 180 W. A cell is kept when at least 20 % of it is land.
- Binary grids: `value = min + q / 254 * (max - min)`, `q = 255` means no data (see `export/to_binary.py`).
- Terrain of all three worlds is compared at about 1 km: SRTMGL30 (926 m), MOLA MEGDR 64 pixels per degree (926 m), LOLA 240 m averaged 4 × 4 (960 m).
- "Low Sun" means the Sun 0 to 5 degrees above a flat horizon. At the lunar south pole it never climbs higher than about 2 degrees.
- Known analogs validate the ranking; they are never used to tune it.

## What is not done yet

- Dryness is precipitation only (GPM IMERG 2023), not an aridity index; a 55 km cell around a salt basin (Dallol,
  Tirez) also holds the wetter hills around it.
- Volcanic and impact criteria are distances to point lists; tropical volcanoes under forest rank high in the caves
  and EVA tasks (28-38 % dense vegetation in their top 5 %).
- No detail below the 55 km cell (smaller windows, 30 m DEMs for the top candidates), no side-by-side images of Earth and target, no protected-area layer (the WDPA data may not be redistributed), no machine-learning layer.
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
