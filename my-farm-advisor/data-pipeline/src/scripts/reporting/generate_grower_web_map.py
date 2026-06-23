#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""Generate a lightweight, self-contained interactive HTML web map for a grower.

Reads the grower's farms and field boundary GeoJSON files, then produces a
single HTML file with an embedded Leaflet.js map.  All data is embedded; the
file opens offline except for the internet basemap tiles.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

import geopandas as gpd

_LOCAL_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LOCAL_LIB))

from runtime_paths import resolve_runtime_paths  # noqa: E402

_RUNTIME_PATHS = resolve_runtime_paths()
_REPO = _RUNTIME_PATHS.runtime_base
_SCRIPTS = _RUNTIME_PATHS.runtime_scripts
_LIB = _RUNTIME_PATHS.runtime_scripts / "lib"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_LIB))

from paths import (  # noqa: E402
    farm_boundary_path,
    farm_dir,
    grower_dir,
)
from reporting_bootstrap import ensure_skill_path  # noqa: E402

_FARM_INTEL_SKILL = ensure_skill_path("farm-intelligence-reporting")
from pipeline import (  # noqa: E402
    STEP_GROWER_WEB_MAP_RENDER,
    FieldReportingConfig,
    build_step_manifest,
    load_manifest,
    step_is_stale,
)

_SCRIPT = Path(__file__)
_DEFAULT_GROWER = os.environ.get("AG_GROWER_SLUG", "default-grower")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _discover_farms(grower_slug: str) -> list[dict[str, Any]]:
    """Return a list of farm metadata dicts for the given grower."""
    farms_root = grower_dir(grower_slug) / "farms"
    if not farms_root.exists():
        return []
    farms: list[dict[str, Any]] = []
    for farm_path in sorted(farms_root.iterdir()):
        if not farm_path.is_dir():
            continue
        farm_json = farm_path / "farm.json"
        meta = _load_json(farm_json)
        if meta:
            farms.append(meta)
    return farms


def _simplify_geometry(fields: gpd.GeoDataFrame, tolerance: float = 0.0001) -> gpd.GeoDataFrame:
    """Simplify polygon geometries to reduce embedded GeoJSON size."""
    simplified = fields.copy()
    simplified["geometry"] = simplified.geometry.simplify(tolerance, preserve_topology=True)
    return simplified


def _field_color(index: int) -> str:
    """Return a pleasant, distinguishable fill color for a field index."""
    palette = [
        "#2E7D32", "#1565C0", "#C62828", "#F9A825",
        "#6A1B9A", "#00695C", "#D84315", "#0277BD",
        "#558B2F", "#4527A0", "#AD1457", "#00838F",
    ]
    return palette[index % len(palette)]


