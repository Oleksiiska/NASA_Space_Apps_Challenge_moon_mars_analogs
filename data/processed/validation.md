# Validation against known analog sites

Each site is a cell of the 0.5 degree grid; its score is turned into a percentile among all ranked cells (1.0 = best cell on Earth for that task and target). A random site would get a median of 0.5 and land in the top 20 % one time in five. Known analogs were not used to set any weight or threshold.

- Scores only: 46 of 50 site-task-target pairs scored, median percentile 0.647, top 20 % in 24%, top 10 % in 9%.
- With the hard filters of each task: 36 pairs left, median 0.573, top 20 % in 17%. Filters remove sites whose 55 km cell is mostly vegetated although the site itself is bare (impact craters in forest, volcanic islands).

| Task | pairs | median percentile | top 20 % | top 10 % |
|---|---|---|---|---|
| biosignatures | 12 | 0.527 | 17% | 0% |
| eva_geology | 16 | 0.716 | 25% | 12% |
| isru_ice | 2 | 0.615 | 0% | 0% |
| mobility | 16 | 0.705 | 31% | 12% |
| caves | 0 | not ranked: no cell has enough data (missing: volcanic) | | |

## Per site

| Site | Task | Target | Percentile | With filters | Failed filters |
|---|---|---|---|---|---|
| atacama | biosignatures | arcadia_planitia | 0.481 | 0.393 |  |
| atacama | biosignatures | jezero | 0.481 | 0.393 |  |
| dallol | biosignatures | arcadia_planitia | 0.708 | 0.617 |  |
| dallol | biosignatures | jezero | 0.708 | 0.617 |  |
| kangerlussuaq | biosignatures | arcadia_planitia | None | None |  |
| kangerlussuaq | biosignatures | jezero | None | None |  |
| makgadikgadi | biosignatures | arcadia_planitia | 0.381 | 0.295 |  |
| makgadikgadi | biosignatures | jezero | 0.381 | 0.295 |  |
| pilbara | biosignatures | arcadia_planitia | None | None |  |
| pilbara | biosignatures | jezero | None | None |  |
| qaidam | biosignatures | arcadia_planitia | 0.878 | 0.829 |  |
| qaidam | biosignatures | jezero | 0.878 | 0.829 |  |
| rio_tinto | biosignatures | arcadia_planitia | 0.23 | None | bare_ground_min |
| rio_tinto | biosignatures | jezero | 0.23 | None | bare_ground_min |
| tirez | biosignatures | arcadia_planitia | 0.574 | 0.482 |  |
| tirez | biosignatures | jezero | 0.574 | 0.482 |  |
| askja | eva_geology | mons_mouton | 0.83 | 0.793 |  |
| askja | eva_geology | shackleton_ridge | 0.829 | 0.79 |  |
| kilbourne_hole | eva_geology | mons_mouton | 0.392 | 0.366 |  |
| kilbourne_hole | eva_geology | shackleton_ridge | 0.409 | 0.372 |  |
| lmas_reunion | eva_geology | mons_mouton | 0.92 | None | bare_ground_min |
| lmas_reunion | eva_geology | shackleton_ridge | 0.945 | None | bare_ground_min |
| mistastin | eva_geology | mons_mouton | 0.672 | None | bare_ground_min |
| mistastin | eva_geology | shackleton_ridge | 0.611 | None | bare_ground_min |
| ries | eva_geology | mons_mouton | 0.539 | None | bare_ground_min |
| ries | eva_geology | shackleton_ridge | 0.54 | None | bare_ground_min |
| rio_grande_del_norte | eva_geology | mons_mouton | 0.76 | 0.726 |  |
| rio_grande_del_norte | eva_geology | shackleton_ridge | 0.763 | 0.724 |  |
| sp_crater | eva_geology | mons_mouton | 0.622 | 0.585 |  |
| sp_crater | eva_geology | shackleton_ridge | 0.617 | 0.56 |  |
| sw_nevada_vf | eva_geology | mons_mouton | 0.791 | 0.757 |  |
| sw_nevada_vf | eva_geology | shackleton_ridge | 0.799 | 0.76 |  |
| kangerlussuaq | isru_ice | arcadia_planitia | 0.61 | 0.245 |  |
| kangerlussuaq | isru_ice | jezero | 0.62 | 0.265 |  |
| askja | mobility | mons_mouton | 0.829 | 0.802 |  |
| askja | mobility | shackleton_ridge | 0.844 | 0.808 |  |
| atacama | mobility | arcadia_planitia | 0.17 | 0.13 |  |
| atacama | mobility | jezero | 0.775 | 0.751 |  |
| death_valley | mobility | arcadia_planitia | 0.173 | 0.133 |  |
| death_valley | mobility | jezero | 0.736 | 0.713 |  |
| lmas_reunion | mobility | mons_mouton | 0.785 | None | bare_ground_min |
| lmas_reunion | mobility | shackleton_ridge | 0.841 | None | bare_ground_min |
| makgadikgadi | mobility | arcadia_planitia | 0.614 | 0.508 |  |
| makgadikgadi | mobility | jezero | 0.162 | 0.072 |  |
| mdrs | mobility | arcadia_planitia | 0.262 | 0.224 |  |
| mdrs | mobility | jezero | 0.986 | 0.961 |  |
| qaidam | mobility | arcadia_planitia | 0.31 | 0.269 |  |
| qaidam | mobility | jezero | 0.998 | 0.994 |  |
| sp_crater | mobility | mons_mouton | 0.674 | 0.597 |  |
| sp_crater | mobility | shackleton_ridge | 0.673 | 0.55 |  |

## How to read this

- A cell is about 55 km across; a site is much smaller. A flat Martian plain (Arcadia) is rarely matched by a whole cell.
- Earth cannot reach lunar or Martian cold, vacuum or radiation. Cold, thermal range and low Sun are ranked in the useful direction only.
- Volcanic, impact and dryness layers are not in the data yet, so geology tasks lean on terrain; the caves task cannot be ranked.
