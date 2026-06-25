#!/usr/bin/env python3
"""
Visualize original field boundary alongside headland and ring buffers.

Example:
    python visualize.py \
        ~/my-farm-advisor-runtime/data-pipeline/growers/ia-grower/farms/ia-grower-iowa/fields/osm-1052414024/boundary/field_boundary.geojson \
        --headland-distance 12 \
        --ring-distance 5
"""

import argparse
import sys
from pathlib import Path

try:
    import geopandas as gpd
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise ImportError(
        "This script requires geopandas and matplotlib. "
        "Install them with: pip install geopandas matplotlib"
    ) from exc

sys.path.insert(0, str(Path(__file__).parent))
from create_headlands import (
    add_area_columns,
    generate_headlands,
    generate_ring,
    load_geojson,
)


def plot_field(
    original_gdf: gpd.GeoDataFrame,
    headlands_gdf: gpd.GeoDataFrame | None,
    ring_gdf: gpd.GeoDataFrame | None,
    title: str = "Field Boundary with Headlands and Ring",
) -> plt.Figure:
    """Plot original, headland, and ring geometries on one figure."""
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot original boundary
    original_gdf.plot(
        ax=ax,
        color="none",
        edgecolor="black",
        linewidth=2,
        label="Original",
    )

    # Plot headland (inner)
    if headlands_gdf is not None and not headlands_gdf.empty:
        headlands_gdf.plot(
            ax=ax,
            color="lightgreen",
            edgecolor="green",
            linewidth=1.5,
            alpha=0.6,
            label="Headland",
        )

    # Plot ring (outer)
    if ring_gdf is not None and not ring_gdf.empty:
        ring_gdf.plot(
            ax=ax,
            color="lightcoral",
            edgecolor="red",
            linewidth=1.5,
            alpha=0.4,
            label="Ring",
        )

    ax.set_title(title, fontsize=14)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="upper right")
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.5)

    # Add acreage annotations
    annotations = []
    orig_acres = float(original_gdf["acres"].iloc[0]) if "acres" in original_gdf.columns else None
    if orig_acres is not None:
        annotations.append(f"Original: {orig_acres:.2f} acres")

    if headlands_gdf is not None and not headlands_gdf.empty and "acres" in headlands_gdf.columns:
        annotations.append(f"Headland: {headlands_gdf['acres'].iloc[0]:.2f} acres")

    if ring_gdf is not None and not ring_gdf.empty and "acres" in ring_gdf.columns:
        annotations.append(f"Ring: {ring_gdf['acres'].iloc[0]:.2f} acres")

    if annotations:
        ax.annotate(
            "\n".join(annotations),
            xy=(0.02, 0.02),
            xycoords="axes fraction",
            fontsize=11,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

    plt.tight_layout()
    return fig


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Visualize field boundary with headland and ring buffers."
    )
    parser.add_argument("input", type=Path, help="Input field boundary GeoJSON path.")
    parser.add_argument(
        "--headland-distance",
        type=float,
        default=12.0,
        help="Inner buffer distance in metres (default: 12).",
    )
    parser.add_argument(
        "--ring-distance",
        type=float,
        default=5.0,
        help="Outer buffer distance in metres (default: 5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to save the figure (e.g. output.png).",
    )
    args = parser.parse_args()

    print(f"Loading: {args.input}")
    gdf = load_geojson(args.input)

    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)

    if gdf.crs.is_geographic:
        utm_crs = gdf.estimate_utm_crs()
        gdf_metric = gdf.to_crs(utm_crs)
    else:
        gdf_metric = gdf.copy()

    gdf_metric = add_area_columns(gdf_metric)
    orig_acres = float(gdf_metric["acres"].iloc[0])
    print(f"Original area: {orig_acres:.2f} acres")

    headlands = None
    if args.headland_distance > 0:
        headlands = generate_headlands(gdf_metric, args.headland_distance)
        if not headlands.empty:
            headlands = add_area_columns(headlands)
            print(f"Headland area: {headlands['acres'].iloc[0]:.2f} acres")
            headlands = headlands.to_crs(gdf.crs)
        else:
            print("Warning: headland collapsed to empty geometry.")
            headlands = None

    ring = None
    if args.ring_distance > 0:
        ring = generate_ring(gdf_metric, args.ring_distance)
        ring = add_area_columns(ring)
        print(f"Ring area:     {ring['acres'].iloc[0]:.2f} acres")
        ring = ring.to_crs(gdf.crs)

    field_id = str(gdf.iloc[0].get("field_id", args.input.stem))
    title = f"Field: {field_id}"
    fig = plot_field(gdf, headlands, ring, title=title)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150)
        print(f"Figure saved to: {args.output}")
    else:
        plt.show()

    return 0


if __name__ == "__main__":
    sys.exit(main())
