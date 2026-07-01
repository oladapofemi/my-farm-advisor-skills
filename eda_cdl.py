"""
EDA Category 3: CDL / Cropland Data Layer
Outputs:
  fig_cdl_01_crop_class_counts.png  – VIZ 1: Crop class frequency per grower (stacked bar)
  fig_cdl_02_rotation_pattern.png   – VIZ 2: Crop rotation heatmap (field × year) per grower
  fig_cdl_03_size_dominance_corr.png – COMPARISON: Field size vs CDL dominant pct correlation
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats

RUNTIME = os.path.expanduser("~/my-farm-advisor-runtime")
OUTDIR  = os.path.join(os.path.dirname(__file__), "eda_outputs")
os.makedirs(OUTDIR, exist_ok=True)

GROWER_COLORS = {"IL001": "#2196F3", "IA001": "#4CAF50", "NE001": "#FF9800"}
GROWER_LABELS = {
    "IL001": "IL – McLean Co.",
    "IA001": "IA – Story Co.",
    "NE001": "NE – Hamilton Co.",
}
CROP_COLORS = {
    "Corn": "#FFC107", "Soybeans": "#8BC34A",
    "Winter Wheat": "#A1887F", "Alfalfa": "#00BCD4",
}

cdl = pd.read_csv(os.path.join(RUNTIME, "cdl.csv"))
cdl["grower_label"] = cdl["grower_id"].map(GROWER_LABELS)

# ── VIZ 1: Crop class counts per grower (stacked bar by year) ────────────────
crop_year = (cdl.groupby(["grower_id", "year", "crop_name"])
             .size().rename("count").reset_index())

fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=True)
grower_order = ["IL001", "IA001", "NE001"]
years = sorted(cdl["year"].unique())
crops_all = sorted(cdl["crop_name"].unique())

for ax, gid in zip(axes, grower_order):
    pivot = (crop_year[crop_year["grower_id"] == gid]
             .pivot(index="year", columns="crop_name", values="count")
             .fillna(0)
             .reindex(columns=crops_all, fill_value=0))
    bottom = np.zeros(len(pivot))
    for crop in crops_all:
        if crop in pivot.columns:
            bars = ax.bar(pivot.index, pivot[crop], bottom=bottom,
                          color=CROP_COLORS.get(crop, "#888"),
                          label=crop, edgecolor="white", linewidth=0.5)
            bottom += pivot[crop].values
    ax.set_title(GROWER_LABELS[gid], fontsize=10, fontweight="bold")
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45, fontsize=8)
    ax.set_xlabel("Year")
    ax.grid(axis="y", alpha=0.3)
    sns.despine(ax=ax)

axes[0].set_ylabel("Number of Fields")
# shared legend
handles = [mpatches.Patch(color=CROP_COLORS.get(c, "#888"), label=c) for c in crops_all]
fig.legend(handles=handles, title="Crop", loc="lower center", ncol=len(crops_all),
           bbox_to_anchor=(0.5, -0.05))
fig.suptitle("CDL Crop Class Counts per Year by Grower", fontsize=12, fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_cdl_01_crop_class_counts.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved fig_cdl_01_crop_class_counts.png")

# ── VIZ 2: Crop rotation heatmap per grower (field × year) ──────────────────
# Encode crops as numbers for heatmap
CROP_CODE_MAP = {"Corn": 1, "Soybeans": 2, "Winter Wheat": 3, "Alfalfa": 4}
cdl["crop_num"] = cdl["crop_name"].map(CROP_CODE_MAP)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, gid in zip(axes, grower_order):
    sub = cdl[cdl["grower_id"] == gid]
    pivot = sub.pivot_table(index="field_id", columns="year", values="crop_num", aggfunc="first")
    pivot = pivot.sort_index()
    pivot.index = [f"F{i+1}" for i in range(len(pivot))]

    cmap = plt.get_cmap("tab10", 4)
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0.5, vmax=4.5)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, rotation=45, fontsize=8)
    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=7)
    ax.set_title(GROWER_LABELS[gid], fontsize=10, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Field")

# colorbar legend
handles = [mpatches.Patch(color=plt.get_cmap("tab10", 4)(v/4), label=k)
           for k, v in CROP_CODE_MAP.items()]
fig.legend(handles=handles, title="Crop", loc="lower center", ncol=4,
           bbox_to_anchor=(0.5, -0.05))
fig.suptitle("Crop Rotation Pattern per Field-Year (CDL heatmap)", fontsize=12, fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_cdl_02_rotation_pattern.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved fig_cdl_02_rotation_pattern.png")

# ── COMPARISON: Field size vs CDL dominant percentage ─────────────────────────
# Asks: do larger fields have higher CDL purity (dominant pct)?
# Edge pixels dilute purity in smaller fields.
fig, ax = plt.subplots(figsize=(9, 6))
for gid, grp in cdl.groupby("grower_id"):
    ax.scatter(grp["acres"], grp["dominant_pct"],
               color=GROWER_COLORS[gid], label=GROWER_LABELS[gid],
               s=28, alpha=0.55, edgecolors="none")
    slope, intercept, r, p, _ = stats.linregress(grp["acres"], grp["dominant_pct"])
    x_range = np.linspace(grp["acres"].min(), grp["acres"].max(), 100)
    ax.plot(x_range, slope * x_range + intercept, color=GROWER_COLORS[gid],
            linestyle="--", linewidth=1.5, alpha=0.9)
    pstr = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
    yoffset = {"IL001": 0, "IA001": -0.022, "NE001": -0.044}
    ax.annotate(f"{GROWER_LABELS[gid]}: r={r:.2f}, {pstr}",
                xy=(0.02, 0.10 + yoffset[gid]), xycoords="axes fraction",
                fontsize=8.5, color=GROWER_COLORS[gid], fontweight="bold")

ax.set_xlabel("Field Size (acres)")
ax.set_ylabel("CDL Dominant Crop Pixel Fraction")
ax.set_title("Field Size vs. CDL Dominant Crop Percentage\n(All field-year observations)", fontsize=12, fontweight="bold")
ax.legend(title="Grower")
ax.grid(alpha=0.3)
sns.despine()
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_cdl_03_size_dominance_corr.png"), dpi=150)
plt.close()
print("Saved fig_cdl_03_size_dominance_corr.png")
print("\nCDL EDA complete.")
