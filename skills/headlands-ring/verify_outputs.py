#!/usr/bin/env python3
"""Verify output GPKG files by reading them and printing columns."""

import geopandas as gpd
from pathlib import Path

# Read the original field boundary
field_path = Path("skills/headlands-ring/output/field_boundary.gpkg")
field = gpd.read_file(field_path)

# Read the headlands ring
ring_path = Path("skills/headlands-ring/output/field_boundary_headlands_ring.gpkg")
ring = gpd.read_file(ring_path)

print("=" * 60)
print("FIELD BOUNDARY COLUMNS")
print("=" * 60)
print(field.columns.tolist())
print()

print("=" * 60)
print("HEADLANDS RING COLUMNS")
print("=" * 60)
print(ring.columns.tolist())
print()

print("=" * 60)
print("FIELD BOUNDARY FIRST ROW")
print("=" * 60)
print(field.head(1))
print()

print("=" * 60)
print("HEADLANDS RING FIRST ROW")
print("=" * 60)
print(ring.head(1))
print()

print("=" * 60)
print("CRS INFO")
print("=" * 60)
print(f"Field CRS: {field.crs}")
print(f"Ring  CRS: {ring.crs}")
print()

print("=" * 60)
print("AREA COMPARISON (reprojected to UTM for accurate m²)")
print("=" * 60)
field_utm = field.to_crs(field.estimate_utm_crs())
ring_utm = ring.to_crs(ring.estimate_utm_crs())
print(f"Field area: {field_utm.area.iloc[0]:.2f} m²")
print(f"Ring  area: {ring_utm.area.iloc[0]:.2f} m²")
print(f"Ring is {ring_utm.area.iloc[0] / field_utm.area.iloc[0] * 100:.1f}% of field")