def _build_geojson_features(grower_slug: str, grower_name: str) -> list[dict[str, Any]]:
    """Build a flat list of GeoJSON Feature dicts for all farms under a grower."""
    features: list[dict[str, Any]] = []
    farms = _discover_farms(grower_slug)
    for farm in farms:
        farm_slug = str(farm.get("farm_slug", ""))
        farm_name = str(farm.get("display_name", farm_slug))
        boundary_path = farm_boundary_path(grower_slug, farm_slug)
        if not boundary_path.exists():
            continue
        try:
            fields = gpd.read_file(boundary_path)
        except Exception:
            continue
        if fields.empty:
            continue
        fields = _simplify_geometry(fields)
        fields_wgs84 = fields.to_crs("EPSG:4326")
        for idx, row in fields_wgs84.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            props = {
                "grower_name": grower_name,
                "farm_name": farm_name,
                "farm_slug": farm_slug,
                "field_id": str(row.get("field_id", f"field-{idx}")),
                "field_name": str(row.get("field_name", row.get("field_id", f"field-{idx}"))),
                "area_acres": float(row.get("area_acres", 0)) if row.get("area_acres") is not None else 0.0,
                "crop_name": str(row.get("crop_name", "unknown")),
                "county_name": str(row.get("county_name", "")),
                "state_fips": str(row.get("state_fips", "")),
                "fill_color": _field_color(idx),
            }
            feature = {
                "type": "Feature",
                "geometry": geom.__geo_interface__,
                "properties": props,
            }
            features.append(feature)
    return features


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _generate_html(grower_slug: str, grower_name: str, features: list[dict[str, Any]]) -> str:
    if not features:
        return _empty_html(grower_name)

    # Compute overall bounds for initial map view
    all_lats = []
    all_lons = []
    for f in features:
        coords = _extract_coords(f["geometry"])
        for lon, lat in coords:
            all_lons.append(lon)
            all_lats.append(lat)
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    # Build field list sidebar items with zoom-to bounds
    field_items: list[str] = []
    for f in features:
        props = f["properties"]
        fid = _html_escape(props["field_id"])
        fname = _html_escape(props.get("field_name", fid))
        farm_name = _html_escape(props["farm_name"])
        coords = _extract_coords(f["geometry"])
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        bounds_str = f"[[{min(lats):.6f}, {min(lons):.6f}], [{max(lats):.6f}, {max(lons):.6f}]]"
        area = props.get("area_acres", 0)
        area_str = f"{area:.1f} ac" if area else ""
        field_items.append(
            f'<li class="field-item" data-bounds="{bounds_str}">'
            f'<span class="field-name">{fname}</span>'
            f'<span class="field-meta">{farm_name}{" &middot; " + area_str if area_str else ""}</span>'
            f"</li>"
        )

    geojson_str = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_html_escape(grower_name)} — Field Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; }}
    #container {{ display: flex; height: 100vh; }}
    #sidebar {{
      width: 320px;
      background: #ffffff;
      border-right: 1px solid #dee2e6;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    #sidebar header {{
      padding: 1.25rem 1rem;
      background: linear-gradient(135deg, #e0f2fe, #fef3c7);
      border-bottom: 1px solid #bfdbfe;
    }}
    #sidebar header h1 {{
      margin: 0;
      font-size: 1.15rem;
      color: #1e3a5f;
    }}
    #sidebar header p {{
      margin: 0.25rem 0 0;
      font-size: 0.8rem;
      color: #475569;
    }}
    #field-list {{
      flex: 1;
      overflow-y: auto;
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .field-item {{
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #f1f5f9;
      cursor: pointer;
      transition: background 0.15s;
    }}
    .field-item:hover {{ background: #f0f9ff; }}
    .field-item.active {{ background: #dbeafe; border-left: 4px solid #2563eb; }}
    .field-name {{
      display: block;
      font-weight: 600;
      font-size: 0.9rem;
      color: #1e293b;
    }}
    .field-meta {{
      display: block;
      font-size: 0.78rem;
      color: #64748b;
      margin-top: 0.15rem;
    }}
    #map {{ flex: 1; }}
    .legend {{
      background: white;
      padding: 8px 12px;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      font-size: 0.8rem;
      line-height: 1.5;
      color: #333;
    }}
    .legend i {{
      width: 14px;
      height: 14px;
      float: left;
      margin-right: 8px;
      opacity: 0.85;
      border-radius: 3px;
    }}
    @media (max-width: 768px) {{
      #sidebar {{ width: 240px; }}
      #sidebar header h1 {{ font-size: 1rem; }}
    }}
  </style>
</head>
<body>
  <div id="container">
    <div id="sidebar">
      <header>
        <h1>{_html_escape(grower_name)}</h1>
        <p>{len(features)} field{'s' if len(features) != 1 else ''} &middot; Interactive map</p>
      </header>
      <ul id="field-list">
        {''.join(field_items)}
      </ul>
    </div>
    <div id="map"></div>
  </div>
  <script>
    var map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 13);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      maxZoom: 19
    }}).addTo(map);

    var geojsonData = {geojson_str};

    var layer = L.geoJSON(geojsonData, {{
      style: function(feature) {{
        return {{
          color: '#1e293b',
          weight: 1.5,
          fillColor: feature.properties.fill_color,
          fillOpacity: 0.55
        }};
      }},
      onEachFeature: function(feature, layer) {{
        var p = feature.properties;
        var popupHtml = '<div style="font-family:sans-serif;font-size:0.85rem;line-height:1.5;">'
          + '<strong style="font-size:1rem;color:#1e3a5f;">' + p.field_name + '</strong><hr style="margin:0.4rem 0;border:none;border-top:1px solid #e2e8f0;">'
          + '<b>Grower:</b> ' + p.grower_name + '<br>'
          + '<b>Farm:</b> ' + p.farm_name + '<br>'
          + '<b>Field ID:</b> ' + p.field_id + '<br>'
          + '<b>Area:</b> ' + (p.area_acres ? p.area_acres.toFixed(1) + ' acres' : 'N/A') + '<br>'
          + '<b>Crop:</b> ' + p.crop_name + '<br>'
          + (p.county_name ? '<b>County:</b> ' + p.county_name + '<br>' : '')
          + (p.state_fips ? '<b>State FIPS:</b> ' + p.state_fips : '')
          + '</div>';
        layer.bindPopup(popupHtml);
      }}
    }}).addTo(map);

    map.fitBounds(layer.getBounds(), {{ padding: [40, 40] }});

    // Sidebar zoom interaction
    var fieldItems = document.querySelectorAll('.field-item');
    fieldItems.forEach(function(item, index) {{
      item.addEventListener('click', function() {{
        fieldItems.forEach(function(el) {{ el.classList.remove('active'); }});
        item.classList.add('active');
        var bounds = JSON.parse(item.getAttribute('data-bounds'));
        map.fitBounds(bounds, {{ padding: [60, 60], maxZoom: 16 }});
        // Open popup for the corresponding layer
        var layers = layer.getLayers();
        if (layers[index]) {{
          layers[index].openPopup();
        }}
      }});
    }});
  </script>
