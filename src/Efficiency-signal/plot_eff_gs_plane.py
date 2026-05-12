import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

BDT_CUT = 0.0   # change as needed
MODEL   = "v2_2500_4"

df = pd.read_csv("efficiency.csv")
df = df[(df["model"] == MODEL) & (df["bdt_cut"] == BDT_CUT)]

mx1_vals = sorted(df["mx1"].unique())
ncols = len(mx1_vals)

fig, axes = plt.subplots(1, ncols, figsize=(4.5 * ncols, 4.2), constrained_layout=True)
if ncols == 1:
    axes = [axes]

vmin, vmax = df["eff_gs"].min(), df["eff_gs"].max()
norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
cmap = "viridis"

for ax, mx1 in zip(axes, mx1_vals):
    sub = df[df["mx1"] == mx1]
    pivot = sub.pivot(index="lam1", columns="lam2", values="eff_gs")

    lam2 = pivot.columns.values
    lam1 = pivot.index.values
    Z = pivot.values

    im = ax.pcolormesh(lam2, lam1, Z, cmap=cmap, norm=norm, shading="auto")
    ax.set_title(f"$m_{{X_1}}$ = {mx1} TeV", fontsize=12)
    ax.set_xlabel(r"$\lambda_2$")
    ax.set_ylabel(r"$\lambda_1$")
    #ax.set_xscale("log")
    #ax.set_yscale("log")

fig.colorbar(im, ax=axes, label=r"$\varepsilon_\mathrm{gs}$ ($N_\mathrm{BDT}/N_\mathrm{gen}$)",
             fraction=0.03, pad=0.04)
fig.suptitle(f"Signal efficiency — {MODEL}, BDT cut = {BDT_CUT}", fontsize=13)

plt.savefig("eff_gs_plane.png", dpi=150)
print("Saved eff_gs_plane.png")
