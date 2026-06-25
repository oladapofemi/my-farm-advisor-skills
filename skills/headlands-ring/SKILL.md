---
name: headlands-ring
description: Generate headland and ring buffers for agricultural field boundaries.
---

# headlands-ring

**When to use:**
You need to compute headland (inner) or ring (outer) buffer zones around field boundary polygons, calculate resulting acreage, and export new GeoJSONs.

**Where to start:**
- `README.md` — installation, CLI usage, and batch processing
- `create_headlands.py` — single-field script with `--headland-distance` and `--ring-distance`
- `batch_process.py` — recursively process all field boundaries under a growers tree
- `visualize.py` — matplotlib map of original, headland, and ring geometries

**Outputs:**
Per-field GeoJSONs (`*_headlands.geojson`, `*_ring.geojson`) and `summary.csv` with original / buffered acreages.

**Dependencies:**
Python 3.10+, `geopandas`, `shapely`, `matplotlib`.
