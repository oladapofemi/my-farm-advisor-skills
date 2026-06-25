# Headlands and Ring Buffer Generator

Generate headland (inner) and ring (outer) buffers around agricultural field boundaries from GeoJSON inputs. Computes acreage before and after buffering and outputs new GeoJSONs plus a summary CSV.

## What it does

- **Reads** field boundary GeoJSON files (e.g. from `growers/*/fields/*/boundary/field_boundary.geojson`).
- **Reprojects** to a local UTM CRS for accurate metric buffering.
- **Generates headlands** by buffering inward (negative buffer) by a configurable distance in metres.
- **Generates rings** by buffering outward (positive buffer) by a configurable distance in metres.
- **Calculates area** in square metres and acres for each geometry.
- **Outputs** per-field GeoJSONs and a batch summary CSV.

## Quick start

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv skills/headlands-ring/.venv
skills/headlands-ring/.venv/bin/pip install geopandas shapely matplotlib

# 2. Process a single field
skills/headlands-ring/.venv/bin/python skills/headlands-ring/create_headlands.py \
  ~/my-farm-advisor-runtime/data-pipeline/growers/ia-grower/farms/ia-grower-iowa/fields/osm-1052414024/boundary/field_boundary.geojson \
  --output-dir skills/headlands-ring/output \
  --headland-distance 12 \
  --ring-distance 5

# 3. Process all fields (batch)
skills/headlands-ring/.venv/bin/python skills/headlands-ring/batch_process.py

# 4. Visualize one field
skills/headlands-ring/.venv/bin/python skills/headlands-ring/visualize.py \
  ~/my-farm-advisor-runtime/data-pipeline/growers/ia-grower/farms/ia-grower-iowa/fields/osm-1052414024/boundary/field_boundary.geojson \
  --headland-distance 12 \
  --ring-distance 5
```

## Scripts

| Script | Purpose |
|--------|---------|
| `create_headlands.py` | Single-field headland / ring generation with CLI args |
| `batch_process.py` | Recursively process every `field_boundary.geojson` under a growers directory |
| `visualize.py` | Matplotlib plot showing original, headland, and ring polygons |

## CLI options (create_headlands.py)

```
usage: create_headlands.py [-h] [--output-dir OUTPUT_DIR]
                           [--headland-distance HEADLAND_DISTANCE]
                           [--ring-distance RING_DISTANCE]
                           input [input ...]

positional arguments:
  input                 One or more input GeoJSON file paths.

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        Directory to write output GeoJSONs (default: ./output).
  --headland-distance HEADLAND_DISTANCE
                        Inner buffer distance in metres (default: 12).
  --ring-distance RING_DISTANCE
                        Outer buffer distance in metres (default: 0, disabled).
```

## Example output

```
Processing: .../field_boundary.geojson
  Reprojecting to UTM: EPSG:32615
  Original area: 38.82 acres
  Headland area: 34.26 acres (lost 4.56 acres)
  Ring area:     40.80 acres (gained 1.98 acres)
```

## Batch summary

`batch_process.py` writes `output/summary.csv` with columns:

- `field_id`
- `original_acres`
- `headland_acres`
- `headland_lost_acres`
- `ring_acres`
- `ring_gained_acres`
- `source_path`

## Requirements

- Python 3.10+
- `geopandas`
- `shapely`
- `matplotlib` (for `visualize.py`)

## Notes

- Input GeoJSONs are assumed to be in WGS 84 (EPSG:4326) if no CRS is present.
- The script uses `geopandas.GeoDataFrame.estimate_utm_crs()` to pick an appropriate metric CRS for each field, then reprojects results back to the original CRS.
- Features whose headland collapses to empty geometry (very small fields relative to buffer distance) are skipped with a warning.
