# Validation against known analog sites

Each site is a cell of the 0.5 degree grid; its score is turned into a percentile among all ranked cells (1.0 = best cell on Earth for that task and target). A random site would get a median of 0.5 and land in the top 20 % one time in five. Known analogs were not used to set any weight or threshold.

- Scores only: 128 of 136 site-task-target pairs scored, median percentile 0.771, top 20 % in 44%, top 10 % in 35%.
- With the hard filters of each task: 116 pairs left, median 0.765, top 20 % in 47%. Filters remove sites whose 55 km cell is mostly vegetated although the site itself is bare (impact craters in forest, volcanic islands), the ice-sheet cell of the McMurdo Dry Valleys, and, for operations under a low Sun, cells without a snow-free month that has at least 2 h a day of low Sun (glaciated cells such as Svalbard and the Antarctic sites). Optional filters (the road filter of rover mobility, the Sun window of landing and EVA geology) are off by default and not applied here.
- Low Sun is not part of any score: it depends only on latitude and season, so the page shows it as a separate window (hours per day with the Sun 0-5 degrees up in a snow-free month, and which month).
- Independent part: the tasks caves, eva_geology use the volcano and impact lists, and those lists contain many of the analog sites themselves, so their high percentiles show that the layers work, not that the method finds analogs on its own. Without them: 78 pairs, median percentile 0.657, top 20 % in 17%, top 10 % in 4%.

| Task | pairs | median percentile | top 20 % | top 10 % |
|---|---|---|---|---|
| biosignatures | 20 | 0.54 | 0% | 0% |
| caves | 12 | 0.985 | 100% | 100% |
| eva_geology | 38 | 0.974 | 82% | 79% |
| isru_ice | 14 | 0.694 | 0% | 0% |
| low_sun_ops | 4 | 0.447 | 0% | 0% |
| mobility | 40 | 0.75 | 32% | 8% |

## Per site

