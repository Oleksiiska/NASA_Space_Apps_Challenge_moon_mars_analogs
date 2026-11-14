# Validation against known analog sites

Each site is a cell of the 0.25 degree grid (a coastal site whose own cell is mostly sea takes the nearest land cell next to it); its score is turned into a percentile among all ranked cells (1.0 = best cell on Earth for that task and target). A random site would get a median of 0.5 and land in the top 20 % one time in five. Known analogs were not used to set any weight or threshold.

- Scores only: 132 of 136 site-task-target pairs scored, median percentile 0.835, top 20 % in 55%, top 10 % in 39%.
- With the hard filters of each task: 80 pairs left, median 0.732, top 20 % in 42%. Filters remove sites whose 28 km cell is mostly vegetated although the site itself is bare (impact craters in forest, volcanic islands), and remote sites with no major road within 50 km for rover mobility.
- Independent part: the tasks caves, eva_geology use the volcano and impact lists, and those lists contain many of the analog sites themselves, so their high percentiles show that the layers work, not that the method finds analogs on its own. Without them: 82 pairs, median percentile 0.708, top 20 % in 29%, top 10 % in 10%.

| Task | pairs | median percentile | top 20 % | top 10 % |
|---|---|---|---|---|
| biosignatures | 20 | 0.585 | 20% | 10% |
| caves | 12 | 0.999 | 100% | 92% |
| eva_geology | 38 | 0.946 | 95% | 84% |
| isru_ice | 14 | 0.694 | 0% | 0% |
| low_sun_ops | 8 | 0.746 | 25% | 0% |
| mobility | 40 | 0.773 | 45% | 15% |

## Per site