</body>
</html>
'''
    return html


def _extract_coords(geometry: dict[str, Any]) -> list[list[float]]:
    """Flatten all coordinate pairs from a GeoJSON geometry."""
    coords: list[list[float]] = []
    geom_type = geometry.get("type", "")
    raw_coords = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        for ring in raw_coords:
            for point in ring:
                coords.append(point)
    elif geom_type == "MultiPolygon":
        for polygon in raw_coords:
            for ring in polygon:
                for point in ring:
                    coords.append(point)
    elif geom_type == "Point":
        coords.append(raw_coords)
    return coords


def _empty_html(grower_name: str) -> str:
    return textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="utf-8"><title>{_html_escape(grower_name)} — Field Map</title></head>
    <body style="font-family:sans-serif;padding:2rem;">
      <h1>{_html_escape(grower_name)}</h1>
      <p>No field boundaries found for this grower.</p>
    </body>
    </html>
    """)


def _output_path(grower_slug: str) -> Path:
    out_dir = grower_dir(grower_slug) / "derived" / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{grower_slug}_web_map.html"


def main() -> None:
    print("=" * 60)
    print("Grower web map — lightweight interactive Leaflet map")
    print("=" * 60)

    grower_slug = _DEFAULT_GROWER
    grower_meta = _load_json(grower_dir(grower_slug) / "grower.json")
    grower_name = str(grower_meta.get("display_name", grower_slug))

    output_path = _output_path(grower_slug)
    manifest_dir = grower_dir(grower_slug) / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Gather input paths for manifest
    input_paths: list[str] = [str(grower_dir(grower_slug) / "grower.json")]
    farms = _discover_farms(grower_slug)
    for farm in farms:
        farm_slug = str(farm.get("farm_slug", ""))
        if not farm_slug:
            continue
        boundary = farm_boundary_path(grower_slug, farm_slug)
        if boundary.exists():
            input_paths.append(str(boundary))
        farm_json = farm_dir(grower_slug, farm_slug) / "farm.json"
        if farm_json.exists():
            input_paths.append(str(farm_json))

    config = FieldReportingConfig(
        farm_name=grower_name,
        field_boundary_path="",
        grower_slug=grower_slug,
        farm_slug="",
    )

    prior = load_manifest(manifest_dir / f"{STEP_GROWER_WEB_MAP_RENDER}.json")
    manifest = build_step_manifest(
        step_name=STEP_GROWER_WEB_MAP_RENDER,
        input_paths=input_paths,
        output_paths=[output_path],
        code_paths=[_SCRIPT],
        config=config,
    )
    force = os.environ.get("AG_FORCE") == "1"
    if not force and not step_is_stale(manifest, prior):
        print("skip  grower web map (current)")
        return

    print(f"  Grower: {grower_name} ({grower_slug})")
    print(f"  Farms discovered: {len(farms)}")

    features = _build_geojson_features(grower_slug, grower_name)
    print(f"  Total fields: {len(features)}")

    html = _generate_html(grower_slug, grower_name, features)
    output_path.write_text(html, encoding="utf-8")

    manifest.status = "complete"
    manifest.write(manifest_dir / f"{STEP_GROWER_WEB_MAP_RENDER}.json")
    print(f"  HTML map saved → {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
