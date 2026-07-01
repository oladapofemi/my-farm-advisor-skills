"""
EDA Category 1: Field Boundaries
Outputs:
  fig_fb_01_acreage_dist.png    – VIZ 1: Acreage distribution histogram by grower
  fig_fb_02_field_count.png     – VIZ 2: Field count + total acres bar chart by grower
  fig_fb_03_acreage_corr.png    – COMPARISON: Field acreage vs field index (rank)
  fig_map_01_boundaries.png     – GEOSPATIAL MAP: All field boundaries colored by grower
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

RUNTIME = os.path.expanduser("~/my-farm-advisor-runtime")
OUTDIR  = os.path.join(os.path.dirname(__file__), "eda_outputs")
os.makedirs(OUTDIR, exist_ok=True)

# Color palette consistent across all outputs
GROWER_COLORS = {"IL001": "#2196F3", "IA001": "#4CAF50", "NE001": "#FF9800"}
GROWER_LABELS = {
    "IL001": "IL – McLean Co.",
    "IA001": "IA – Story Co.",
    "NE001": "NE – Hamilton Co.",
}

gdf = gpd.read_file(os.path.join(RUNTIME, "fields.geojson"))
gdf["grower_label"] = gdf["grower_id"].map(GROWER_LABELS)

# ── VIZ 1: Acreage distribution histogram by grower ──────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
for gid, grp in gdf.groupby("grower_id"):
    ax.hist(grp["acres"], bins=6, alpha=0.75, color=GROWER_COLORS[gid],
            label=GROWER_LABELS[gid], edgecolor="white", linewidth=0.8)
ax.set_title("Field Acreage Distribution by Grower", fontsize=13, fontweight="bold")
ax.set_xlabel("Field Size (acres)")
ax.set_ylabel("Number of Fields")
ax.legend(title="Grower")
ax.grid(axis="y", alpha=0.3)
sns.despine()
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_fb_01_acreage_dist.png"), dpi=150)
plt.close()
print("Saved fig_fb_01_acreage_dist.png")

# ── VIZ 2: Field count and total acreage by grower ──────────────────────────
summary = (gdf.groupby(["grower_id", "grower_label"])
           .agg(field_count=("field_id", "count"), total_acres=("acres", "sum"))
           .reset_index())
x = np.arange(len(summary))
width = 0.35
fig, ax1 = plt.subplots(figsize=(9, 5))
bars1 = ax1.bar(x - width/2, summary["field_count"], width,
                color=[GROWER_COLORS[g] for g in summary["grower_id"]],
                label="Field Count", edgecolor="white")
ax2 = ax1.twinx()
bars2 = ax2.bar(x + width/2, summary["total_acres"], width,
                color=[GROWER_COLORS[g] for g in summary["grower_id"]],
                alpha=0.45, label="Total Acres", edgecolor="white", hatch="//")
ax1.set_xticks(x)
ax1.set_xticklabels(summary["grower_label"], fontsize=10)
ax1.set_ylabel("Number of Fields", color="#333")
ax2.set_ylabel("Total Acres", color="#333")
ax1.set_title("Field Count and Total Acreage per Grower", fontsize=13, fontweight="bold")
# legend
p1 = mpatches.Patch(facecolor="#888", label="Field Count (solid)")
p2 = mpatches.Patch(facecolor="#888", alpha=0.45, hatch="//", label="Total Acres (hatched)")
ax1.legend(handles=[p1, p2], loc="upper left")
sns.despine(right=False)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_fb_02_field_count.png"), dpi=150)
plt.close()
print("Saved fig_fb_02_field_count.png")

# ── COMPARISON: Acreage correlation – field index vs size (across growers) ──
# Shows whether field size is randomly assigned or follows a pattern.
gdf_sorted = gdf.sort_values(["grower_id", "acres"]).copy()
gdf_sorted["rank"] = gdf_sorted.groupby("grower_id").cumcount() + 1

fig, ax = plt.subplots(figsize=(9, 5))
for gid, grp in gdf_sorted.groupby("grower_id"):
    ax.scatter(grp["rank"], grp["acres"], color=GROWER_COLORS[gid],
               label=GROWER_LABELS[gid], s=70, alpha=0.85, edgecolors="white", linewidth=0.5)
    # trend line
    z = np.polyfit(grp["rank"], grp["acres"], 1)
    p = np.poly1d(z)
    ax.plot(sorted(grp["rank"]), p(sorted(grp["rank"])),
            color=GROWER_COLORS[gid], linestyle="--", linewidth=1.2, alpha=0.7)

# Pearson r per grower annotation
for gid, grp in gdf_sorted.groupby("grower_id"):
    r = np.corrcoef(grp["rank"], grp["acres"])[0, 1]
    ax.annotate(f"r={r:.2f}", xy=(0.98, 0.05 + list(gdf_sorted["grower_id"].unique()).index(gid)*0.07),
                xycoords="axes fraction", ha="right", fontsize=9,
                color=GROWER_COLORS[gid], fontweight="bold")

ax.set_title("Field Size vs. Rank Within Grower (Correlation Analysis)", fontsize=13, fontweight="bold")
ax.set_xlabel("Field Rank (smallest → largest within grower)")
ax.set_ylabel("Field Acreage")
ax.legend(title="Grower")
ax.grid(alpha=0.3)
sns.despine()
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_fb_03_acreage_corr.png"), dpi=150)
plt.close()
print("Saved fig_fb_03_acreage_corr.png")

# ── GEOSPATIAL MAP: 3-panel map, one panel per grower, so polygons are visible ─
grower_order = ["IL001", "IA001", "NE001"]
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for ax, gid in zip(axes, grower_order):
    sub = gdf[gdf["grower_id"] == gid].copy()
    sub.plot(ax=ax, color=GROWER_COLORS[gid], edgecolor="white",
             linewidth=0.8, alpha=0.85)
    # label each field number at centroid
    for _, row in sub.iterrows():
        cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
        num = row["field_name"].replace("Field ", "")
        ax.annotate(num, (cx, cy), fontsize=7, ha="center", va="center",
                    color="white", fontweight="bold")
    ax.set_title(GROWER_LABELS[gid], fontsize=10, fontweight="bold",
                 color=GROWER_COLORS[gid])
    ax.set_xlabel("Longitude", fontsize=8)
    ax.set_ylabel("Latitude", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2, linestyle=":")
    # add acreage annotation
    min_a, max_a = int(sub["acres"].min()), int(sub["acres"].max())
    ax.annotate(f"10 fields | {min_a}–{max_a} ac",
                xy=(0.03, 0.04), xycoords="axes fraction",
                fontsize=7.5, color="#444",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

fig.suptitle("Field Boundaries – Illinois, Iowa & Nebraska Growers (WGS-84)",
             fontsize=12, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_map_01_boundaries.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved fig_map_01_boundaries.png")
print("\nField boundaries EDA complete.")
