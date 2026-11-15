# Validation against known analog sites

Each site is a cell of the 0.5 degree grid; its score is turned into a percentile among all ranked cells (1.0 = best cell on Earth for that task and target). A random site would get a median of 0.5 and land in the top 20 % one time in five. Known analogs were not used to set any weight or threshold.

- Scores only: 128 of 136 site-task-target pairs scored, median percentile 0.782, top 20 % in 48%, top 10 % in 34%.
- With the hard filters of each task: 78 pairs left, median 0.722, top 20 % in 44%. Filters remove sites whose 55 km cell is mostly vegetated although the site itself is bare (impact craters in forest, volcanic islands), remote sites with no major road within 50 km for rover mobility, and, for operations under a low Sun, cells without a snow-free month that has at least 2 h a day of low Sun (glaciated cells such as Svalbard and the Antarctic sites).
- Low Sun is not part of any score: it depends only on latitude and season, so the page shows it as a separate window (hours per day with the Sun 0-5 degrees up in a snow-free month, and which month).
- Independent part: the tasks caves, eva_geology use the volcano and impact lists, and those lists contain many of the analog sites themselves, so their high percentiles show that the layers work, not that the method finds analogs on its own. Without them: 78 pairs, median percentile 0.673, top 20 % in 22%, top 10 % in 6%.

| Task | pairs | median percentile | top 20 % | top 10 % |
|---|---|---|---|---|
| biosignatures | 20 | 0.575 | 20% | 10% |
| caves | 12 | 0.994 | 100% | 100% |
| eva_geology | 38 | 0.915 | 87% | 68% |
| isru_ice | 14 | 0.694 | 0% | 0% |
| low_sun_ops | 4 | 0.447 | 0% | 0% |
| mobility | 40 | 0.75 | 32% | 8% |

## Per site

