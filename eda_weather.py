"""
EDA Category 2: Weather
Outputs:
  fig_wx_01_annual_precip.png    – VIZ 1: Annual precipitation by grower (box/strip)
  fig_wx_02_gdd_trend.png        – VIZ 2: Annual GDD trend 2020-2024 by grower
  fig_wx_03_precip_gdd_corr.png  – COMPARISON: Correlation between annual precip and GDD
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

wfy = pd.read_csv(os.path.join(RUNTIME, "weather_field_year.csv"))
wfy["grower_label"] = wfy["grower_id"].map(GROWER_LABELS)

# ── VIZ 1: Annual precipitation distribution by grower ──────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
order = ["IL001", "IA001", "NE001"]
positions = {gid: i for i, gid in enumerate(order)}

for gid, grp in wfy.groupby("grower_id"):
    x_pos = positions[gid]
    # box
    bp = ax.boxplot(grp["ann_precip_mm"], positions=[x_pos], widths=0.4,
                    patch_artist=True,
                    boxprops=dict(facecolor=GROWER_COLORS[gid], alpha=0.6),
                    medianprops=dict(color="white", linewidth=2),
                    whiskerprops=dict(color=GROWER_COLORS[gid]),
                    capprops=dict(color=GROWER_COLORS[gid]),
                    flierprops=dict(marker="o", markerfacecolor=GROWER_COLORS[gid], markersize=4))
    # strip points
    jitter = np.random.uniform(-0.12, 0.12, len(grp))
    ax.scatter(np.full(len(grp), x_pos) + jitter, grp["ann_precip_mm"],
               color=GROWER_COLORS[gid], s=28, alpha=0.7, zorder=3, edgecolors="white", linewidth=0.4)

ax.set_xticks(range(3))
ax.set_xticklabels([GROWER_LABELS[g] for g in order])
ax.set_ylabel("Annual Precipitation (mm)")
ax.set_title("Annual Precipitation Distribution by Grower (2020–2024,\nall fields)", fontsize=12, fontweight="bold")
ax.axhline(y=800, color="gray", linestyle=":", linewidth=1, label="800 mm reference")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
sns.despine()
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_wx_01_annual_precip.png"), dpi=150)
plt.close()
print("Saved fig_wx_01_annual_precip.png")

# ── VIZ 2: Annual GDD trend 2020-2024 by grower (mean ± 1 SD across fields) ─
gdd_trend = (wfy.groupby(["grower_id", "year"])
             .agg(mean_gdd=("ann_gdd_c", "mean"), sd_gdd=("ann_gdd_c", "std"))
             .reset_index())
gdd_trend["grower_label"] = gdd_trend["grower_id"].map(GROWER_LABELS)

fig, ax = plt.subplots(figsize=(9, 5))
for gid, grp in gdd_trend.groupby("grower_id"):
    grp = grp.sort_values("year")
    ax.plot(grp["year"], grp["mean_gdd"], marker="o", color=GROWER_COLORS[gid],
            label=GROWER_LABELS[gid], linewidth=2, markersize=7)
    ax.fill_between(grp["year"],
                    grp["mean_gdd"] - grp["sd_gdd"],
                    grp["mean_gdd"] + grp["sd_gdd"],
                    color=GROWER_COLORS[gid], alpha=0.15)

ax.set_xticks(range(2020, 2025))
ax.set_xlabel("Year")
ax.set_ylabel("Annual GDD (base 10 °C)")
ax.set_title("Annual Growing Degree Days Trend by Grower (2020–2024)\nMean ± 1 SD across 10 fields", fontsize=12, fontweight="bold")
ax.legend(title="Grower")
ax.grid(alpha=0.3)
sns.despine()
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_wx_02_gdd_trend.png"), dpi=150)
plt.close()
print("Saved fig_wx_02_gdd_trend.png")

# ── COMPARISON: Correlation – annual precip vs annual GDD per field-year ────
fig, ax = plt.subplots(figsize=(9, 6))
for gid, grp in wfy.groupby("grower_id"):
    ax.scatter(grp["ann_precip_mm"], grp["ann_gdd_c"],
               color=GROWER_COLORS[gid], label=GROWER_LABELS[gid],
               s=55, alpha=0.75, edgecolors="white", linewidth=0.5)
    # regression line
    slope, intercept, r, p, _ = stats.linregress(grp["ann_precip_mm"], grp["ann_gdd_c"])
    x_range = np.linspace(grp["ann_precip_mm"].min(), grp["ann_precip_mm"].max(), 100)
    ax.plot(x_range, slope * x_range + intercept, color=GROWER_COLORS[gid],
            linestyle="--", linewidth=1.2, alpha=0.8)
    # annotate r and p
    yoffset = {"IL001": -0.06, "IA001": -0.13, "NE001": -0.20}
    pstr = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
    ax.annotate(f"{GROWER_LABELS[gid]}: r={r:.2f}, {pstr}",
                xy=(0.02, 0.96 + yoffset[gid]), xycoords="axes fraction",
                fontsize=8.5, color=GROWER_COLORS[gid], fontweight="bold")

ax.set_xlabel("Annual Precipitation (mm)")
ax.set_ylabel("Annual GDD (base 10 °C)")
ax.set_title("Annual Precipitation vs. GDD Correlation\n(field-year observations, all three growers)", fontsize=12, fontweight="bold")
ax.legend(title="Grower")
ax.grid(alpha=0.3)
sns.despine()
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "fig_wx_03_precip_gdd_corr.png"), dpi=150)
plt.close()
print("Saved fig_wx_03_precip_gdd_corr.png")
print("\nWeather EDA complete.")
