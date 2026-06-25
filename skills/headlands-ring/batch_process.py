#!/usr/bin/env python3
"""
Batch process all field boundaries for headlands and ring generation.
Produces a summary CSV and per-field GeoJSON outputs.
"""

import csv
import sys
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise ImportError("This script requires geopandas. Install: pip install geopandas") from exc

# Import helpers from create_headlands.py
sys.path.insert(0, str(Path(__file__).parent))
from create_headlands import (
    add_area_columns,
    generate_headlands,
    generate_ring,
    load_geojson,
    save_geojson,
)


def find_all_field_boundaries(base_dir: Path) -> list[Path]:
    """Recursively find all field_boundary.geojson files."""
    return sorted(base_dir.rglob("*/boundary/field_boundary.geojson"))


def process_all_fields(
    base_dir: Path,
    output_dir: Path,
    headland_distance: float,
    ring_distance: float,
) -> list[dict]:
    """Process every field boundary found under base_dir."""
    field_paths = find_all_field_boundaries(base_dir)
    print(f"Found {len(field_paths)} field boundary files.\n")

    records = []
    for path in field_paths:
        print(f"Processing: {path}")
        gdf = load_geojson(path)

        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)

        if gdf.crs.is_geographic:
            utm_crs = gdf.estimate_utm_crs()
            gdf_metric = gdf.to_crs(utm_crs)
        else:
            gdf_metric = gdf.copy()

        gdf_metric = add_area_columns(gdf_metric)
        orig_acres = float(gdf_metric["acres"].iloc[0])

        record = {
            "field_id": str(gdf_metric.iloc[0].get("field_id", path.stem)),
            "source_path": str(path),
            "original_acres": orig_acres,
            "headland_acres": None,
            "headland_lost_acres": None,
            "ring_acres": None,
            "ring_gained_acres": None,
        }

        # Headlands
        if headland_distance > 0:
            headlands = generate_headlands(gdf_metric, headland_distance)
            if not headlands.empty:
                headlands = add_area_columns(headlands)
                hl_acres = float(headlands["acres"].iloc[0])
                record["headland_acres"] = hl_acres
                record["headland_lost_acres"] = round(orig_acres - hl_acres, 2)
                headlands = headlands.to_crs(gdf.crs)
                rel = path.parent.relative_to(base_dir)
                out_path = output_dir / rel / f"{path.stem}_headlands.geojson"
                save_geojson(headlands, out_path)
            else:
                print(f"  Warning: headland collapsed for {path}")

        # Ring
        if ring_distance > 0:
            ring = generate_ring(gdf_metric, ring_distance)
            ring = add_area_columns(ring)
            r_acres = float(ring["acres"].iloc[0])
            record["ring_acres"] = r_acres
            record["ring_gained_acres"] = round(r_acres - orig_acres, 2)
            ring = ring.to_crs(gdf.crs)
            rel = path.parent.relative_to(base_dir)
            out_path = output_dir / rel / f"{path.stem}_ring.geojson"
            save_geojson(ring, out_path)

        records.append(record)
        print()

    return records


def write_summary_csv(records: list[dict], path: Path) -> None:
    """Write summary records to CSV."""
    fieldnames = [
        "field_id",
        "original_acres",
        "headland_acres",
        "headland_lost_acres",
        "ring_acres",
        "ring_gained_acres",
        "source_path",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Summary written to: {path}")


def main() -> int:
    base_dir = Path("/home/coder/my-farm-advisor-runtime/data-pipeline/growers")
    output_dir = Path(__file__).parent / "output"
    summary_path = output_dir / "summary.csv"

    headland_distance = 12.0  # metres
    ring_distance = 5.0       # metres

    records = process_all_fields(
        base_dir,
        output_dir,
        headland_distance,
        ring_distance,
    )

    write_summary_csv(records, summary_path)

    # Print a quick table
    print("\n" + "=" * 80)
    print(f"{'Field ID':<25} {'Orig':>8} {'Headland':>10} {'Lost':>8} {'Ring':>10} {'Gained':>8}")
    print("-" * 80)
    for r in records:
        print(
            f"{r['field_id']:<25} "
            f"{r['original_acres']:>8.2f} "
            f"{r['headland_acres'] or 0:>10.2f} "
            f"{r['headland_lost_acres'] or 0:>8.2f} "
            f"{r['ring_acres'] or 0:>10.2f} "
            f"{r['ring_gained_acres'] or 0:>8.2f}"
        )
    print("=" * 80)
    print(f"\nTotal fields processed: {len(records)}")
    print(f"Total original area:    {sum(r['original_acres'] for r in records):.2f} acres")

    return 0


if __name__ == "__main__":
    sys.exit(main())
