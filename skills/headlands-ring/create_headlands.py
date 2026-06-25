#!/usr/bin/env python3
"""
Headlands and Ring Buffer Generator for Field Boundaries.

Reads field boundary GeoJSON files, generates:
  - Inner buffers (headlands): shrink the field by a given distance
  - Outer buffers (rings): expand the field by a given distance

Outputs new GeoJSON FeatureCollections for each operation.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import geopandas as gpd
    from shapely.geometry import mapping, shape
except ImportError as exc:
    raise ImportError(
        "This script requires geopandas and shapely. "
        "Install them with: pip install geopandas shapely"
    ) from exc


def load_geojson(path: Path) -> gpd.GeoDataFrame:
    """Load a GeoJSON file into a GeoDataFrame."""
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {path}")
    return gpd.read_file(path)


def save_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    """Save a GeoDataFrame to a GeoJSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    print(f"  Saved: {path}")


def save_gpkg(gdf: gpd.GeoDataFrame, path: Path) -> None:
    """Save a GeoDataFrame to a GeoPackage file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG")
    print(f"  Saved: {path}")


def generate_headlands(gdf: gpd.GeoDataFrame, distance: float) -> gpd.GeoDataFrame:
    """
    Generate headlands by buffering inward (negative buffer).

    Args:
        gdf: Input GeoDataFrame with field boundaries.
        distance: Distance to buffer inward (in CRS units, typically metres).

    Returns:
        GeoDataFrame with headland geometries. Features that collapse to empty
        geometries are dropped.
    """
    result = gdf.copy()
    result["geometry"] = result.geometry.buffer(-distance)
    print("Inner buffer created")
    print(result.head())
    result = result[~result.geometry.is_empty]
    print("After removing empty geometries:")
    print(result.head())
    if not result.empty:
        print(f"  Buffered area: {result.area.iloc[0]:.2f} m²")
    return result


def generate_headlands_ring(original_gdf: gpd.GeoDataFrame, inner_buffer_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Generate the headlands ring by computing the difference between
    the original field and the inner buffer.

    Args:
        original_gdf: Original field boundary GeoDataFrame.
        inner_buffer_gdf: Inner-buffered (headland) GeoDataFrame.

    Returns:
        GeoDataFrame representing the headland strip.
    """
    ring = original_gdf.copy()
    ring["geometry"] = original_gdf.geometry.difference(inner_buffer_gdf.geometry)
    print("Headlands ring created")
    print(ring.head())
    ring = ring[~ring.geometry.is_empty]
    ring["meters_squared"] = ring.area.round(2)
    ring["acres"] = (ring["meters_squared"] * 0.000247105).round(2)
    print(ring[["meters_squared", "acres"]])
    return ring


def generate_ring(gdf: gpd.GeoDataFrame, distance: float) -> gpd.GeoDataFrame:
    """
    Generate an outer ring buffer (positive buffer).

    Args:
        gdf: Input GeoDataFrame with field boundaries.
        distance: Distance to buffer outward (in CRS units, typically metres).

    Returns:
        GeoDataFrame with buffered geometries.
    """
    result = gdf.copy()
    result["geometry"] = result.geometry.buffer(distance)
    return result


def add_area_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add area columns (m² and acres) to a GeoDataFrame."""
    gdf = gdf.copy()
    gdf["meters_squared"] = gdf.area.round(2)
    gdf["acres"] = (gdf["meters_squared"] * 0.000247105).round(2)
    return gdf


def process_field(
    input_path: Path,
    output_dir: Path,
    headland_distance: float,
    ring_distance: float,
    generate_headlands_ring_flag: bool = True,
) -> None:
    """
    Process a single field boundary GeoJSON.

    Generates headland and ring GeoJSONs in the output directory.
    """
    print(f"Processing: {input_path}")
    gdf = load_geojson(input_path)

    if gdf.crs is None:
        print("  Warning: No CRS found. Assuming EPSG:4326.")
        gdf.set_crs(epsg=4326, inplace=True)

    # Export original boundary as GeoPackage
    stem = input_path.stem
    original_gpkg_path = output_dir / f"{stem}.gpkg"
    save_gpkg(gdf, original_gpkg_path)
    print("Field boundary exported")

    # Reproject to a metric CRS for accurate buffering if necessary.
    if gdf.crs is None or gdf.crs.is_geographic:
        utm_crs = gdf.estimate_utm_crs()
        print(f"  Reprojecting to UTM: {utm_crs}")
        gdf_metric = gdf.to_crs(utm_crs)
    else:
        gdf_metric = gdf.copy()

    # Original area (metric)
    gdf_metric = add_area_columns(gdf_metric)
    print(f"  Original area: {gdf_metric['acres'].iloc[0]} acres")

    # Headlands (inner buffer)
    headlands = None
    if headland_distance > 0:
        headlands = generate_headlands(gdf_metric, headland_distance)
        headlands = add_area_columns(headlands)
        print(
            f"  Headland area: {headlands['acres'].iloc[0]} acres "
            f"(lost {gdf_metric['acres'].iloc[0] - headlands['acres'].iloc[0]:.2f} acres)"
        )
        headlands_crs = headlands.to_crs(gdf.crs)  # Back to original CRS
        stem = input_path.stem
        out_path = output_dir / f"{stem}_headlands.geojson"
        save_geojson(headlands_crs, out_path)

        # Headlands ring (difference: original - inner buffer)
        if generate_headlands_ring_flag:
            headlands_ring = generate_headlands_ring(gdf_metric, headlands)
            headlands_ring = add_area_columns(headlands_ring)
            print(
                f"  Headlands ring area: {headlands_ring['acres'].iloc[0]} acres "
                f"(strip width: {headland_distance}m)"
            )
            headlands_ring = headlands_ring.to_crs(gdf.crs)
            print(f"  Headlands ring CRS: {headlands_ring.crs}")
            out_path = output_dir / f"{stem}_headlands_ring.geojson"
            save_geojson(headlands_ring, out_path)

    # Outer ring (positive buffer)
    if ring_distance > 0:
        ring = generate_ring(gdf_metric, ring_distance)
        ring = add_area_columns(ring)
        print(
            f"  Ring area:     {ring['acres'].iloc[0]} acres "
            f"(gained {ring['acres'].iloc[0] - gdf_metric['acres'].iloc[0]:.2f} acres)"
        )
        ring = ring.to_crs(gdf.crs)  # Back to original CRS
        stem = input_path.stem
        out_path = output_dir / f"{stem}_ring.geojson"
        save_geojson(ring, out_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate headlands and ring buffers for field boundary GeoJSONs."
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="+",
        help="One or more input GeoJSON file paths.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory to write output GeoJSONs (default: ./output).",
    )
    parser.add_argument(
        "--headland-distance",
        type=float,
        default=12.0,
        help="Inner buffer distance in metres for headlands (default: 12).",
    )
    parser.add_argument(
        "--ring-distance",
        type=float,
        default=0.0,
        help="Outer buffer distance in metres for rings (default: 0, disabled).",
    )
    parser.add_argument(
        "--headlands-ring",
        action="store_true",
        default=True,
        help="Generate headlands ring (difference between original and inner buffer) (default: True).",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in args.input:
        try:
            process_field(
                input_path,
                args.output_dir,
                args.headland_distance,
                args.ring_distance,
                args.headlands_ring,
            )
        except Exception as exc:
            print(f"  Error processing {input_path}: {exc}", file=sys.stderr)
            continue

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
