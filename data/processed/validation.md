# Validation against known analog sites

Each site is a cell of the 0.5 degree grid; its score is turned into a percentile among all ranked cells (1.0 = best cell on Earth for that task and target). A random site would get a median of 0.5 and land in the top 20 % one time in five. Known analogs were not used to set any weight or threshold.

- Scores only: 124 of 136 site-task-target pairs scored, median percentile 0.782, top 20 % in 48%, top 10 % in 33%.
- With the hard filters of each task: 80 pairs left, median 0.726, top 20 % in 42%. Filters remove sites whose 55 km cell is mostly vegetated although the site itself is bare (impact craters in forest, volcanic islands).
- Independent part: the tasks caves, eva_geology use the volcano and impact lists, and those lists contain many of the analog sites themselves, so their high percentiles show that the layers work, not that the method finds analogs on its own. Without them: 74 pairs, median percentile 0.704, top 20 % in 20%, top 10 % in 4%.

| Task | pairs | median percentile | top 20 % | top 10 % |
|---|---|---|---|---|
| biosignatures | 12 | 0.527 | 17% | 0% |
| caves | 12 | 0.994 | 100% | 100% |
| eva_geology | 38 | 0.923 | 84% | 68% |
| isru_ice | 14 | 0.694 | 0% | 0% |
| low_sun_ops | 8 | 0.758 | 0% | 0% |
| mobility | 40 | 0.75 | 32% | 8% |

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
| mcmurdo_dry_valleys | biosignatures | arcadia_planitia | None | None |  |
| mcmurdo_dry_valleys | biosignatures | jezero | None | None |  |
| pilbara | biosignatures | arcadia_planitia | None | None |  |
| pilbara | biosignatures | jezero | None | None |  |
| qaidam | biosignatures | arcadia_planitia | 0.878 | 0.829 |  |
| qaidam | biosignatures | jezero | 0.878 | 0.829 |  |
| rio_tinto | biosignatures | arcadia_planitia | 0.23 | None | bare_ground_min |
| rio_tinto | biosignatures | jezero | 0.23 | None | bare_ground_min |
| svalbard | biosignatures | arcadia_planitia | None | None |  |
| svalbard | biosignatures | jezero | None | None |  |
| tirez | biosignatures | arcadia_planitia | 0.574 | 0.482 |  |
| tirez | biosignatures | jezero | 0.574 | 0.482 |  |
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
| askja | eva_geology | mons_mouton | 0.929 | 0.913 |  |
| askja | eva_geology | shackleton_ridge | 0.919 | 0.902 |  |
| craters_of_the_moon | eva_geology | mons_mouton | 0.905 | 0.883 |  |
| craters_of_the_moon | eva_geology | shackleton_ridge | 0.914 | 0.896 |  |
| etna | eva_geology | mons_mouton | 0.956 | None | bare_ground_min |
| etna | eva_geology | shackleton_ridge | 0.956 | None | bare_ground_min |
| gros_morne | eva_geology | mons_mouton | 0.772 | None | bare_ground_min |
| gros_morne | eva_geology | shackleton_ridge | 0.769 | None | bare_ground_min |
| haughton | eva_geology | mons_mouton | 0.944 | 0.932 |  |
| haughton | eva_geology | shackleton_ridge | 0.943 | 0.932 |  |
| hi_seas | eva_geology | mons_mouton | 0.999 | None | bare_ground_min |
| hi_seas | eva_geology | shackleton_ridge | 0.999 | None | bare_ground_min |
| kilauea | eva_geology | mons_mouton | 0.98 | None | bare_ground_min |
| kilauea | eva_geology | shackleton_ridge | 0.977 | None | bare_ground_min |
| kilbourne_hole | eva_geology | mons_mouton | 0.368 | 0.338 |  |
| kilbourne_hole | eva_geology | shackleton_ridge | 0.384 | 0.343 |  |
| lanzarote_timanfaya | eva_geology | mons_mouton | 0.833 | 0.802 |  |
| lanzarote_timanfaya | eva_geology | shackleton_ridge | 0.847 | 0.819 |  |
| lmas_reunion | eva_geology | mons_mouton | 0.996 | None | bare_ground_min |
| lmas_reunion | eva_geology | shackleton_ridge | 0.997 | None | bare_ground_min |
| meteor_crater | eva_geology | mons_mouton | 0.958 | 0.95 |  |
| meteor_crater | eva_geology | shackleton_ridge | 0.954 | 0.945 |  |
| mistastin | eva_geology | mons_mouton | 0.943 | None | bare_ground_min |
| mistastin | eva_geology | shackleton_ridge | 0.927 | None | bare_ground_min |
| ries | eva_geology | mons_mouton | 0.902 | None | bare_ground_min |
| ries | eva_geology | shackleton_ridge | 0.904 | None | bare_ground_min |
| rio_grande_del_norte | eva_geology | mons_mouton | 0.758 | 0.729 |  |
| rio_grande_del_norte | eva_geology | shackleton_ridge | 0.762 | 0.729 |  |
| sp_crater | eva_geology | mons_mouton | 0.857 | 0.828 |  |
| sp_crater | eva_geology | shackleton_ridge | 0.862 | 0.836 |  |
| sudbury | eva_geology | mons_mouton | 0.902 | None | bare_ground_min |
| sudbury | eva_geology | shackleton_ridge | 0.908 | None | bare_ground_min |
| svalbard | eva_geology | mons_mouton | 0.946 | 0.935 |  |
| svalbard | eva_geology | shackleton_ridge | 0.949 | 0.939 |  |
| sw_nevada_vf | eva_geology | mons_mouton | 0.816 | 0.784 |  |
| sw_nevada_vf | eva_geology | shackleton_ridge | 0.819 | 0.788 |  |
| teide | eva_geology | mons_mouton | 0.992 | None | bare_ground_min |
| teide | eva_geology | shackleton_ridge | 0.993 | None | bare_ground_min |
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
| concordia | low_sun_ops | mons_mouton | 0.691 | None | snow_free_window |
| concordia | low_sun_ops | shackleton_ridge | 0.688 | None | snow_free_window |
| haughton | low_sun_ops | mons_mouton | 0.75 | 0.929 |  |
| haughton | low_sun_ops | shackleton_ridge | 0.748 | 0.922 |  |
| mcmurdo_dry_valleys | low_sun_ops | mons_mouton | 0.797 | None | snow_free_window |
| mcmurdo_dry_valleys | low_sun_ops | shackleton_ridge | 0.795 | None | snow_free_window |
| svalbard | low_sun_ops | mons_mouton | 0.765 | None | snow_free_window |
| svalbard | low_sun_ops | shackleton_ridge | 0.767 | None | snow_free_window |
| askja | mobility | mons_mouton | 0.829 | 0.802 |  |
| askja | mobility | shackleton_ridge | 0.844 | 0.808 |  |
| atacama | mobility | arcadia_planitia | 0.17 | 0.13 |  |
| atacama | mobility | jezero | 0.775 | 0.751 |  |
| craters_of_the_moon | mobility | arcadia_planitia | 0.403 | 0.347 |  |
| craters_of_the_moon | mobility | jezero | 0.746 | 0.724 |  |
| craters_of_the_moon | mobility | mons_mouton | 0.615 | 0.529 |  |
| craters_of_the_moon | mobility | shackleton_ridge | 0.675 | 0.554 |  |
| death_valley | mobility | arcadia_planitia | 0.173 | 0.133 |  |
| death_valley | mobility | jezero | 0.736 | 0.713 |  |
| etna | mobility | arcadia_planitia | 0.276 | None | bare_ground_min |
| etna | mobility | jezero | 0.819 | None | bare_ground_min |
| etna | mobility | mons_mouton | 0.778 | None | bare_ground_min |
| etna | mobility | shackleton_ridge | 0.806 | None | bare_ground_min |
| haughton | mobility | arcadia_planitia | 0.922 | 0.789 |  |
| haughton | mobility | jezero | 0.595 | 0.565 |  |
| haughton | mobility | mons_mouton | 0.706 | 0.635 |  |
| haughton | mobility | shackleton_ridge | 0.757 | 0.684 |  |
| hi_seas | mobility | arcadia_planitia | 0.072 | None | bare_ground_min |
| hi_seas | mobility | jezero | 0.605 | None | bare_ground_min |
| hi_seas | mobility | mons_mouton | 0.886 | None | bare_ground_min |
| hi_seas | mobility | shackleton_ridge | 0.888 | None | bare_ground_min |
| kilauea | mobility | arcadia_planitia | 0.267 | None | bare_ground_min |
| kilauea | mobility | jezero | 0.896 | None | bare_ground_min |
| kilauea | mobility | mons_mouton | 0.753 | None | bare_ground_min |
| kilauea | mobility | shackleton_ridge | 0.767 | None | bare_ground_min |
| lmas_reunion | mobility | mons_mouton | 0.785 | None | bare_ground_min |
| lmas_reunion | mobility | shackleton_ridge | 0.841 | None | bare_ground_min |
| makgadikgadi | mobility | arcadia_planitia | 0.614 | 0.508 |  |
| makgadikgadi | mobility | jezero | 0.162 | 0.072 |  |
| mcmurdo_dry_valleys | mobility | arcadia_planitia | None | None |  |
| mcmurdo_dry_valleys | mobility | jezero | None | None |  |
| mcmurdo_dry_valleys | mobility | mons_mouton | None | None |  |
| mcmurdo_dry_valleys | mobility | shackleton_ridge | None | None |  |
| mdrs | mobility | arcadia_planitia | 0.262 | 0.224 |  |
| mdrs | mobility | jezero | 0.986 | 0.961 |  |
| qaidam | mobility | arcadia_planitia | 0.31 | 0.269 |  |
| qaidam | mobility | jezero | 0.998 | 0.994 |  |
| sp_crater | mobility | mons_mouton | 0.674 | 0.597 |  |
| sp_crater | mobility | shackleton_ridge | 0.673 | 0.55 |  |
| teide | mobility | arcadia_planitia | 0.257 | None | bare_ground_min |
| teide | mobility | jezero | 0.759 | None | bare_ground_min |
| teide | mobility | mons_mouton | 0.813 | None | bare_ground_min |
| teide | mobility | shackleton_ridge | 0.861 | None | bare_ground_min |

## Stability when the weights change

Every weight of a task was changed at random by up to +-25 % (30 draws). Share of the baseline top 5 % cells that stay in the top 5 % (1.0 = unchanged), and the share of those top cells under dense vegetation (NDVI over 0.4; should be near zero, though the bare-ground filter removes dense vegetation by construction).

| Task | stays in top 5 % | dense vegetation in top |
|---|---|---|
| biosignatures | 92% | 0% |
| caves | 92% | 13% |
| eva_geology | 95% | 0% |
| isru_ice | 99% | 0% |
| landing | 96% | 0% |
| low_sun_ops | 75% | 0% |
| mobility | 95% | 0% |

No spatial hold-out is run: no weight or threshold is fitted to the known sites, so every site is already unseen by the method.

## How to read this

- A cell is about 55 km across; a site is much smaller. A flat Martian plain (Arcadia) is rarely matched by a whole cell.
- Earth cannot reach lunar or Martian cold, vacuum or radiation. Cold, thermal range and low Sun are ranked in the useful direction only.
- Volcanic fields and impact structures enter as distance to the nearest listed point or rim; dryness comes from NASA POWER precipitation when its layer was built.
