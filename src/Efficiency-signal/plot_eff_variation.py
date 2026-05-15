import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

OPTIMAL_CUTS = {1.0: 0.105, 1.5: 0.135, 2.0: 0.144, 2.5: 0.152}
MODEL        = "v2_2500_4"
EFF_COLS     = ["eff_gb", "eff_gs", "eff_sb"]
EFF_LABELS   = {
    "eff_gb": r"$\varepsilon_\mathrm{sig}$ = $N_\mathrm{BDT}/N_\mathrm{gen}$",
    "eff_gs": r"$\varepsilon_\mathrm{sel}$ = $N_\mathrm{sel}/N_\mathrm{gen}$",
    "eff_sb": r"$\varepsilon_\mathrm{BDT}$ = $N_\mathrm{BDT}/N_\mathrm{sel}$",
}
os.makedirs("plots", exist_ok=True)

df = pd.read_csv("efficiency.csv")

print(f"\n{'MX1':>5}  {'cut':>6}  {'eff':>8}  {'mean':>8}  {'std':>8}  {'min':>8}  {'max':>8}  {'(max-min)/mean':>15}")
print("-" * 80)

for mx1, cut in OPTIMAL_CUTS.items():
    sub = df[(df.model == MODEL) & (df.mx1 == mx1) & (df.bdt_cut == cut)]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    fig.suptitle(f"$m_{{X_1}}$ = {mx1} TeV  |  {MODEL}  |  BDT cut = {cut}", fontsize=13)

    for ax, col in zip(axes, EFF_COLS):
        pivot = sub.pivot(index="lam1", columns="lam2", values=col)
        lam2  = pivot.columns.values
        lam1  = pivot.index.values
        Z     = pivot.values

        im = ax.pcolormesh(lam2, lam1, Z, cmap="viridis", shading="auto")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        mean = Z.mean()
        variation = (Z.max() - Z.min()) / mean * 100
        ax.set_title(f"{EFF_LABELS[col]}\nmean={mean:.3f}  Δ/mean={variation:.1f}%", fontsize=10)
        ax.set_xlabel(r"$\lambda_2$")
        ax.set_ylabel(r"$\lambda_1$")

        # stats to stdout
        print(f"{mx1:>5.1f}  {cut:>6.3f}  {col:>8}  "
              f"{mean:>8.4f}  {Z.std():>8.4f}  {Z.min():>8.4f}  {Z.max():>8.4f}  "
              f"{variation:>13.1f}%")

    out = f"plots/efficiency_map_MX1{str(mx1).replace('.', '-')}.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  → saved {out}")
    print()
