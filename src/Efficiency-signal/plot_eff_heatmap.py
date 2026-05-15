"""
plot_eff_heatmap.py

Produces one PNG with 3 rows × 4 columns = 12 heatmaps.
Each mx1 column uses its own optimal BDT cut:
  mx1=1.0 → 0.1050,  mx1=1.5 → 0.1350,
  mx1=2.0 → 0.1440,  mx1=2.5 → 0.1520
  lam1 → columns (x-axis),  lam2 → rows (y-axis)
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# ── paths ─────────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), "efficiency.csv")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(OUT_DIR, exist_ok=True)

# ── parameters ────────────────────────────────────────────────────────────────
MODEL = "v2_2500_4"

# optimal BDT cut per mass point
MX1_CUT = {
    1.0: 0.1050,
    1.5: 0.1350,
    2.0: 0.1440,
    2.5: 0.1520,
}
MX1_VALS = [1.0, 1.5, 2.0, 2.5]

EFF_COLS = [
    ("eff_gs", r"$\varepsilon_\mathrm{sel}$  ( $N_\mathrm{sel}$ / $N_\mathrm{gen}$ )"),
    ("eff_sb", r"$\varepsilon_\mathrm{BDT}$  ( $N_\mathrm{BDT}$ / $N_\mathrm{sel}$ )"),
    ("eff_gb", r"$\varepsilon_\mathrm{tot}$  ( $N_\mathrm{BDT}$ / $N_\mathrm{gen}$ )"),
]

# ── load data ─────────────────────────────────────────────────────────────────
df_all = pd.read_csv(CSV_PATH)
df_all = df_all[df_all["model"] == MODEL]

# ── helpers ───────────────────────────────────────────────────────────────────
def draw_heatmap(ax, pivot, vmin, vmax, cmap, annot_fmt=".3f"):
    sns.heatmap(
        pivot,
        ax=ax,
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
        annot=True,
        fmt=annot_fmt,
        annot_kws={"size": 5.5},
        linewidths=0.3,
        linecolor="#cccccc",
        cbar=False,
    )
    ax.set_facecolor("white")
    ax.set_xlabel(r"$\lambda_1$", fontsize=16)
    ax.set_ylabel(r"$\lambda_2$", fontsize=16)
    ax.tick_params(axis="both", labelsize=10)


# ── main ──────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(
    nrows=3, ncols=4,
    figsize=(22, 14),
    facecolor="white",
)
fig.suptitle(
    f"Signal efficiency — {MODEL}  "
    r"[$m_{X_1}$-optimal BDT cuts: "
    "1.0 TeV→0.1050, 1.5 TeV→0.1350, 2.0 TeV→0.1440, 2.5 TeV→0.1520]",
    fontsize=11, y=0.999,
)

for row_idx, (eff_col, eff_label) in enumerate(EFF_COLS):
    # shared colour scale: pool all rows from each mx1's own cut
    pooled = pd.concat([
        df_all[(df_all["mx1"] == mx1) & np.isclose(df_all["bdt_cut"], MX1_CUT[mx1])]
        for mx1 in MX1_VALS
    ])
    vmin = pooled[eff_col].min()
    vmax = pooled[eff_col].max()
    cmap = "Blues"

    for col_idx, mx1 in enumerate(MX1_VALS):
        bdt_cut = MX1_CUT[mx1]
        ax = axes[row_idx][col_idx]
        sub = df_all[(df_all["mx1"] == mx1) & np.isclose(df_all["bdt_cut"], bdt_cut)]

        pivot = sub.pivot(index="lam2", columns="lam1", values=eff_col)
        pivot = pivot.sort_index(ascending=False)
        pivot = pivot[sorted(pivot.columns)]

        draw_heatmap(ax, pivot, vmin=vmin, vmax=vmax, cmap=cmap)

        cut_str = f"cut={bdt_cut:.4f}"
        title = f"$m_{{X_1}}$ = {mx1} TeV  ({cut_str})"
        if col_idx == 0:
            title = f"{eff_label}\n{title}"
        ax.set_title(title, fontsize=8, pad=3)

plt.tight_layout(rect=[0, 0, 1, 0.997])

fname = os.path.join(OUT_DIR, "eff_heatmap_optimal_cut.png")
fig.savefig(fname, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {fname}")
