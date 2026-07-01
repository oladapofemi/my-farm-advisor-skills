"""
Assignment 2 – Dataset Generator
Produces a realistic synthetic runtime dataset for:
  - Illinois grower (McLean County, central IL corn/soy)
  - Iowa grower (Story County, central IA corn/soy)
  - Nebraska grower (Hamilton County, NE – strong center-pivot irrigation corridor)

Each grower: 1 farm, 10 fields.
Outputs (saved to ~/my-farm-advisor-runtime/):
  - growers.csv          master grower table
  - fields.geojson       all 30 field polygons (WGS-84)
  - weather.csv          daily weather summaries 2020-2024 per field
  - cdl.csv              CDL crop class per field per year 2020-2024
"""

import os, json, math, random
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

random.seed(42)
np.random.seed(42)

RUNTIME = os.path.expanduser("~/my-farm-advisor-runtime")
os.makedirs(RUNTIME, exist_ok=True)

# ── Grower definitions ───────────────────────────────────────────────────────
GROWERS = [
    {
        "grower_id": "IL001",
        "grower_name": "Adams Farm – McLean Co., IL",
        "state": "IL",
        "county": "McLean",
        "lat_center": 40.50,
        "lon_center": -88.95,
        "irr_type": "rainfed",
        "context": "Central Illinois – prime corn/soy belt, rainfed, flat glacial till",
    },
    {
        "grower_id": "IA001",
        "grower_name": "Hansen Farm – Story Co., IA",
        "state": "IA",
        "county": "Story",
        "lat_center": 42.02,
        "lon_center": -93.62,
        "irr_type": "rainfed",
        "context": "Central Iowa – high-productivity corn/soy, rainfed, tile-drained",
    },
    {
        "grower_id": "NE001",
        "grower_name": "Rivera Farm – Hamilton Co., NE",
        "state": "NE",
        "county": "Hamilton",
        "lat_center": 40.87,
        "lon_center": -98.00,
        "irr_type": "center-pivot",
        "context": "South-central Nebraska – Ogallala Aquifer zone, center-pivot corn/soy, "
                   "Hamilton County chosen because it sits in the densest pivot corridor "
                   "of Nebraska's Platte River valley with >85% irrigated cropland.",
    },
]

pd.DataFrame(GROWERS).to_csv(os.path.join(RUNTIME, "growers.csv"), index=False)

# ── Field polygon generator ──────────────────────────────────────────────────
# Degrees-per-metre approximation
DEG_LAT = 1 / 111_320  # constant
def deg_lon(lat): return 1 / (111_320 * math.cos(math.radians(lat)))

def make_field_polygon(lat_c, lon_c, acres, angle_deg=0):
    """Return a slightly irregular quadrilateral field polygon."""
    side_m = math.sqrt(acres * 4046.86)          # convert acres → m, square root for side
    dlat = side_m * DEG_LAT
    dlon = side_m * deg_lon(lat_c)
    # add ±5% jitter per corner for realism
    jitter = 0.05
    def j(): return 1 + random.uniform(-jitter, jitter)
    corners = [
        (lon_c - dlon/2 * j(), lat_c - dlat/2 * j()),
        (lon_c + dlon/2 * j(), lat_c - dlat/2 * j()),
        (lon_c + dlon/2 * j(), lat_c + dlat/2 * j()),
        (lon_c - dlon/2 * j(), lat_c + dlat/2 * j()),
    ]
    return Polygon(corners)

FIELD_ACRES_POOL = [40, 60, 80, 100, 120, 150, 80, 60, 90, 110]

features = []
field_meta = []

# Grid spacing between fields (degrees)
GRID_DLAT = 0.015   # ~1.7 km
GRID_DLON = 0.022

for grower in GROWERS:
    cols = 5  # 2 rows × 5 cols = 10 fields
    for i in range(10):
        row, col = divmod(i, cols)
        lat = grower["lat_center"] + (row - 0.5) * GRID_DLAT
        lon = grower["lon_center"] + (col - 2) * GRID_DLON
        acres = FIELD_ACRES_POOL[i]
        fid = f"{grower['grower_id']}_F{i+1:02d}"

        geom = make_field_polygon(lat, lon, acres)
        features.append({
            "type": "Feature",
            "properties": {
                "field_id":    fid,
                "grower_id":   grower["grower_id"],
                "grower_name": grower["grower_name"],
                "state":       grower["state"],
                "county":      grower["county"],
                "farm_id":     f"{grower['grower_id']}_FARM1",
                "field_name":  f"Field {i+1}",
                "acres":       acres,
                "irr_type":    grower["irr_type"],
                "lat_c":       lat,
                "lon_c":       lon,
            },
            "geometry": geom.__geo_interface__,
        })
        field_meta.append({
            "field_id":  fid,
            "grower_id": grower["grower_id"],
            "state":     grower["state"],
            "acres":     acres,
            "irr_type":  grower["irr_type"],
        })

geojson = {"type": "FeatureCollection", "features": features}
with open(os.path.join(RUNTIME, "fields.geojson"), "w") as f:
    json.dump(geojson, f)

print(f"Saved {len(features)} field polygons → {RUNTIME}/fields.geojson")

