# Data sources, attribution and licences

Every dataset of the project, the official challenge resource it comes from, and the
text to cite. The machine-readable version is `pipeline/config/sources.yaml`; file names
and sizes of the NASA PDS files were read from the PDS directory listings on 2026-11-13.

NASA does not endorse any non-U.S. Government entity and is not responsible for
information on non-U.S. Government websites. For ESA, CSA, JAXA and other non-U.S.
Government sources the data-use terms of that source apply.

## How the official challenge resources are used

| Official resource | What the project takes from it | Role |
| --- | --- | --- |
| NASA Earthdata Search | SRTMGL30 (terrain), MOD11C3 (surface temperature), MOD13C2 (NDVI), MOD10CM (snow), EMIT L3ASA (minerals); MCD12C1 (land cover) is downloaded but not used | Core: features of every Earth cell |
| NASA Worldview | GIBS imagery layers: true colour, temperature, snow | Map background and visual check of the top candidates; nothing is downloaded into the pipeline |
| NASA Planetary Data System (PDS) | Mars: MOLA MEGDR topography, Odyssey GRS water map | Core: fingerprints of the Martian targets |
| NASA Lunar Reconnaissance Orbiter (PDS Geosciences) | LOLA gridded data: south polar elevation, slope and roughness maps | Core: terrain of the lunar targets |
| NASA LRO Diviner Lunar Data | Polar Resource Product: temperatures and depth of stable ice | Core: the "cold" and "ice" criteria |
| ESA Copernicus Data Space Ecosystem | Copernicus DEM GLO-90 for high latitudes; Sentinel-1 and Sentinel-2 for the top candidates | Core for polar analogs, detail otherwise |
| CSA RADARSAT-1, RCM, SAR Python Tutorial | Radar images of Arctic analogs; the tutorial as a code template | Detail and optional; not part of the downloads yet |
| ESA Open Science Catalog | Search for ESA products on permafrost, snow, surface temperature | Optional |
| JAXA G-Portal | GCOM-C/SGLI, GCOM-W/AMSR2, GSMaP precipitation | Optional: independent check of temperature, snow and aridity |

## Datasets in the manifest

Access: `open` needs no account; `earthdata_login` needs the free NASA Earthdata Login.


### Moon

**LRO LOLA GDR, south polar elevation (240 m, 80 m, 20 m)** (`moon_lola_polar_dem`)

- Official resource: NASA Lunar Reconnaissance Orbiter (PDS Geosciences). Agency: NASA. Access: `open`.
- Source: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/
- Size: 3 file(s), 259.6 MB. Saved to `data/raw/moon/lola`. Used for: terrain.
- Citation: Smith, D. E., et al. (2017). Summary of the results from the Lunar Orbiter Laser Altimeter after seven years in lunar orbit. Icarus, 283, 70-91. Data set LRO-L-LOLA-4-GDR-V1.0, NASA Planetary Data System.
- Licence: NASA PDS, public.

**LRO LOLA GDR, south polar slope and roughness maps** (`moon_lola_polar_slope_roughness`)

- Official resource: NASA Lunar Reconnaissance Orbiter (PDS Geosciences). Agency: NASA. Access: `open`.
- Source: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/
- Size: 3 file(s), 173.2 MB. Saved to `data/raw/moon/lola`. Used for: terrain_crosscheck.
- Citation: Same as moon_lola_polar_dem.
- Licence: NASA PDS, public.

**LRO Diviner Polar Resource Product, south pole** (`moon_diviner_prp`)

- Official resource: NASA LRO Diviner Lunar Data (PDS Geosciences). Agency: NASA. Access: `open`.
- Source: https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/
- Size: 1 file(s), 604.8 MB. Saved to `data/raw/moon/diviner`. Used for: thermal, ice.
- Citation: Paige, D. A., et al. (2010). Diviner Lunar Radiometer observations of cold traps in the Moon's south polar region. Science, 330, 479-482. Diviner derived products, NASA Planetary Data System.
- Licence: NASA PDS, public.