| Site | Task | Target | Percentile | With filters | Failed filters |
|---|---|---|---|---|---|
| atacama | biosignatures | arcadia_planitia | 0.858 | 0.738 |  |
| atacama | biosignatures | jezero | 0.858 | 0.738 |  |
| dallol | biosignatures | arcadia_planitia | 0.696 | 0.442 |  |
| dallol | biosignatures | jezero | 0.696 | 0.442 |  |
| kangerlussuaq | biosignatures | arcadia_planitia | 0.534 | 0.177 |  |
| kangerlussuaq | biosignatures | jezero | 0.534 | 0.177 |  |
| makgadikgadi | biosignatures | arcadia_planitia | 0.557 | 0.211 |  |
| makgadikgadi | biosignatures | jezero | 0.557 | 0.211 |  |
| mcmurdo_dry_valleys | biosignatures | arcadia_planitia | 0.759 | 0.557 |  |
| mcmurdo_dry_valleys | biosignatures | jezero | 0.759 | 0.557 |  |
| pilbara | biosignatures | arcadia_planitia | 0.451 | 0.075 |  |
| pilbara | biosignatures | jezero | 0.451 | 0.075 |  |
| qaidam | biosignatures | arcadia_planitia | 0.922 | 0.856 |  |
| qaidam | biosignatures | jezero | 0.922 | 0.856 |  |
| rio_tinto | biosignatures | arcadia_planitia | 0.478 | None | bare_ground_min |
| rio_tinto | biosignatures | jezero | 0.478 | None | bare_ground_min |
| svalbard | biosignatures | arcadia_planitia | 0.515 | 0.151 |  |
| svalbard | biosignatures | jezero | 0.515 | 0.151 |  |
| tirez | biosignatures | arcadia_planitia | 0.612 | 0.297 |  |
| tirez | biosignatures | jezero | 0.612 | 0.297 |  |
| chill_ice_lava_tube | caves | arcadia_planitia | 0.907 | 0.907 |  |
| chill_ice_lava_tube | caves | jezero | 0.893 | 0.893 |  |
| chill_ice_lava_tube | caves | mons_mouton | 0.955 | 0.955 |  |
| chill_ice_lava_tube | caves | shackleton_ridge | 0.951 | 0.951 |  |
| craters_of_the_moon | caves | arcadia_planitia | 0.998 | 0.998 |  |
| craters_of_the_moon | caves | jezero | 0.999 | 0.999 |  |
| craters_of_the_moon | caves | mons_mouton | 0.999 | 0.999 |  |
| craters_of_the_moon | caves | shackleton_ridge | 0.999 | 0.999 |  |
| lanzarote_timanfaya | caves | arcadia_planitia | 0.999 | 0.999 |  |
| lanzarote_timanfaya | caves | jezero | 0.999 | 0.999 |  |
| lanzarote_timanfaya | caves | mons_mouton | 0.999 | 0.999 |  |
| lanzarote_timanfaya | caves | shackleton_ridge | 0.999 | 0.999 |  |
| askja | eva_geology | mons_mouton | 0.963 | 0.954 |  |
| askja | eva_geology | shackleton_ridge | 0.952 | 0.94 |  |
| craters_of_the_moon | eva_geology | mons_mouton | 0.977 | 0.973 |  |
| craters_of_the_moon | eva_geology | shackleton_ridge | 0.974 | 0.97 |  |
| etna | eva_geology | mons_mouton | 0.985 | None | bare_ground_min |
| etna | eva_geology | shackleton_ridge | 0.981 | None | bare_ground_min |
| gros_morne | eva_geology | mons_mouton | 0.85 | None | bare_ground_min |
| gros_morne | eva_geology | shackleton_ridge | 0.849 | None | bare_ground_min |
| haughton | eva_geology | mons_mouton | 0.975 | 0.971 |  |
| haughton | eva_geology | shackleton_ridge | 0.961 | 0.952 |  |
| hi_seas | eva_geology | mons_mouton | 0.989 | None | bare_ground_min |
| hi_seas | eva_geology | shackleton_ridge | 0.985 | None | bare_ground_min |
| kilauea | eva_geology | mons_mouton | 1.0 | None | bare_ground_min |
| kilauea | eva_geology | shackleton_ridge | 1.0 | None | bare_ground_min |
| kilbourne_hole | eva_geology | mons_mouton | 0.278 | 0.261 |  |
| kilbourne_hole | eva_geology | shackleton_ridge | 0.291 | 0.263 |  |
| lanzarote_timanfaya | eva_geology | mons_mouton | 0.958 | 0.946 |  |
| lanzarote_timanfaya | eva_geology | shackleton_ridge | 0.943 | 0.929 |  |
| lmas_reunion | eva_geology | mons_mouton | 1.0 | None | bare_ground_min |
| lmas_reunion | eva_geology | shackleton_ridge | 1.0 | None | bare_ground_min |
| meteor_crater | eva_geology | mons_mouton | 0.945 | 0.93 |  |
| meteor_crater | eva_geology | shackleton_ridge | 0.946 | 0.933 |  |
| mistastin | eva_geology | mons_mouton | 0.956 | None | bare_ground_min |
| mistastin | eva_geology | shackleton_ridge | 0.946 | None | bare_ground_min |
| ries | eva_geology | mons_mouton | 0.947 | None | bare_ground_min |
| ries | eva_geology | shackleton_ridge | 0.94 | None | bare_ground_min |
| rio_grande_del_norte | eva_geology | mons_mouton | 0.908 | None | bare_ground_min |
| rio_grande_del_norte | eva_geology | shackleton_ridge | 0.911 | None | bare_ground_min |
| sp_crater | eva_geology | mons_mouton | 0.922 | 0.9 |  |
| sp_crater | eva_geology | shackleton_ridge | 0.911 | 0.89 |  |
| sudbury | eva_geology | mons_mouton | 0.92 | None | bare_ground_min |
| sudbury | eva_geology | shackleton_ridge | 0.927 | None | bare_ground_min |
| svalbard | eva_geology | mons_mouton | 0.934 | 0.915 |  |
| svalbard | eva_geology | shackleton_ridge | 0.94 | 0.925 |  |
| sw_nevada_vf | eva_geology | mons_mouton | 0.812 | 0.783 |  |
| sw_nevada_vf | eva_geology | shackleton_ridge | 0.813 | 0.783 |  |
| teide | eva_geology | mons_mouton | 0.999 | None | bare_ground_min |
| teide | eva_geology | shackleton_ridge | 0.999 | None | bare_ground_min |
| haughton | isru_ice | arcadia_planitia | 0.696 | 0.411 |  |
| haughton | isru_ice | jezero | 0.716 | 0.451 |  |
| haughton | isru_ice | mons_mouton | 0.702 | 0.423 |  |
| haughton | isru_ice | shackleton_ridge | 0.691 | 0.403 |  |
| kangerlussuaq | isru_ice | arcadia_planitia | 0.61 | 0.245 |  |
| kangerlussuaq | isru_ice | jezero | 0.617 | 0.259 |  |
| mcmurdo_dry_valleys | isru_ice | arcadia_planitia | 0.718 | 0.454 |  |
| mcmurdo_dry_valleys | isru_ice | jezero | 0.739 | 0.495 |  |
| mcmurdo_dry_valleys | isru_ice | mons_mouton | 0.74 | 0.496 |  |
| mcmurdo_dry_valleys | isru_ice | shackleton_ridge | 0.74 | 0.496 |  |
| svalbard | isru_ice | arcadia_planitia | 0.613 | 0.25 |  |
| svalbard | isru_ice | jezero | 0.62 | 0.266 |  |
| svalbard | isru_ice | mons_mouton | 0.637 | 0.298 |  |
| svalbard | isru_ice | shackleton_ridge | 0.638 | 0.3 |  |
| concordia | low_sun_ops | mons_mouton | 0.664 | None | snow_free_window |
| concordia | low_sun_ops | shackleton_ridge | 0.662 | None | snow_free_window |
| haughton | low_sun_ops | mons_mouton | 0.75 | 0.939 |  |
| haughton | low_sun_ops | shackleton_ridge | 0.749 | 0.935 |  |
| mcmurdo_dry_valleys | low_sun_ops | mons_mouton | 0.802 | None | snow_free_window |
| mcmurdo_dry_valleys | low_sun_ops | shackleton_ridge | 0.802 | None | snow_free_window |
| svalbard | low_sun_ops | mons_mouton | 0.742 | None | snow_free_window |
| svalbard | low_sun_ops | shackleton_ridge | 0.743 | None | snow_free_window |
| askja | mobility | mons_mouton | 0.835 | 0.808 |  |
| askja | mobility | shackleton_ridge | 0.851 | 0.819 |  |
| atacama | mobility | arcadia_planitia | 0.188 | 0.152 |  |
| atacama | mobility | jezero | 0.842 | 0.798 |  |
| craters_of_the_moon | mobility | arcadia_planitia | 0.332 | 0.315 |  |
| craters_of_the_moon | mobility | jezero | 0.891 | 0.837 |  |
| craters_of_the_moon | mobility | mons_mouton | 0.719 | 0.661 |  |
| craters_of_the_moon | mobility | shackleton_ridge | 0.773 | 0.726 |  |
| death_valley | mobility | arcadia_planitia | 0.217 | 0.185 |  |
| death_valley | mobility | jezero | 0.866 | 0.818 |  |
| etna | mobility | arcadia_planitia | 0.143 | None | bare_ground_min |
| etna | mobility | jezero | 0.85 | None | bare_ground_min |
| etna | mobility | mons_mouton | 0.828 | None | bare_ground_min |
| etna | mobility | shackleton_ridge | 0.836 | None | bare_ground_min |
| haughton | mobility | arcadia_planitia | 0.409 | None | road_access |
| haughton | mobility | jezero | 0.921 | None | road_access |
| haughton | mobility | mons_mouton | 0.763 | None | road_access |
| haughton | mobility | shackleton_ridge | 0.773 | None | road_access |
| hi_seas | mobility | arcadia_planitia | 0.027 | None | bare_ground_min |
| hi_seas | mobility | jezero | 0.569 | None | bare_ground_min |
| hi_seas | mobility | mons_mouton | 0.852 | None | bare_ground_min |
| hi_seas | mobility | shackleton_ridge | 0.849 | None | bare_ground_min |
| kilauea | mobility | arcadia_planitia | 0.073 | None | bare_ground_min |
| kilauea | mobility | jezero | 0.577 | None | bare_ground_min |
| kilauea | mobility | mons_mouton | 0.896 | None | bare_ground_min |
| kilauea | mobility | shackleton_ridge | 0.899 | None | bare_ground_min |
| lmas_reunion | mobility | mons_mouton | 0.988 | None | bare_ground_min, road_access |
| lmas_reunion | mobility | shackleton_ridge | 0.978 | None | bare_ground_min, road_access |
| makgadikgadi | mobility | arcadia_planitia | 0.617 | 0.548 |  |
| makgadikgadi | mobility | jezero | 0.239 | 0.113 |  |
| mcmurdo_dry_valleys | mobility | arcadia_planitia | None | None | road_access |
| mcmurdo_dry_valleys | mobility | jezero | None | None | road_access |
| mcmurdo_dry_valleys | mobility | mons_mouton | None | None | road_access |
| mcmurdo_dry_valleys | mobility | shackleton_ridge | None | None | road_access |
| mdrs | mobility | arcadia_planitia | 0.345 | None | road_access |
| mdrs | mobility | jezero | 0.914 | None | road_access |
| qaidam | mobility | arcadia_planitia | 0.495 | 0.457 |  |
| qaidam | mobility | jezero | 0.784 | 0.746 |  |
| sp_crater | mobility | mons_mouton | 0.713 | 0.653 |  |
| sp_crater | mobility | shackleton_ridge | 0.699 | 0.599 |  |
| teide | mobility | arcadia_planitia | 0.145 | None | bare_ground_min |
| teide | mobility | jezero | 0.303 | None | bare_ground_min |
| teide | mobility | mons_mouton | 0.931 | None | bare_ground_min |
| teide | mobility | shackleton_ridge | 0.945 | None | bare_ground_min |

## Stability when the weights change

Every weight of a task was changed at random by up to +-25 % (30 draws). Share of the baseline top 5 % cells that stay in the top 5 % (1.0 = unchanged), and the share of those top cells under dense vegetation (NDVI over 0.4; should be near zero, though the bare-ground filter removes dense vegetation by construction).

| Task | stays in top 5 % | dense vegetation in top |
|---|---|---|
| biosignatures | 83% | 0% |
| caves | 92% | 13% |
| eva_geology | 95% | 0% |
| isru_ice | 100% | 0% |
| landing | 96% | 0% |
| low_sun_ops | 76% | 0% |
| mobility | 97% | 0% |

No spatial hold-out is run: no weight or threshold is fitted to the known sites, so every site is already unseen by the method.

## How to read this

- A cell is about 28 km across; a site is much smaller. A flat Martian plain (Arcadia) is rarely matched by a whole cell.
- Earth cannot reach lunar or Martian cold, vacuum or radiation. Cold, thermal range and low Sun are ranked in the useful direction only.
- Volcanic fields and impact structures enter as distance to the nearest listed point or rim; dryness comes from NASA POWER precipitation when its layer was built.
