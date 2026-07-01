# My Farm Advisor – Field-Level EDA Subskill

**Skill path:** `my-farm-advisor/eda/field-level-eda`  
**Type:** Document-routed EDA subskill (static Python outputs)  
**Assignment context:** Assignment 2, Agricultural Data Systems, Instructor: Clayton Young

---

## Overview

This subskill produces a repeatable set of static Python EDA outputs for a
three-grower, field-level dataset covering Illinois, Iowa, and Nebraska.
It compares field boundaries, weather, and CDL/cropland data layer patterns
at three analysis levels:

| Level | Example analyses |
|---|---|
| Within a field | Annual GDD trend across 2020–2024 for the same field |
| Across fields within a grower | Field acreage distribution; crop rotation pattern by field |
| Across growers | IL vs. IA vs. NE precipitation, GDD, and CDL composition |

Soil analysis is **not** included in this subskill.

---

## Dataset

| Grower | State | County | Farm | Fields | Irrigation |
|---|---|---|---|---|---|
| Adams Farm | IL | McLean | 1 | 10 | Rainfed |
| Hansen Farm | IA | Story | 1 | 10 | Rainfed |
| Rivera Farm | NE | Hamilton | 1 | 10 | Center-pivot |

**Nebraska county rationale:** Hamilton County sits in the densest center-pivot
corridor of Nebraska's Platte River valley, with >85% irrigated cropland drawing
from the Ogallala Aquifer. It is a canonical corn/soy center-pivot context.

Runtime data location: `~/my-farm-advisor-runtime/`

---

## Scripts

| Script | Category | Outputs |
|---|---|---|
| `generate_data.py` | Setup | `fields.geojson`, `weather.csv`, `cdl.csv`, `weather_field_year.csv` |
| `eda_field_boundaries.py` | Field Boundaries | `fig_fb_01_acreage_dist.png`, `fig_fb_02_field_count.png`, `fig_fb_03_acreage_corr.png`, `fig_map_01_boundaries.png` |
| `eda_weather.py` | Weather | `fig_wx_01_annual_precip.png`, `fig_wx_02_gdd_trend.png`, `fig_wx_03_precip_gdd_corr.png` |
| `eda_cdl.py` | CDL | `fig_cdl_01_crop_class_counts.png`, `fig_cdl_02_rotation_pattern.png`, `fig_cdl_03_size_dominance_corr.png` |

All outputs are saved to `eda_outputs/` relative to the script directory.

---

## Required output summary

| Requirement | Fulfilled by |
|---|---|
| 2 statistical visualizations – Field Boundaries | `fig_fb_01`, `fig_fb_02` |
| 1 comparison/correlation – Field Boundaries | `fig_fb_03` |
| 2 statistical visualizations – Weather | `fig_wx_01`, `fig_wx_02` |
| 1 comparison/correlation – Weather | `fig_wx_03` |
| 2 statistical visualizations – CDL | `fig_cdl_01`, `fig_cdl_02` |
| 1 comparison/correlation – CDL | `fig_cdl_03` |
| 1 geospatial map | `fig_map_01` |

---

## Running the subskill

```bash
# From the assignment-2 branch root
python generate_data.py        # only needed once; seeds ~/my-farm-advisor-runtime
python eda_field_boundaries.py
python eda_weather.py
python eda_cdl.py
```

Dependencies: `geopandas`, `matplotlib`, `seaborn`, `shapely`, `pandas`, `numpy`, `scipy`

---

## Report artifact

A one-time single-page HTML report (`eda_report.html`) is assembled separately
and is not part of this reusable subskill. It summarizes all subskill outputs
for the assignment submission.