### Mars

**MGS MOLA MEGDR topography, 64 pixels per degree (926 m)** (`mars_mola_megdr_64`)

- Official resource: NASA Planetary Data System (PDS). Agency: NASA. Access: `open`.
- Source: https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg064/
- Size: 4 file(s), 530.8 MB. Saved to `data/raw/mars/mola`. Used for: terrain.
- Citation: Smith, D., Neumann, G., Arvidson, R. E., Guinness, E. A., and Slavney, S. (2003). Mars Global Surveyor Laser Altimeter Mission Experiment Gridded Data Record, MGS-M-MOLA-5-MEGDR-L3-V1.0, NASA Planetary Data System.
- Licence: NASA PDS, public.

**MGS MOLA MEGDR topography, 16 pixels per degree (3.7 km), global quick-look** (`mars_mola_megdr_16`)

- Official resource: NASA Planetary Data System (PDS). Agency: NASA. Access: `open`.
- Source: https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg016/
- Size: 1 file(s), 33.2 MB. Saved to `data/raw/mars/mola`. Used for: terrain_quicklook.
- Citation: Same as mars_mola_megdr_64.
- Licence: NASA PDS, public.

**Mars Odyssey GRS element concentration map, H2O (5 degree bins, smoothed)** (`mars_grs_h2o`)

- Official resource: NASA Planetary Data System (PDS). Agency: NASA. Access: `open`.
- Source: https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/
- Size: 1 file(s), 0.2 MB. Saved to `data/raw/mars/grs`. Used for: ice.
- Citation: Boynton, W. V., et al. (2007). Concentration of H, Si, Cl, K, Fe, and Th in the low- and mid-latitude regions of Mars. J. Geophys. Res., 112, E12S99. Data set ODY-M-GRS-5-ELEMENTS-V1.0, NASA Planetary Data System.
- Licence: NASA PDS, public.


### Earth

**Natural Earth 1:50m land and glaciated areas (land mask of the grid)** (`earth_naturalearth_land`)

- Official resource: none (auxiliary, public domain). Agency: Natural Earth. Access: `open`.
- Source: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/
- Size: 2 file(s), 2.1 MB. Saved to `data/raw/earth/naturalearth`. Used for: land_mask.
- Citation: Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.
- Licence: Public domain.

**Smithsonian Global Volcanism Program, Volcanoes of the World (Holocene and Pleistocene volcanoes)** (`earth_gvp_volcanoes`)

- Official resource: none (auxiliary context layer). Agency: Smithsonian Institution. Access: `open`.
- Source: Earthdata short name `None`, version None
- Size: 2 file(s), 0.0 MB. Saved to `data/raw/earth/context`. Used for: volcanic.
- Citation: Global Volcanism Program (2024). Volcanoes of the World (v. 5.2.x). Smithsonian Institution. doi:10.5479/si.GVP.VOTW5-2024.5.2
- Licence: Smithsonian terms of use; cite the Global Volcanism Program.

**Confirmed impact structures on Earth (Wikipedia list based on the Earth Impact Database, and Wikidata)** (`earth_impact_structures`)

- Official resource: none (auxiliary context layer). Agency: Wikipedia / Wikidata. Access: `open`.
- Source: Earthdata short name `None`, version None
- Size: 2 file(s), 0.0 MB. Saved to `data/raw/earth/context`. Used for: impact.
- Citation: Wikipedia contributors, "List of impact structures on Earth" (CC BY-SA 4.0), compiled from the Earth Impact Database (Planetary and Space Science Centre, University of New Brunswick); Wikidata (CC0), items that are instances of "impact crater" (Q55818) with coordinates on Earth.
- Licence: CC BY-SA 4.0 (Wikipedia), CC0 (Wikidata).

**Natural Earth 1:10M roads (logistics; distance to a major road)** (`earth_naturalearth_roads`)

