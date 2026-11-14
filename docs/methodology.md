# Method

How the Moon–Mars Analog Finder ranks places on Earth, what every number means, and how far the
result can be trusted. The code is in `pipeline/analog_finder/`; the numbers below come from
`data/processed/validation.json` of 14 November 2026. `python -m analog_finder score` rewrites
`data/processed/validation.md` with the current figures.

This is a screening tool. It says where on Earth the conditions of a lunar or Martian site look
similar for a given test. It is not an engineering assessment and not a site-selection
recommendation.

## 1. The question

For one target on the Moon or Mars (for example the Shackleton–de Gerlache ridge) and one test
task (for example rover mobility), which places on Earth reproduce the conditions that matter for
that test? An analog is good or bad only for a given task: a lava field can be excellent for cave
training and useless for testing ice drills.

## 2. The same yardstick on three worlds

- **Earth grid.** Land is cut into 0.5 degree cells (about 55 km). A cell is kept when at least 20 % of it is land: 88,883 cells. Row 0 is the northernmost row, column 0 starts at 180 W.
- **Terrain at one step.** Slopes, relief and roughness are computed at a ground step of about 1 km on all three worlds: SRTMGL30 for the Earth (926 m), MOLA MEGDR 64 pixels per degree for Mars (926 m), LOLA 240 m averaged 4 × 4 for the Moon (960 m). A slope measured at 5 m and one measured at 1 km are different quantities, so nothing finer is mixed in.
- **Targets.** 12 targets in `pipeline/config/targets.yaml`: 5 on the Moon (Shackleton–de Gerlache ridge and Mons Mouton are the main ones; Shackleton crater, de Gerlache crater and Malapert for context) and 7 on Mars (Jezero and Arcadia Planitia are the main ones; Gale, Phoenix, Viking 2 / Utopia, Meridiani, Mawrth Vallis). Each target has an analysis window (10–40 km radius on the Moon, 40–100 km on Mars).
- **Target fingerprint** (`data/processed/target_profiles.json`): share of the window in 9 slope classes (edges 0, 2, 5, 8, 10, 15, 20, 25, 30, 90 degrees), mean slope, relief P5–P95, median roughness (RMS of elevation in 3 × 3 windows); for the Moon also Diviner temperatures, the share where ice is stable within 1 m and the highest Sun elevation; for Mars the GRS water content.

## 3. Earth features

| Feature | Source | How it is made |
| --- | --- | --- |
| Slope classes, mean slope, relief, roughness, elevation | NASA SRTMGL30 | Same functions as for the targets, 60 × 60 pixels per cell |
| Surface temperature (day and night means, hottest and coldest month, day–night swing) | MODIS MOD11C3, 12 months of 2023 | 10 × 10 blocks of 0.05 degree pixels; at least 6 valid months |
| Greenness (NDVI mean and maximum) | MODIS MOD13C2, 12 months | Same |
| Snow cover (annual mean and each month), snow-free months | MODIS MOD10CM, 12 months | Codes for night, cloud and water are treated as unknown |
| Mineral abundances (11 minerals) | NASA EMIT L3 ASA | EMIT cells are a quarter cell off the grid and are averaged 2 × 2; only bare ground between 55 N and 54.5 S |
| Hours per day with the Sun 0–5 degrees up | Solar geometry (`features/sun.py`, checked against pvlib) | Best month and annual mean |
| Glacier share | Natural Earth glaciated areas | Share of the cell |
| Distance to the nearest Holocene volcano, and to the nearest basaltic one | Smithsonian Global Volcanism Program list | Great-circle distance from the cell centre, capped at 300 km |
| Distance to the rim of the nearest impact structure, its diameter | Earth Impact Database (PASSC) | Same, minus the structure radius |
| Annual precipitation | NASA POWER climatology (MERRA-2), 390 boxes of 10 × 10 degrees | Nearest POWER column, mean of the two rows around the cell centre; the API leaves out longitude 0, so the cells next to it take the neighbouring column |

Every product has a self-check against known places (Everest, the Dead Sea, the Sahara, Greenland,
the Amazon, Kilauea, Meteor Crater, Vredefort, Atacama). A failed check stops the run, because it
means a file is read mirrored, shifted or mis-scaled.

## 4. Criteria

Every criterion is a score from 0 to 1 per cell, or "unknown" when the data are missing. Unknown is
never turned into 0.

**Matched to the target** (the cell is compared with the fingerprint):

- `slope_hist` = 1 − ½ Σ|p_k − q_k| = Σ min(p_k, q_k), the overlap of the slope-class shares of the cell (p) and of the target (q).
- `relief` and `roughness` = exp(−½ ((ln(1 + x/a) − ln(1 + x*/a)) / 0.7)²), with x the cell value, x* the target value, a = 50 m for relief and 5 m for roughness. A factor of two in either direction gives about 0.5.