| Site | Task | Target | Percentile | With filters | Failed filters |
|---|---|---|---|---|---|
| atacama | biosignatures | arcadia_planitia | 0.86 | 0.742 |  |
| atacama | biosignatures | jezero | 0.86 | 0.742 |  |
| dallol | biosignatures | arcadia_planitia | 0.65 | 0.36 |  |
| dallol | biosignatures | jezero | 0.65 | 0.36 |  |
| kangerlussuaq | biosignatures | arcadia_planitia | 0.545 | 0.192 |  |
| kangerlussuaq | biosignatures | jezero | 0.545 | 0.192 |  |
| makgadikgadi | biosignatures | arcadia_planitia | 0.54 | 0.186 |  |
| makgadikgadi | biosignatures | jezero | 0.54 | 0.186 |  |
| mcmurdo_dry_valleys | biosignatures | arcadia_planitia | 0.759 | 0.556 |  |
| mcmurdo_dry_valleys | biosignatures | jezero | 0.759 | 0.556 |  |
| pilbara | biosignatures | arcadia_planitia | 0.473 | 0.096 |  |
| pilbara | biosignatures | jezero | 0.473 | 0.096 |  |
| qaidam | biosignatures | arcadia_planitia | 0.923 | 0.858 |  |
| qaidam | biosignatures | jezero | 0.923 | 0.858 |  |
| rio_tinto | biosignatures | arcadia_planitia | 0.48 | None | bare_ground_min |
| rio_tinto | biosignatures | jezero | 0.48 | None | bare_ground_min |
| svalbard | biosignatures | arcadia_planitia | 0.544 | 0.191 |  |
| svalbard | biosignatures | jezero | 0.544 | 0.191 |  |
| tirez | biosignatures | arcadia_planitia | 0.605 | 0.285 |  |
| tirez | biosignatures | jezero | 0.605 | 0.285 |  |
| chill_ice_lava_tube | caves | arcadia_planitia | 0.932 | 0.932 |  |
| chill_ice_lava_tube | caves | jezero | 0.994 | 0.994 |  |
| chill_ice_lava_tube | caves | mons_mouton | 0.987 | 0.987 |  |
| chill_ice_lava_tube | caves | shackleton_ridge | 0.987 | 0.987 |  |
| craters_of_the_moon | caves | arcadia_planitia | 0.993 | 0.993 |  |
| craters_of_the_moon | caves | jezero | 0.996 | 0.996 |  |
| craters_of_the_moon | caves | mons_mouton | 0.994 | 0.994 |  |
| craters_of_the_moon | caves | shackleton_ridge | 0.993 | 0.993 |  |
| lanzarote_timanfaya | caves | arcadia_planitia | 0.998 | 0.998 |  |
| lanzarote_timanfaya | caves | jezero | 0.994 | 0.994 |  |
| lanzarote_timanfaya | caves | mons_mouton | 0.996 | 0.996 |  |
| lanzarote_timanfaya | caves | shackleton_ridge | 0.996 | 0.996 |  |
| askja | eva_geology | mons_mouton | 0.915 | 0.91 |  |
| askja | eva_geology | shackleton_ridge | 0.905 | 0.899 |  |
| craters_of_the_moon | eva_geology | mons_mouton | 0.914 | 0.909 |  |
| craters_of_the_moon | eva_geology | shackleton_ridge | 0.92 | 0.915 |  |
| etna | eva_geology | mons_mouton | 0.959 | None | bare_ground_min |
| etna | eva_geology | shackleton_ridge | 0.958 | None | bare_ground_min |
| gros_morne | eva_geology | mons_mouton | 0.772 | None | bare_ground_min |
| gros_morne | eva_geology | shackleton_ridge | 0.77 | None | bare_ground_min |
| haughton | eva_geology | mons_mouton | 0.92 | 0.915 |  |
| haughton | eva_geology | shackleton_ridge | 0.922 | 0.918 |  |
| hi_seas | eva_geology | mons_mouton | 1.0 | None | bare_ground_min |
| hi_seas | eva_geology | shackleton_ridge | 0.999 | None | bare_ground_min |
| kilauea | eva_geology | mons_mouton | 0.986 | None | bare_ground_min |
| kilauea | eva_geology | shackleton_ridge | 0.983 | None | bare_ground_min |
| kilbourne_hole | eva_geology | mons_mouton | 0.506 | 0.525 |  |
| kilbourne_hole | eva_geology | shackleton_ridge | 0.505 | 0.524 |  |
| lanzarote_timanfaya | eva_geology | mons_mouton | 0.873 | 0.865 |  |
| lanzarote_timanfaya | eva_geology | shackleton_ridge | 0.879 | 0.87 |  |
| lmas_reunion | eva_geology | mons_mouton | 0.998 | None | bare_ground_min |
| lmas_reunion | eva_geology | shackleton_ridge | 0.999 | None | bare_ground_min |
| meteor_crater | eva_geology | mons_mouton | 0.963 | 0.962 |  |
| meteor_crater | eva_geology | shackleton_ridge | 0.959 | 0.959 |  |
| mistastin | eva_geology | mons_mouton | 0.938 | None | bare_ground_min |
| mistastin | eva_geology | shackleton_ridge | 0.923 | None | bare_ground_min |
| ries | eva_geology | mons_mouton | 0.905 | None | bare_ground_min |
| ries | eva_geology | shackleton_ridge | 0.906 | None | bare_ground_min |
| rio_grande_del_norte | eva_geology | mons_mouton | 0.796 | 0.786 |  |
| rio_grande_del_norte | eva_geology | shackleton_ridge | 0.8 | 0.788 |  |
| sp_crater | eva_geology | mons_mouton | 0.879 | 0.871 |  |
| sp_crater | eva_geology | shackleton_ridge | 0.88 | 0.872 |  |
| sudbury | eva_geology | mons_mouton | 0.907 | None | bare_ground_min |
| sudbury | eva_geology | shackleton_ridge | 0.912 | None | bare_ground_min |
| svalbard | eva_geology | mons_mouton | 0.916 | 0.911 |  |
| svalbard | eva_geology | shackleton_ridge | 0.923 | 0.919 |  |
| sw_nevada_vf | eva_geology | mons_mouton | 0.845 | 0.836 |  |
| sw_nevada_vf | eva_geology | shackleton_ridge | 0.846 | 0.837 |  |
| teide | eva_geology | mons_mouton | 0.993 | None | bare_ground_min |
| teide | eva_geology | shackleton_ridge | 0.994 | None | bare_ground_min |
| haughton | isru_ice | arcadia_planitia | 0.701 | 0.422 |  |
| haughton | isru_ice | jezero | 0.698 | 0.415 |  |
| haughton | isru_ice | mons_mouton | 0.693 | 0.406 |  |
| haughton | isru_ice | shackleton_ridge | 0.694 | 0.408 |  |
| kangerlussuaq | isru_ice | arcadia_planitia | 0.61 | 0.245 |  |
| kangerlussuaq | isru_ice | jezero | 0.62 | 0.265 |  |
| mcmurdo_dry_valleys | isru_ice | arcadia_planitia | 0.719 | 0.457 |  |
| mcmurdo_dry_valleys | isru_ice | jezero | 0.74 | 0.497 |  |
| mcmurdo_dry_valleys | isru_ice | mons_mouton | 0.74 | 0.498 |  |
| mcmurdo_dry_valleys | isru_ice | shackleton_ridge | 0.74 | 0.498 |  |
| svalbard | isru_ice | arcadia_planitia | 0.621 | 0.266 |  |
| svalbard | isru_ice | jezero | 0.628 | 0.282 |  |
| svalbard | isru_ice | mons_mouton | 0.657 | 0.337 |  |
| svalbard | isru_ice | shackleton_ridge | 0.658 | 0.339 |  |
| concordia | low_sun_ops | mons_mouton | None | None | sun_window |
| concordia | low_sun_ops | shackleton_ridge | None | None | sun_window |
| haughton | low_sun_ops | mons_mouton | 0.466 | 0.914 |  |
| haughton | low_sun_ops | shackleton_ridge | 0.459 | 0.906 |  |
| mcmurdo_dry_valleys | low_sun_ops | mons_mouton | None | None | sun_window |
| mcmurdo_dry_valleys | low_sun_ops | shackleton_ridge | None | None | sun_window |
| svalbard | low_sun_ops | mons_mouton | 0.415 | None | sun_window |
| svalbard | low_sun_ops | shackleton_ridge | 0.434 | None | sun_window |
| askja | mobility | mons_mouton | 0.829 | 0.798 |  |
| askja | mobility | shackleton_ridge | 0.844 | 0.807 |  |
| atacama | mobility | arcadia_planitia | 0.17 | None | road_access |
| atacama | mobility | jezero | 0.775 | None | road_access |
| craters_of_the_moon | mobility | arcadia_planitia | 0.403 | 0.391 |  |
| craters_of_the_moon | mobility | jezero | 0.746 | 0.703 |  |
| craters_of_the_moon | mobility | mons_mouton | 0.615 | 0.531 |  |
| craters_of_the_moon | mobility | shackleton_ridge | 0.675 | 0.554 |  |
| death_valley | mobility | arcadia_planitia | 0.173 | 0.131 |  |
| death_valley | mobility | jezero | 0.736 | 0.692 |  |
| etna | mobility | arcadia_planitia | 0.276 | None | bare_ground_min |
| etna | mobility | jezero | 0.819 | None | bare_ground_min |
| etna | mobility | mons_mouton | 0.778 | None | bare_ground_min |
| etna | mobility | shackleton_ridge | 0.806 | None | bare_ground_min |
| haughton | mobility | arcadia_planitia | 0.922 | None | road_access |
| haughton | mobility | jezero | 0.595 | None | road_access |
| haughton | mobility | mons_mouton | 0.706 | None | road_access |
| haughton | mobility | shackleton_ridge | 0.757 | None | road_access |
| hi_seas | mobility | arcadia_planitia | 0.072 | None | bare_ground_min |
| hi_seas | mobility | jezero | 0.605 | None | bare_ground_min |
| hi_seas | mobility | mons_mouton | 0.886 | None | bare_ground_min |
| hi_seas | mobility | shackleton_ridge | 0.888 | None | bare_ground_min |
| kilauea | mobility | arcadia_planitia | 0.267 | None | bare_ground_min |
| kilauea | mobility | jezero | 0.896 | None | bare_ground_min |
| kilauea | mobility | mons_mouton | 0.753 | None | bare_ground_min |
| kilauea | mobility | shackleton_ridge | 0.767 | None | bare_ground_min |
| lmas_reunion | mobility | mons_mouton | 0.785 | None | bare_ground_min, road_access |
| lmas_reunion | mobility | shackleton_ridge | 0.841 | None | bare_ground_min, road_access |
| makgadikgadi | mobility | arcadia_planitia | 0.614 | None | road_access |
| makgadikgadi | mobility | jezero | 0.162 | None | road_access |
| mcmurdo_dry_valleys | mobility | arcadia_planitia | None | None | road_access |
| mcmurdo_dry_valleys | mobility | jezero | None | None | road_access |
| mcmurdo_dry_valleys | mobility | mons_mouton | None | None | road_access |
| mcmurdo_dry_valleys | mobility | shackleton_ridge | None | None | road_access |
| mdrs | mobility | arcadia_planitia | 0.262 | None | road_access |
| mdrs | mobility | jezero | 0.986 | None | road_access |
| qaidam | mobility | arcadia_planitia | 0.31 | 0.296 |  |
| qaidam | mobility | jezero | 0.998 | 0.992 |  |
| sp_crater | mobility | mons_mouton | 0.674 | 0.598 |  |
| sp_crater | mobility | shackleton_ridge | 0.673 | 0.551 |  |
| teide | mobility | arcadia_planitia | 0.257 | None | bare_ground_min |
| teide | mobility | jezero | 0.759 | None | bare_ground_min |
| teide | mobility | mons_mouton | 0.813 | None | bare_ground_min |
| teide | mobility | shackleton_ridge | 0.861 | None | bare_ground_min |

## Stability when the weights change

Every weight of a task was changed at random by up to +-25 % (30 draws). Share of the baseline top 5 % cells that stay in the top 5 % (1.0 = unchanged), and the share of those top cells under dense vegetation (NDVI over 0.4; should be near zero, though the bare-ground filter removes dense vegetation by construction).

| Task | stays in top 5 % | dense vegetation in top |
|---|---|---|
| biosignatures | 88% | 0% |
| caves | 92% | 13% |
| eva_geology | 97% | 0% |
| isru_ice | 99% | 0% |
| landing | 97% | 0% |
| low_sun_ops | 89% | 0% |
| mobility | 97% | 0% |

No spatial hold-out is run: no weight or threshold is fitted to the known sites, so every site is already unseen by the method.

## How to read this

- A cell is about 55 km across; a site is much smaller. A flat Martian plain (Arcadia) is rarely matched by a whole cell.
- Earth cannot reach lunar or Martian cold, vacuum or radiation. Cold, thermal range and low Sun are ranked in the useful direction only.
- Volcanic fields and impact structures enter as distance to the nearest listed point or rim; dryness comes from NASA POWER precipitation when its layer was built.