# ── CDL (Cropland Data Layer) generator ─────────────────────────────────────
# Corn-soy rotation is the dominant pattern in all three states.
# Nebraska also has some irrigated wheat and alfalfa (~10%).
CDL_CLASSES = {
    "IL": {1: "Corn", 5: "Soybeans"},
    "IA": {1: "Corn", 5: "Soybeans"},
    "NE": {1: "Corn", 5: "Soybeans", 22: "Winter Wheat", 36: "Alfalfa"},
}
CDL_WEIGHTS = {
    "IL": [0.52, 0.48],
    "IA": [0.50, 0.50],
    "NE": [0.50, 0.35, 0.10, 0.05],
}
YEARS = list(range(2020, 2025))

cdl_rows = []
for fm in field_meta:
    state = fm["state"]
    classes = list(CDL_CLASSES[state].keys())
    weights = CDL_WEIGHTS[state]
    prev_crop = None
    for yr in YEARS:
        # enforce corn-soy rotation when possible
        if prev_crop == 1 and state in ("IL", "IA"):
            crop_code = 5
        elif prev_crop == 5 and state in ("IL", "IA"):
            crop_code = 1
        else:
            crop_code = random.choices(classes, weights=weights)[0]
        prev_crop = crop_code
        # CDL pixel majority (%) – field is mostly one crop but can have edge pixels
        dominant_pct = round(random.uniform(0.82, 0.98), 3)
        cdl_rows.append({
            "field_id":    fm["field_id"],
            "grower_id":   fm["grower_id"],
            "state":       state,
            "year":        yr,
            "crop_code":   crop_code,
            "crop_name":   CDL_CLASSES[state][crop_code],
            "dominant_pct": dominant_pct,
            "acres":       fm["acres"],
        })

cdl_df = pd.DataFrame(cdl_rows)
cdl_df.to_csv(os.path.join(RUNTIME, "cdl.csv"), index=False)
print(f"Saved {len(cdl_df)} CDL records → {RUNTIME}/cdl.csv")

# ── Weather generator ────────────────────────────────────────────────────────
# Daily summaries per field-year: tmax, tmin, precip, GDD (base 10°C).
# Climate normals loosely based on NOAA data for each state.
CLIMATE = {
    "IL": {"tmax_mean": 16.5, "tmax_std": 11.0, "precip_ann": 950,  "hot_months": [6,7,8]},
    "IA": {"tmax_mean": 14.0, "tmax_std": 12.0, "precip_ann": 850,  "hot_months": [6,7,8]},
    "NE": {"tmax_mean": 13.5, "tmax_std": 13.0, "precip_ann": 620,  "hot_months": [6,7,8]},
}

def gdd(tmax_c, tmin_c, base=10):
    tavg = (tmax_c + tmin_c) / 2
    return max(0, tavg - base)

weather_rows = []
for fm in field_meta:
    state = fm["state"]
    cl = CLIMATE[state]
    for yr in YEARS:
        # slight year-to-year variability
        yr_adj = random.uniform(-0.8, 0.8)   # °C shift for that year
        precip_adj = random.uniform(0.85, 1.15)
        for month in range(1, 13):
            days_in_month = pd.Period(f"{yr}-{month:02d}").days_in_month
            is_hot = month in cl["hot_months"]
            for day in range(1, days_in_month + 1):
                # seasonal tmax: use sine curve
                day_of_year = pd.Timestamp(yr, month, day).day_of_year
                seasonal = cl["tmax_std"] * math.sin(math.pi * (day_of_year - 80) / 182)
                tmax = cl["tmax_mean"] + seasonal + yr_adj + random.gauss(0, 2.5)
                tmin = tmax - random.uniform(7, 14)
                # precip: exponential distribution, zero-inflated
                has_rain = random.random() < 0.30
                precip_mm = round(random.expovariate(1/8) if has_rain else 0, 1)
                weather_rows.append({
                    "field_id":  fm["field_id"],
                    "grower_id": fm["grower_id"],
                    "state":     state,
                    "date":      f"{yr}-{month:02d}-{day:02d}",
                    "year":      yr,
                    "month":     month,
                    "tmax_c":    round(tmax, 2),
                    "tmin_c":    round(tmin, 2),
                    "precip_mm": precip_mm,
                    "gdd_c":     round(gdd(tmax, tmin), 2),
                })

weather_df = pd.DataFrame(weather_rows)
weather_df.to_csv(os.path.join(RUNTIME, "weather.csv"), index=False)
print(f"Saved {len(weather_df):,} weather records → {RUNTIME}/weather.csv")

# ── Field-year summary ───────────────────────────────────────────────────────
w_agg = (weather_df.groupby(["field_id", "grower_id", "state", "year"])
         .agg(
             ann_precip_mm=("precip_mm", "sum"),
             ann_gdd_c=("gdd_c", "sum"),
             mean_tmax_c=("tmax_c", "mean"),
         )
         .reset_index()
         .round(2))
w_agg.to_csv(os.path.join(RUNTIME, "weather_field_year.csv"), index=False)
print(f"Saved field-year weather summary → {RUNTIME}/weather_field_year.csv")

print("\nDataset generation complete.")
print(f"  Growers : {len(GROWERS)}")
print(f"  Fields  : {len(features)}")
print(f"  CDL rows: {len(cdl_df)}")
print(f"  Weather rows: {len(weather_df):,}")