- Official resource: none (auxiliary, public domain). Agency: Natural Earth. Access: `open`.
- Source: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/
- Size: 1 file(s), 50.5 MB. Saved to `data/raw/earth/naturalearth`. Used for: road_access.
- Citation: Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.
- Licence: Public domain.

**Natural Earth 1:10M populated places (city search of the web page)** (`earth_naturalearth_places`)

- Official resource: none (auxiliary, public domain). Agency: Natural Earth. Access: `open`.
- Source: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/
- Size: 1 file(s), 19.4 MB. Saved to `data/raw/earth/naturalearth`. Used for: city_search.
- Citation: Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.
- Licence: Public domain.

**NASA SRTM Global 30 arc second (about 926 m), 90N to 60S** (`earth_srtmgl30`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `SRTMGL30`, version 002
- Size: chosen at download time. Saved to `data/raw/earth/srtmgl30`. Used for: terrain.
- Citation: NASA JPL (2013). NASA Shuttle Radar Topography Mission Global 30 arc second. NASA EOSDIS Land Processes DAAC. doi:10.5067/MEaSUREs/SRTM/SRTMGL30.002
- Licence: NASA EOSDIS open data policy.

**MODIS/Terra Land Surface Temperature, monthly, 0.05 degree (MOD11C3)** (`earth_mod11c3`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `MOD11C3`, version 061
- Size: chosen at download time. Saved to `data/raw/earth/modis_lst`. Used for: thermal.
- Citation: Wan, Z., Hook, S., and Hulley, G. (2021). MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG V061. NASA EOSDIS LP DAAC. doi:10.5067/MODIS/MOD11C3.061
- Licence: NASA EOSDIS open data policy.

**MODIS/Terra Vegetation Indices (NDVI), monthly, 0.05 degree (MOD13C2)** (`earth_mod13c2`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `MOD13C2`, version 061
- Size: chosen at download time. Saved to `data/raw/earth/modis_ndvi`. Used for: bare_ground.
- Citation: Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG V061. NASA EOSDIS LP DAAC. doi:10.5067/MODIS/MOD13C2.061
- Licence: NASA EOSDIS open data policy.

**MODIS/Terra Snow Cover, monthly, 0.05 degree (MOD10CM)** (`earth_mod10cm`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `MOD10CM`, version 61
- Size: chosen at download time. Saved to `data/raw/earth/modis_snow`. Used for: snow_free_months.
- Citation: Hall, D. K. and Riggs, G. A. (2021). MODIS/Terra Snow Cover Monthly L3 Global 0.05Deg CMG, Version 61. NASA NSIDC DAAC. doi:10.5067/MODIS/MOD10CM.061
- Licence: NASA EOSDIS open data policy.

**MODIS Land Cover Type, yearly, 0.05 degree (MCD12C1)** (`earth_mcd12c1`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `MCD12C1`, version 061
- Size: chosen at download time. Saved to `data/raw/earth/modis_lc`. Used for: land_cover_mask.
- Citation: Friedl, M. and Sulla-Menashe, D. (2022). MODIS/Terra+Aqua Land Cover Type Yearly L3 Global 0.05Deg CMG V061. NASA EOSDIS LP DAAC. doi:10.5067/MODIS/MCD12C1.061
- Licence: NASA EOSDIS open data policy.

**GPM IMERG Final Precipitation, monthly, 0.1 degree (GPM_3IMERGM)** (`earth_imerg_monthly`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `GPM_3IMERGM`, version 07
- Size: chosen at download time. Saved to `data/raw/earth/imerg`. Used for: dryness.
- Citation: Huffman, G.J., E.F. Stocker, D.T. Bolvin, E.J. Nelkin, J. Tan (2023). GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07. Goddard Earth Sciences Data and Information Services Center (GES DISC). doi:10.5067/GPM/IMERG/3B-MONTH/07
- Licence: NASA EOSDIS open data policy.

**EMIT L3 Aggregated Mineral Spectral Abundance, 0.5 degree, 52N to 52S** (`earth_emit_l3asa`)

- Official resource: NASA Earthdata Search. Agency: NASA. Access: `earthdata_login`.
- Source: Earthdata short name `EMITL3ASA`, version 002
- Size: chosen at download time. Saved to `data/raw/earth/emit`. Used for: composition.
- Citation: NASA EMIT L3 Aggregated Mineral Spectral Abundance and Uncertainty 0.5 Deg (EMITL3ASA). NASA EOSDIS LP DAAC. Take the DOI and citation text from the product page.
- Licence: NASA EOSDIS open data policy.

**NASA POWER climatology at points (air temperature, precipitation, humidity, sun)** (`earth_power_climatology`)

- Official resource: none (NASA, outside the challenge list). Agency: NASA. Access: `open`.
- Source: https://power.larc.nasa.gov/api/temporal/climatology/point
- Size: chosen at download time. Saved to `data/raw/earth/power`. Used for: climate_of_sites.
- Citation: NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science/Applied Science Program.
- Licence: NASA open data.

**NASA POWER precipitation climatology on the whole land grid (dryness criterion)** (`earth_power_precip_grid`)

- Official resource: none (NASA, outside the challenge list). Agency: NASA. Access: `open`.
- Source: https://power.larc.nasa.gov/api/temporal/climatology/regional
- Size: chosen at download time. Saved to `data/raw/earth/power_grid`. Used for: dryness.
- Citation: NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science/Applied Science Program. Precipitation from MERRA-2 (corrected), long-term climatology.
- Licence: NASA open data.

**Holocene volcanoes of the world (location and type), Smithsonian Global Volcanism Program** (`earth_volcanoes`)

- Official resource: none (geological context, outside the challenge list). Agency: Smithsonian Institution. Access: `open`.
- Source: https://raw.githubusercontent.com/plotly/datasets/master/
- Size: 1 file(s), 0.1 MB. Saved to `data/raw/earth/context`. Used for: volcanic.
- Citation: Global Volcanism Program, Smithsonian Institution. Volcanoes of the World, list of Holocene volcanoes (an earlier version of the database, 1,571 volcanoes, as copied in the plotly/datasets repository on GitHub). Current version: https://volcano.si.edu
- Licence: Free use with citation of the Global Volcanism Program (check the terms on volcano.si.edu).

**Confirmed impact structures (Earth Impact Database, 189 structures)** (`earth_impacts`)

- Official resource: none (geological context, outside the challenge list). Agency: Planetary and Space Science Centre, University of New Brunswick. Access: `open`.
- Source: https://raw.githubusercontent.com/cjwinchester/earth-impact-data/main/
- Size: 1 file(s), 0.0 MB. Saved to `data/raw/earth/context`. Used for: impact.
- Citation: Earth Impact Database, Planetary and Space Science Centre, University of New Brunswick (http://www.passc.net/EarthImpactDatabase), table as compiled in the cjwinchester/earth-impact-data repository on GitHub.
- Licence: Terms of the Earth Impact Database apply; cite PASSC.

**Copernicus DEM GLO-90 tiles (terrain of Antarctic sites and detail views)** (`earth_copdem_glo90`)

- Official resource: Copernicus Data Space Ecosystem (ESA). Agency: ESA / Copernicus. Access: `open`.
- Source: https://copernicus-dem-90m.s3.amazonaws.com/
- Size: chosen at download time. Saved to `data/raw/earth/copdem`. Used for: terrain_polar.
- Citation: Copernicus DEM GLO-90. Produced using Copernicus WorldDEM-90 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. Check the licence text on the Copernicus page.
- Licence: Copernicus DEM licence (free for the general public).


## Reference tables written for the project

| File | Where the content comes from |
| --- | --- |
| `data/reference/known_analogs.csv` | Site list and coordinates: the Wikipedia articles "Terrestrial analogue site" and "List of impact structures on Earth" and the articles of single sites (text under CC BY-SA 4.0), Cavalazzi et al. 2019 (Astrobiology 19:553) for Dallol. Uses: USGS, NASA NTRS, Europlanet, CORDIS and National Park Service pages. Each row names its own sources in `coord_source` and `use_source`. |
| `pipeline/config/targets.yaml`, `data/reference/targets.geojson` | Coordinates from the USGS Gazetteer of Planetary Nomenclature, the LROC site, the PDS Orbital Data Explorer landing-site table and Wikipedia; the source of each target is in its `source` field. |
| `data/reference/environment_gaps.json` | NASA Planetary Fact Sheets (NSSDCA); Hassler et al. 2014 (Science 343, 1244797) for Mars radiation; Zhang et al. 2020 (Science Advances 6, eaaz1334) for lunar radiation; UNSCEAR 2008 for the Earth background. |
| `data/processed/grid.*`, `lowsun_by_latitude.csv` | Land and ice masks from Natural Earth; the low-Sun hours are computed from solar geometry in `features/sun.py` and were checked against the pvlib library. |

### Columns of known_analogs.csv

| Column | Meaning |
| --- | --- |
| `id`, `name`, `name_uk`, `country` | Identifier and names |
| `lat`, `lon` | Degrees, north and east positive |
| `world` | Which world the site stands in for: `moon`, `mars` or `both` |
| `tasks` | Test tasks the site is relevant to, ids from `config/tasks.yaml`, separated by `;` |
| `kind` | Type of site, separated by `;` (volcanic, impact, polar_desert, evaporite, habitat and so on) |
| `validate` | `yes` when the site is a natural landscape that the ranking should be able to find again; `no` for habitats, underwater sites and field schools |
| `used_by` | Who uses the site and for what |
| `coord_quality` | `verified`: the coordinates were read from `coord_source`; `approx`: written from memory, to be refined |
| `coord_source`, `use_source` | Pages the coordinates and the use were taken from |
| `use_checked` | `no` when the page in `use_source` was found but not read yet; `used_by` then ends with "(to confirm)" |
| `notes` | Scale of the site, caveats |

## Known limits of the data

- The Natural Earth ice mask (1:50 million) is too coarse for small ice-free areas: the cell of the McMurdo Dry Valleys comes out as fully ice-covered. Use the MODIS snow and land-cover products for such places.
- SRTMGL30 covers 90 N to 60 S. North of 60 N, where real SRTM ends, the values come from a coarser source (GTOPO30, to be confirmed), so Arctic terrain is smoother than elsewhere. Antarctica (south of 60 S) has no terrain: use Copernicus DEM for single sites such as the McMurdo Dry Valleys.
- EMIT L3ASA: the file covers 55 N to 54.5 S and only bare, dust-source surfaces; elsewhere the mineral features are empty. Its cell centres sit a quarter cell away from the project grid and are averaged 2 x 2.
- The volcano list is an earlier version of the Global Volcanism Program database (1,571 volcanoes, 1,420 on land). A volcanic field is one point, so distance to it is only a proxy for volcanic terrain nearby.
- The impact table lists 189 confirmed structures; the distance is measured to a circular rim of the listed diameter.
- NASA POWER precipitation comes from the MERRA-2 reanalysis on a 0.5 x 0.625 degree grid and is least reliable in mountains and over small deserts.
- The GRS water map has 5 degree bins, about 300 km on Mars: it describes a region, not a landing site.
- The LOLA files of the manifest cover 75 S to the pole, which is enough for the lunar targets of `targets.yaml` and nothing else.
- Sun elevations assume a flat horizon. Real horizons at the lunar pole and in mountains change the lighting a lot.

## Short form for the submission

Data: NASA PDS (LRO LOLA, LRO Diviner, MGS MOLA, Mars Odyssey GRS); NASA EOSDIS LP DAAC
and NSIDC DAAC through Earthdata (SRTMGL30, MOD11C3, MOD13C2, MOD10CM, EMIT L3ASA); NASA
POWER (precipitation, if the dryness layer was built); Smithsonian Global Volcanism
Program; Earth Impact Database (PASSC, University of New Brunswick); Natural Earth.
