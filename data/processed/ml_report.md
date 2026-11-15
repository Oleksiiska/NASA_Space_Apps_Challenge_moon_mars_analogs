# Experimental ML layer: positive-unlabeled learning

The model learns which Earth cells look like the known analog sites. It can only repeat the pattern of places agencies already chose, including the reasons that have nothing to do with the Moon or Mars (access, tradition), so it is shown apart from the physics-based formula and never mixed into it.

- Features (40): elev_mean_m, relief_m, slope_mean_deg, slope_lt8, slope_lt15, rough_p50_m, slope_h0, slope_h1, slope_h2, slope_h3, slope_h4, slope_h5, slope_h6, slope_h7, slope_h8, lst_day_mean_k, lst_night_mean_k, lst_day_max_k, lst_night_min_k, lst_diurnal_k, ndvi_mean, ndvi_max, snow_cover_pct, snow_free_months, precip_log_mm, bare_px_frac, lowsun_best_h, lowsun_mean_h, ice_frac, min_calcite, min_chlorite, min_dolomite, min_goethite, min_gypsum, min_hematite, min_illite_muscovite, min_kaolinite, min_montmorillonite, min_vermiculite, min_quartz_feldspar.
- Left out on purpose: lat, lon, volc_dist_km, volc_basalt_dist_km, impact_dist_km, impact_diam_km, road_dist_km, volcano_dist_km, holocene_volcano_dist_km (location, and lists that contain the sites themselves).
- Bagged PU classifier: 40 bags, 20 unlabeled cells per positive in each bag, gradient-boosted trees of depth 3.
- Evaluation: each site and everything within 300 km of it is hidden from training; the site's percentile among all land cells is recorded. The formula column is the same site's mean percentile over its tasks and main targets, also among all land cells (scores only; a cell without a score counts as the lowest), so both columns use the same yardstick. validation.md ranks among scored cells only and is not comparable.

| World | held-out sites | ML median percentile | ML top 20 % | formula median | formula top 20 % |
|---|---|---|---|---|---|
| moon | 22 | 0.883 | 59% | 0.903 | 82% |
| mars | 24 | 0.851 | 58% | 0.609 | 15% |

## moon: held-out sites

| Sites in the cell | ML percentile | formula percentile |
|---|---|---|
| rio_grande_del_norte | 0.999 | 0.989 |
| teide | 0.999 | 0.929 |
| kilauea | 0.998 | 0.883 |
| lmas_reunion | 0.998 | 0.911 |
| etna | 0.996 | 0.9 |
| craters_of_the_moon | 0.959 | 0.905 |
| meteor_crater | 0.935 | 0.997 |
| sp_crater | 0.927 | 0.878 |
| kilbourne_hole | 0.918 | 0.976 |
| chill_ice_lava_tube | 0.909 | 0.982 |
| haughton | 0.887 | 0.811 |
| ries | 0.879 | 0.819 |
| mistastin | 0.842 | 0.873 |
| sw_nevada_vf | 0.77 | 0.977 |
| svalbard | 0.727 | 0.803 |
| askja | 0.719 | 0.94 |
| gros_morne | 0.719 | 0.567 |
| concordia | 0.616 | 0.691 |
| hi_seas | 0.568 | 0.951 |
| sudbury | 0.539 | 0.791 |
| mcmurdo_dry_valleys | 0.521 | 0.559 |
| lanzarote_timanfaya | 0.486 | 0.987 |

## mars: held-out sites

| Sites in the cell | ML percentile | formula percentile |
|---|---|---|
| teide | 0.999 | 0.645 |
| mdrs | 0.996 | 0.729 |
| etna | 0.995 | 0.674 |
| kilauea | 0.987 | 0.698 |
| meteor_crater | 0.979 | None |
| atacama | 0.971 | 0.611 |
| craters_of_the_moon | 0.964 | 0.837 |
| death_valley | 0.946 | 0.606 |
| qaidam | 0.891 | 0.774 |
| dallol | 0.89 | 0.598 |
| pilbara | 0.877 | 0.495 |
| chill_ice_lava_tube | 0.876 | 0.985 |
| haughton | 0.826 | 0.763 |
| svalbard | 0.806 | 0.586 |
| gros_morne | 0.797 | None |
| lanzarote_timanfaya | 0.752 | 0.991 |
| rio_tinto | 0.649 | 0.43 |
| kangerlussuaq | 0.537 | 0.536 |
| makgadikgadi | 0.524 | 0.518 |
| concordia | 0.485 | None |
| mcmurdo_dry_valleys | 0.428 | 0.549 |
| hi_seas | 0.374 | 0.523 |
| tirez | 0.359 | 0.541 |
| sudbury | 0.353 | None |

## How to read this

- Few positives (about 20 cells per world) and no true negatives: the scores are unstable and mostly say how much a cell resembles the landscapes and climates already in the list.
- A high ML score next to a low formula score means: looks like places people already use, but does not match the target for the task. The opposite means: physically similar, but unlike the usual choices; these are the candidates the challenge asks for.