**Ranked in the useful direction** (Earth cannot reach the target's value, so cells are ranked by how far they go towards it):

- `cold`: percentile of the annual mean surface temperature, coldest first.
- `thermal_range`: percentile of the mean day–night swing, largest first.
- `low_sun`: percentile of the low-Sun hours per day in the best month.
- `ground_ice`: max(clip((273.15 K − T_mean) / 20 K, 0, 1), glacier share). A mean surface temperature under 0 °C is a common permafrost indicator; it is a proxy, not a measurement of ice.
- `bare_ground`: clip(1 − (NDVI − 0.05) / 0.25, 0, 1): 1 for bare ground, 0 at NDVI 0.30 and above.
- `snow_free`: snow-free months / 12.
- `composition` (Mars only): percentile of the summed abundance of minerals that form in water (kaolinite, montmorillonite, illite and muscovite, vermiculite, chlorite, gypsum, calcite, dolomite, hematite, goethite). The lunar highlands have none of these, so the criterion is not used for the Moon.
- `volcanic`: max(exp(−d_basalt / 50 km), 0.6 · exp(−d_any / 50 km)). Basaltic forms (shields, volcanic fields, fissure vents, cinder cones) are where lava tubes and fresh basalt are found.
- `impact`: exp(−d_rim / 40 km), 1 inside a structure.
- `dryness`: 1 − log10(P / 25 mm) / log10(1000 / 25), clipped to 0–1: 1 for 25 mm per year or less (hyper-arid), 0 for 1,000 mm or more. Present only after `fetch power-grid` and `context`.

## 5. Task score

For task t and cell x:

S_t(x) = Σ_i w_t,i · s_i(x) / Σ_i w_t,i, summed over the criteria that have data for x.

- **Coverage** is the share of the task's weight that had data. A cell with coverage under 0.5 gets no score; the coverage is shown on its card.
- **Hard filters** remove cells before ranking: `bare_ground_min` (mean NDVI above 0.25 fails), `flat_patch_exists` (under 5 % of the cell below 8 degrees fails), `ground_ice_present` (mean surface temperature at or above 0 °C and glacier share under 50 % fails), `snow_free_window` (no month with under 10 % snow fails), `road_access` (no major road of Natural Earth 1:10M within 50 km of the cell centre fails; small and unpaved roads are not in that map). Unknown values pass, except for the snow window. Safe access and protected areas have no data and are listed as not checked.
- The plan also mentions a weighted geometric mean as a switch; only the arithmetic mean is implemented.

Weights (`pipeline/config/tasks.yaml`; the sliders on the page start from these):

| Task | Worlds | Weights | Hard filters |
| --- | --- | --- | --- |
| Landing and descent navigation | Moon, Mars | slope classes 0.35, roughness 0.30, relief 0.10, low Sun 0.15, bare ground 0.10 | bare ground, flat patch |
| Rover mobility | Moon, Mars | slope classes 0.40, roughness 0.30, relief 0.10, bare ground 0.10, minerals 0.10 | bare ground (road access not checked) |
| Surface EVA and field geology | Moon | relief 0.25, slope classes 0.20, volcanic 0.20, impact 0.15, minerals 0.10, low Sun 0.10 | bare ground (safe access not checked) |
| Ice mining (ISRU) | Moon, Mars | ground ice 0.40, cold 0.30, bare ground 0.10, minerals 0.10, slope classes 0.10 | ground ice present |
| Operations under a low Sun | Moon | low Sun 0.45, relief 0.20, snow-free 0.20, bare ground 0.15 | snow-free window, bare ground |
| Caves and shelters | Moon, Mars | volcanic 0.60, bare ground 0.20, relief 0.20 | (safe access not checked) |
| Search for biosignatures | Mars | dryness 0.35, minerals 0.30, bare ground 0.15, day–night swing 0.10, cold 0.10 | bare ground (protected areas not checked) |

The weights were set by hand from the description of each test. They were not tuned on the known
analogs.

## 6. Validation

`data/reference/known_analogs.csv` lists 39 sites that agencies and research groups already use;
32 are marked `validate=yes` (natural landscapes the ranking should find again; habitats and
underwater sites are excluded). For every such site, every task it is listed for and every main
target of its world, the score of its cell is turned into a percentile among all ranked cells
(1.0 = best cell on Earth). A place picked at random gets a median of 0.5 and lands in the top 20 %
one time in five.

| Set | Pairs scored | Median percentile | In the top 20 % | In the top 10 % |
| --- | --- | --- | --- | --- |
| All tasks, scores only | 132 of 136 | 0.77 | 46 % | 33 % |
| All tasks, with hard filters | 78 of 136 | 0.72 | 41 % | 30 % |
| Without caves and EVA geology, scores only | 82 of 86 | 0.70 | 21 % | 6 % |
| Without caves and EVA geology, with hard filters | 46 of 86 | 0.41 | 13 % | 7 % |

By task (scores only): caves 0.99, EVA geology 0.92, low-Sun operations 0.76, mobility 0.75,
ice mining 0.69, biosignatures 0.58.

How to read this:

- **Caves and EVA geology** use the volcano and impact lists, and those lists contain many of the analog sites themselves (Craters of the Moon, Meteor Crater, Haughton). Their high percentiles show that the context layers work; they are not independent evidence that the method finds analogs.
- **The other tasks** put known sites clearly above a random place (median 0.70 against 0.50), but not into the very top: only 21 % are in the top 20 %, about the rate of chance. The main reason is scale: a site is a few hundred metres to a few kilometres across, while a cell is 55 km and mixes the site with its surroundings. Flat targets such as Arcadia Planitia are rarely matched by a whole Earth cell.
- **Hard filters** remove sites whose cell is mostly vegetated although the site itself is bare (Ries, Mistastin, Réunion), and for rover mobility the remote sites with no major road within 50 km (Haughton, Svalbard). With filters the independent median falls to 0.41, below a random place.

**Stability.** Every weight of a task was changed at random by up to ±25 % (30 draws). The share of
the baseline top 5 % cells that stays in the top 5 %: ice mining 99 %, landing 96 %, EVA geology
95 %, mobility 95 %, caves 92 %, biosignatures 83 %, low-Sun operations 75 %. The page shows the
same test for the selected cell (20 draws, top 10 %).

**Sanity.** Share of the top 5 % cells under dense vegetation (NDVI over 0.4): 0 % for every task
except caves (13 %, volcanic islands and tropical volcanoes; the caves task has no bare-ground
filter).

**No spatial hold-out.** The plan proposed hiding each known site and its neighbours. No weight or
threshold is fitted to the known sites, so every site is already unseen by the method and a
hold-out would give the same numbers.

## 7. Getting there and checking a place

- **Road access.** Natural Earth 1:10M roads (ferry routes left out) are densified to 5 km steps and binned at 0.1 degree; the distance from each cell centre to the nearest bin is the `road_dist_km` feature (capped at 300 km). It drives the `road_access` filter of the mobility task.
- **Trip CO₂.** The card of a cell estimates one passenger's flight from an origin city (Kyiv unless the viewer picks another): great-circle distance + 8 %, times 68.0 g CO₂ per passenger-km under 3,700 km or 63.2 g above (economy class, UK DESNZ greenhouse gas conversion factors 2025, methodology paper, tables of passenger flights), and ×1.7 for the non-CO₂ effects of flight, the paper's central estimate. Ground travel is not included.
- **Check a place.** The page has the 7,342 populated places of Natural Earth (`data/reference/cities.csv`). Picking one shows the score and percentile of its cell for every task with the default weights, or why it has none, and the nearest cell in the top 10 % for the current task.

## 8. Low-Sun windows

Hours per day with the Sun 0–5 degrees above a flat horizon depend only on latitude and date; they are
computed for every grid row and month (`data/processed/lowsun_by_latitude.csv`, checked against pvlib). The
page combines them with the monthly MODIS snow cover of 2023: a month counts for low-Sun work when its
snow cover is under 10 %. The "Low-Sun window" map shows one month at a time; the card of a cell shows all
twelve and names the best snow-free month.

## 9. What Earth cannot reproduce

`data/reference/environment_gaps.json` lists gravity, surface pressure, length of the solar day,
spin-axis tilt, sunlight above the atmosphere, radiation dose and surface temperature for the
Earth, the Moon and Mars, with sources (NASA Planetary Fact Sheets, Hassler et al. 2014, Zhang et al.
2020, UNSCEAR 2008). The page shows this table next to every candidate and never mixes it into the
score. The card of a lunar target also lists the values of the target that no Earth cell matches:
the coldest surface (about 39 K at the ridge), the share where ice is stable within 1 m, and the
highest Sun elevation.

## 10. Known limits

- Scale: 55 km cells against sites of a few kilometres. Smaller windows inside each cell are the main improvement left.
- SRTMGL30 has no data south of 60 S, so Antarctic cells have no terrain criteria; north of 60 N the values come from a coarser source.
- Ground ice is a temperature proxy; the volcano and impact criteria are distances to listed points, not mapped outcrops.
- MODIS values are for 2023 only. Polar night removes winter months, so means above about 60 degrees are warm-biased.
- EMIT covers bare ground between 55 N and 54.5 S only; outside, the mineral criterion is unknown.
- Sun elevations assume a flat horizon.
- Coordinates of 11 known sites are approximate and 4 uses are still to be confirmed (marked in `known_analogs.csv`).

## 11. Reproducing the result

```powershell
pip install -e "pipeline[geo,earth,formats,dev]"
python -m pytest pipeline
python -m analog_finder all            # uses the processed data in the repository
python -m analog_finder all --fetch    # downloads everything first (Earthdata Login needed)
```

The web page `webapp/index.html` is built from `data/processed/` by `python -m analog_finder web`.
It recomputes the same weighted mean in the browser from the criteria stored as bytes (0–254), so
its scores differ from the Python ones by less than 0.4 %.
