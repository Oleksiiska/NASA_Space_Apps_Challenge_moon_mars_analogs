# Experimental ML layer: positive-unlabeled learning

The model learns which Earth cells look like the known analog sites. It can only repeat the pattern of places agencies already chose, including the reasons that have nothing to do with the Moon or Mars (access, tradition), so it is shown apart from the physics-based formula and never mixed into it.

- Features (39): elev_mean_m, relief_m, slope_mean_deg, slope_lt8, slope_lt15, rough_p50_m, slope_h0, slope_h1, slope_h2, slope_h3, slope_h4, slope_h5, slope_h6, slope_h7, slope_h8, lst_day_mean_k, lst_night_mean_k, lst_day_max_k, lst_night_min_k, lst_diurnal_k, ndvi_mean, ndvi_max, snow_cover_pct, snow_free_months, precip_mm_yr, lowsun_best_h, lowsun_mean_h, ice_frac, min_calcite, min_chlorite, min_dolomite, min_goethite, min_gypsum, min_hematite, min_illite_muscovite, min_kaolinite, min_montmorillonite, min_vermiculite, min_quartz_feldspar.
- Left out on purpose: lat, lon, volc_dist_km, volc_basalt_dist_km, impact_dist_km, impact_diam_km, road_dist_km (location, and lists that contain the sites themselves).
- Bagged PU classifier: 40 bags, 20 unlabeled cells per positive in each bag, gradient-boosted trees of depth 3.
- Evaluation: each site and everything within 300 km of it is hidden from training; the site's percentile among all land cells is recorded. The formula column is the same site's mean percentile over its tasks and main targets, also among all land cells (scores only; a cell without a score counts as the lowest), so both columns use the same yardstick. validation.md ranks among scored cells only and is not comparable.

| World | held-out sites | ML median percentile | ML top 20 % | formula median | formula top 20 % |
|---|---|---|---|---|---|
| moon | 22 | 0.897 | 59% | 0.907 | 82% |
| mars | 24 | 0.849 | 58% | 0.647 | 20% |

## moon: held-out sites

| Sites in the cell | ML percentile | formula percentile |
|---|---|---|
| teide | 0.999 | 0.939 |
| etna | 0.998 | 0.909 |
| rio_grande_del_norte | 0.998 | 0.827 |
| lmas_reunion | 0.998 | 0.931 |
| kilauea | 0.997 | 0.906 |
| craters_of_the_moon | 0.947 | 0.891 |
| chill_ice_lava_tube | 0.942 | 0.987 |
| meteor_crater | 0.935 | 0.968 |
| sp_crater | 0.927 | 0.832 |
| kilbourne_hole | 0.921 | 0.55 |
| ries | 0.902 | 0.93 |
| haughton | 0.892 | 0.802 |
| mistastin | 0.828 | 0.953 |
| askja | 0.772 | 0.913 |
| sw_nevada_vf | 0.755 | 0.868 |
| gros_morne | 0.746 | 0.834 |
| svalbard | 0.74 | 0.796 |
| concordia | 0.625 | 0.691 |
| hi_seas | 0.582 | 0.959 |
| sudbury | 0.556 | 0.931 |
| lanzarote_timanfaya | 0.542 | 0.94 |
| mcmurdo_dry_valleys | 0.533 | 0.559 |

## mars: held-out sites

| Sites in the cell | ML percentile | formula percentile |
|---|---|---|
| teide | 0.998 | 0.645 |
| etna | 0.996 | 0.674 |
| mdrs | 0.994 | 0.729 |
| kilauea | 0.991 | 0.698 |
| meteor_crater | 0.981 | None |
| atacama | 0.97 | 0.74 |
| craters_of_the_moon | 0.968 | 0.844 |
| death_valley | 0.932 | 0.606 |
| qaidam | 0.903 | 0.837 |
| chill_ice_lava_tube | 0.891 | 0.963 |
| pilbara | 0.877 | 0.473 |
| haughton | 0.859 | 0.763 |
| gros_morne | 0.84 | None |
| dallol | 0.84 | 0.65 |
| svalbard | 0.797 | 0.585 |
| lanzarote_timanfaya | 0.753 | 0.996 |
| rio_tinto | 0.697 | 0.48 |
| kangerlussuaq | 0.593 | 0.58 |
| concordia | 0.483 | None |
| makgadikgadi | 0.474 | 0.55 |
| mcmurdo_dry_valleys | 0.422 | 0.543 |
| hi_seas | 0.407 | 0.523 |
| tirez | 0.381 | 0.606 |
| sudbury | 0.251 | None |

## How to read this

- Few positives (about 20 cells per world) and no true negatives: the scores are unstable and mostly say how much a cell resembles the landscapes and climates already in the list.
- A high ML score next to a low formula score means: looks like places people already use, but does not match the target for the task. The opposite means: physically similar, but unlike the usual choices; these are the candidates the challenge asks for.