| Site | Task | Target | Percentile | With filters | Failed filters |
|---|---|---|---|---|---|
| atacama | biosignatures | arcadia_planitia | 0.598 | 0.616 |  |
| atacama | biosignatures | jezero | 0.598 | 0.616 |  |
| dallol | biosignatures | arcadia_planitia | 0.594 | 0.604 |  |
| dallol | biosignatures | jezero | 0.594 | 0.604 |  |
| kangerlussuaq | biosignatures | arcadia_planitia | 0.451 | 0.229 |  |
| kangerlussuaq | biosignatures | jezero | 0.451 | 0.229 |  |
| makgadikgadi | biosignatures | arcadia_planitia | 0.473 | 0.271 |  |
| makgadikgadi | biosignatures | jezero | 0.473 | 0.271 |  |
| mcmurdo_dry_valleys | biosignatures | arcadia_planitia | 0.777 | None | not_ice_sheet |
| mcmurdo_dry_valleys | biosignatures | jezero | 0.777 | None | not_ice_sheet |
| pilbara | biosignatures | arcadia_planitia | 0.491 | 0.312 |  |
| pilbara | biosignatures | jezero | 0.491 | 0.312 |  |
| qaidam | biosignatures | arcadia_planitia | 0.796 | 0.956 |  |
| qaidam | biosignatures | jezero | 0.796 | 0.956 |  |
| rio_tinto | biosignatures | arcadia_planitia | 0.424 | None | bare_ground_min |
| rio_tinto | biosignatures | jezero | 0.424 | None | bare_ground_min |
| svalbard | biosignatures | arcadia_planitia | 0.543 | 0.462 |  |
| svalbard | biosignatures | jezero | 0.543 | 0.462 |  |
| tirez | biosignatures | arcadia_planitia | 0.537 | 0.442 |  |
| tirez | biosignatures | jezero | 0.537 | 0.442 |  |
| chill_ice_lava_tube | caves | arcadia_planitia | 0.978 | 0.975 |  |
| chill_ice_lava_tube | caves | jezero | 0.991 | 0.991 |  |
| chill_ice_lava_tube | caves | mons_mouton | 0.983 | 0.981 |  |
| chill_ice_lava_tube | caves | shackleton_ridge | 0.982 | 0.98 |  |
| craters_of_the_moon | caves | arcadia_planitia | 0.976 | 0.972 |  |
| craters_of_the_moon | caves | jezero | 0.987 | 0.986 |  |
| craters_of_the_moon | caves | mons_mouton | 0.978 | 0.976 |  |
| craters_of_the_moon | caves | shackleton_ridge | 0.976 | 0.973 |  |
| lanzarote_timanfaya | caves | arcadia_planitia | 0.994 | 0.996 |  |
| lanzarote_timanfaya | caves | jezero | 0.987 | 0.986 |  |
| lanzarote_timanfaya | caves | mons_mouton | 0.99 | 0.991 |  |
| lanzarote_timanfaya | caves | shackleton_ridge | 0.989 | 0.99 |  |
| askja | eva_geology | mons_mouton | 0.996 | 0.997 |  |
| askja | eva_geology | shackleton_ridge | 0.995 | 0.996 |  |
| craters_of_the_moon | eva_geology | mons_mouton | 0.989 | 0.99 |  |
| craters_of_the_moon | eva_geology | shackleton_ridge | 0.989 | 0.99 |  |
| etna | eva_geology | mons_mouton | 0.939 | 0.941 |  |
| etna | eva_geology | shackleton_ridge | 0.943 | 0.944 |  |
| gros_morne | eva_geology | mons_mouton | 0.403 | 0.418 |  |
| gros_morne | eva_geology | shackleton_ridge | 0.394 | 0.41 |  |
| haughton | eva_geology | mons_mouton | 0.985 | 0.985 |  |
| haughton | eva_geology | shackleton_ridge | 0.984 | 0.985 |  |
| hi_seas | eva_geology | mons_mouton | 0.986 | 0.987 |  |
| hi_seas | eva_geology | shackleton_ridge | 0.987 | 0.987 |  |
| kilauea | eva_geology | mons_mouton | 0.95 | 0.951 |  |
| kilauea | eva_geology | shackleton_ridge | 0.953 | 0.954 |  |
| kilbourne_hole | eva_geology | mons_mouton | 0.974 | 0.975 |  |
| kilbourne_hole | eva_geology | shackleton_ridge | 0.973 | 0.974 |  |
| lanzarote_timanfaya | eva_geology | mons_mouton | 0.985 | 0.986 |  |
| lanzarote_timanfaya | eva_geology | shackleton_ridge | 0.984 | 0.985 |  |
| lmas_reunion | eva_geology | mons_mouton | 0.962 | 0.964 |  |
| lmas_reunion | eva_geology | shackleton_ridge | 0.969 | 0.971 |  |
| meteor_crater | eva_geology | mons_mouton | 0.997 | 0.998 |  |
| meteor_crater | eva_geology | shackleton_ridge | 0.997 | 0.997 |  |
| mistastin | eva_geology | mons_mouton | 0.843 | 0.848 |  |
| mistastin | eva_geology | shackleton_ridge | 0.798 | 0.829 |  |
| ries | eva_geology | mons_mouton | 0.737 | 0.766 |  |
| ries | eva_geology | shackleton_ridge | 0.735 | 0.764 |  |
| rio_grande_del_norte | eva_geology | mons_mouton | 0.987 | 0.988 |  |
| rio_grande_del_norte | eva_geology | shackleton_ridge | 0.985 | 0.986 |  |
| sp_crater | eva_geology | mons_mouton | 0.99 | 0.99 |  |
| sp_crater | eva_geology | shackleton_ridge | 0.989 | 0.989 |  |
| sudbury | eva_geology | mons_mouton | 0.681 | 0.707 |  |
| sudbury | eva_geology | shackleton_ridge | 0.684 | 0.71 |  |
| svalbard | eva_geology | mons_mouton | 0.957 | 0.958 |  |
| svalbard | eva_geology | shackleton_ridge | 0.958 | 0.959 |  |
| sw_nevada_vf | eva_geology | mons_mouton | 0.976 | 0.977 |  |
| sw_nevada_vf | eva_geology | shackleton_ridge | 0.973 | 0.974 |  |
| teide | eva_geology | mons_mouton | 0.974 | 0.975 |  |
| teide | eva_geology | shackleton_ridge | 0.978 | 0.979 |  |
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
| concordia | low_sun_ops | mons_mouton | None | None | sun_window, not_ice_sheet |
| concordia | low_sun_ops | shackleton_ridge | None | None | sun_window, not_ice_sheet |
| haughton | low_sun_ops | mons_mouton | 0.466 | 0.936 |  |
| haughton | low_sun_ops | shackleton_ridge | 0.459 | 0.93 |  |
| mcmurdo_dry_valleys | low_sun_ops | mons_mouton | None | None | sun_window, not_ice_sheet |
| mcmurdo_dry_valleys | low_sun_ops | shackleton_ridge | None | None | sun_window, not_ice_sheet |
| svalbard | low_sun_ops | mons_mouton | 0.415 | None | sun_window |
| svalbard | low_sun_ops | shackleton_ridge | 0.434 | None | sun_window |
| askja | mobility | mons_mouton | 0.829 | 0.78 |  |
| askja | mobility | shackleton_ridge | 0.844 | 0.79 |  |
| atacama | mobility | arcadia_planitia | 0.17 | 0.171 |  |
| atacama | mobility | jezero | 0.775 | 0.749 |  |
| craters_of_the_moon | mobility | arcadia_planitia | 0.403 | 0.398 |  |
| craters_of_the_moon | mobility | jezero | 0.746 | 0.721 |  |
| craters_of_the_moon | mobility | mons_mouton | 0.615 | 0.509 |  |
| craters_of_the_moon | mobility | shackleton_ridge | 0.675 | 0.548 |  |
| death_valley | mobility | arcadia_planitia | 0.173 | 0.174 |  |
| death_valley | mobility | jezero | 0.736 | 0.71 |  |
| etna | mobility | arcadia_planitia | 0.276 | None | bare_ground_min |
| etna | mobility | jezero | 0.819 | None | bare_ground_min |
| etna | mobility | mons_mouton | 0.778 | None | bare_ground_min |
| etna | mobility | shackleton_ridge | 0.806 | None | bare_ground_min |
| haughton | mobility | arcadia_planitia | 0.922 | 0.866 |  |
| haughton | mobility | jezero | 0.595 | 0.564 |  |
| haughton | mobility | mons_mouton | 0.706 | 0.615 |  |
| haughton | mobility | shackleton_ridge | 0.757 | 0.67 |  |
| hi_seas | mobility | arcadia_planitia | 0.072 | 0.061 |  |
| hi_seas | mobility | jezero | 0.605 | 0.575 |  |
| hi_seas | mobility | mons_mouton | 0.886 | 0.849 |  |
| hi_seas | mobility | shackleton_ridge | 0.888 | 0.848 |  |
| kilauea | mobility | arcadia_planitia | 0.267 | 0.275 |  |
| kilauea | mobility | jezero | 0.896 | 0.859 |  |
| kilauea | mobility | mons_mouton | 0.753 | 0.678 |  |
| kilauea | mobility | shackleton_ridge | 0.767 | 0.685 |  |
| lmas_reunion | mobility | mons_mouton | 0.785 | None | bare_ground_min |
| lmas_reunion | mobility | shackleton_ridge | 0.841 | None | bare_ground_min |
| makgadikgadi | mobility | arcadia_planitia | 0.614 | 0.568 |  |
| makgadikgadi | mobility | jezero | 0.162 | 0.12 |  |
| mcmurdo_dry_valleys | mobility | arcadia_planitia | None | None | not_ice_sheet |
| mcmurdo_dry_valleys | mobility | jezero | None | None | not_ice_sheet |
| mcmurdo_dry_valleys | mobility | mons_mouton | None | None | not_ice_sheet |
| mcmurdo_dry_valleys | mobility | shackleton_ridge | None | None | not_ice_sheet |
| mdrs | mobility | arcadia_planitia | 0.262 | 0.27 |  |
| mdrs | mobility | jezero | 0.986 | 0.969 |  |
| qaidam | mobility | arcadia_planitia | 0.31 | 0.318 |  |
| qaidam | mobility | jezero | 0.998 | 0.996 |  |
| sp_crater | mobility | mons_mouton | 0.674 | 0.576 |  |
| sp_crater | mobility | shackleton_ridge | 0.673 | 0.545 |  |
| teide | mobility | arcadia_planitia | 0.257 | 0.265 |  |
| teide | mobility | jezero | 0.759 | 0.733 |  |
| teide | mobility | mons_mouton | 0.813 | 0.76 |  |
| teide | mobility | shackleton_ridge | 0.861 | 0.813 |  |

## Stability when the weights change

Every weight of a task was changed at random by up to +-25 % (30 draws). Share of the baseline top 5 % cells that stay in the top 5 % (1.0 = unchanged), and the share of those top cells under dense vegetation (NDVI over 0.4; should be near zero, though the bare-ground filter removes dense vegetation by construction).

| Task | stays in top 5 % | dense vegetation in top |
|---|---|---|
| biosignatures | 92% | 0% |
| caves | 96% | 37% |
| eva_geology | 90% | 15% |
| isru_ice | 99% | 0% |
| landing | 97% | 2% |
| low_sun_ops | 86% | 0% |
| mobility | 95% | 2% |

No spatial hold-out is run: no weight or threshold is fitted to the known sites, so every site is already unseen by the method.

## How to read this

- A cell is about 55 km across; a site is much smaller. A flat Martian plain (Arcadia) is rarely matched by a whole cell.
- Earth cannot reach lunar or Martian cold, vacuum or radiation. Cold, thermal range and low Sun are ranked in the useful direction only.
- Volcanic fields and impact structures enter as distance to the nearest listed point or rim; dryness is the annual precipitation of GPM IMERG.
