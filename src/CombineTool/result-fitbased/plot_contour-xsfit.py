"""
plot_contour-xsfit.py  — Denis 방식 XS-fit exclusion contour

흐름:
  1. results-xsfit.csv 에서 N_exc (모든 quantile) 로드
  2. xs_analytic(lam1, lam2)  : A × lam1² × lam2² / (4 lam1² + lam2²)
     A는 cross_section_SG.csv 에서 iterative fit
  3. eff_interp(lam1, lam2)   : efficiency.csv 에서 RectBivariateSpline
  4. signal_yield = xs × lumi × 1000 × eff
  5. contour at signal_yield = N_exc_{quantile}
  6. plots-xsfit/ 에 PDF 저장

주의: analytic 공식은 MX1≥2.0 에서 ~10% 이상 편차 존재 (인지된 한계)
"""

import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.interpolate import RectBivariateSpline
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

SRC      = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src"
HERE     = os.path.dirname(__file__)
PATH_XS  = f"{SRC}/23.XS-2Dplot/cross_section_SG.csv"
PATH_EFF = f"{SRC}/Efficiency-signal/efficiency.csv"
PATH_RES = os.path.join(HERE, "results-xsfit.csv")
PLOTDIR  = os.path.join(HERE, "plots-xsfit")

OPTIMAL_CUTS = {1.0: 0.105, 1.5: 0.135, 2.0: 0.144, 2.5: 0.152}
MODEL        = "v2_2500_4"
B_FIXED      = 4.0
GRID_FIT     = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
# NWA_MAX      = 0.8   # NWA validity line

os.makedirs(PLOTDIR, exist_ok=True)


# ── 1. xs analytic 공식 A 피팅 ─────────────────────────────────────────────
def _xs_model(X, A):
    l1, l2 = X
    return A * (l1**2 * l2**2) / (B_FIXED * l1**2 + l2**2)

def fit_A_per_mx1(df_xs):
    THRESH = 0.10
    A_map  = {}
    for mx1, grp in df_xs.groupby("mx1"):
        df_cur  = grp[grp["lam1"].isin(GRID_FIT) & grp["lam2"].isin(GRID_FIT)].copy().reset_index(drop=True)
        removed = []
        for _ in range(50):
            keep = [i for i, r in df_cur.iterrows()
                    if not any(np.isclose(r["lam1"], l1) and np.isclose(r["lam2"], l2)
                               for l1, l2 in removed)]
            df_it = df_cur.loc[keep]
            x1, x2 = df_it["lam1"].to_numpy(float), df_it["lam2"].to_numpy(float)
            z,  ze  = df_it["xs"].to_numpy(float),   df_it["xs_err"].to_numpy(float)
            ze = np.where(ze <= 0, np.maximum(1e-12, 0.05 * np.abs(z)), ze)
            popt, _ = curve_fit(_xs_model, (x1, x2), z, p0=[z.max()], sigma=ze, absolute_sigma=True)
            A_opt   = float(popt[0])
            pred    = _xs_model((x1, x2), A_opt)
            reldev  = np.abs(z - pred) / z
            if reldev.max() <= THRESH:
                break
            worst = reldev.argmax()
            removed.append((x1[worst], x2[worst]))
        A_map[mx1] = A_opt
        print(f"  mx1={mx1}: A={A_opt:.5g}  (removed {len(removed)} pts)")
    return A_map


# ── 2. efficiency 보간기 생성 ─────────────────────────────────────────────
def build_eff_interpolators(df_eff):
    interp = {}
    for mx1, cut in OPTIMAL_CUTS.items():
        sub = df_eff[(df_eff["mx1"] == mx1) &
                     (df_eff["model"] == MODEL) &
                     (df_eff["bdt_cut"] == cut) &
                     (df_eff["lam1"] < 1.5) &
                     (df_eff["lam2"] < 1.5)].copy()
        l1_vals = sorted(sub["lam1"].unique())
        l2_vals = sorted(sub["lam2"].unique())
        pivot   = sub.pivot(index="lam1", columns="lam2", values="eff_gb")
        pivot   = pivot.reindex(index=l1_vals, columns=l2_vals)
        Z       = pivot.to_numpy(dtype=float)
        interp[mx1] = RectBivariateSpline(l1_vals, l2_vals, Z, kx=3, ky=3)
    return interp


# ── 3. contour 플롯 ────────────────────────────────────────────────────────
QUANTILE_PAIRS = [
    ("N_exc_exp_m2s", "N_exc_exp_p2s", "#FFFF00", r"$\pm 2\sigma$"),
    ("N_exc_exp_m1s", "N_exc_exp_p1s", "#00FF00", r"$\pm 1\sigma$"),
]
MEDIAN_KEY = "N_exc_exp_med"

def plot_contour(mx1, lumi, mode, df_res, A_map, eff_interp):
    row = df_res[(df_res["mx1"] == mx1) &
                 (df_res["lumi"] == lumi) &
                 (df_res["mode"] == mode)]
    if row.empty:
        print(f"  [SKIP] mx1={mx1} lumi={lumi} mode={mode}: no result")
        return

    row = row.iloc[0]
    A   = A_map[mx1]

    # dense grid (NWA 유효 범위)
    # l1 = np.linspace(0.03, NWA_MAX, 400)
    l1 = np.linspace(0.03, 1.0, 400)
    # l2 = np.linspace(0.04, NWA_MAX, 400)
    l2 = np.linspace(0.04, 1.0, 400)
    L1, L2 = np.meshgrid(l1, l2)

    xs_grid  = _xs_model((L1, L2), A)
    eff_grid = eff_interp[mx1](l1, l2)          # shape (len_l1, len_l2)
    eff_grid = np.clip(eff_grid.T, 0, 1)        # transpose → (l2, l1)

    sig_yield = xs_grid * lumi * 1000 * eff_grid

    fig, ax = plt.subplots(figsize=(7, 6))

    # Brazil band (±2σ, ±1σ)
    for (k_lo, k_hi, color, label) in QUANTILE_PAIRS:
        ax.contourf(L1, L2, sig_yield,
                    levels=[row[k_lo], row[k_hi]],
                    colors=[color], alpha=0.4, zorder=2)

    # median expected contour
    N_med = row[MEDIAN_KEY]
    cs = ax.contour(L1, L2, sig_yield, levels=[N_med],
                    colors=["black"], linewidths=1.8, zorder=3)
    ax.clabel(cs, fmt=f"N_exc={N_med:.1f}", fontsize=8)

    # NWA validity line (λ_max = 0.8)
    # ax.axvline(NWA_MAX, color="gray", linestyle="--", linewidth=1, label=f"NWA max (λ={NWA_MAX})")
    # ax.axhline(NWA_MAX, color="gray", linestyle="--", linewidth=1)

    ax.set_xlabel(r"$\lambda_1$")
    ax.set_ylabel(r"$\lambda_2$")
    ax.set_title(
        f"Exclusion contour (XS-fit)  |  "
        f"$m_{{X_1}}$={mx1} TeV  |  L={lumi} fb$^{{-1}}$  |  {mode}",
        fontsize=11
    )

    # legend patches
    import matplotlib.patches as mpatches
    handles = [
        mpatches.Patch(color="#FFFF00", alpha=0.5, label=r"$\pm 2\sigma$ expected"),
        mpatches.Patch(color="#00FF00", alpha=0.5, label=r"$\pm 1\sigma$ expected"),
        plt.Line2D([0], [0], color="black", lw=1.8, label="Median expected"),
        # plt.Line2D([0], [0], color="gray", lw=1, ls="--", label=f"NWA λ={NWA_MAX}"),
    ]
    ax.legend(handles=handles, fontsize=9, loc="upper left")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend(handles=handles, fontsize=9, loc="upper left")

    # hep.cms.label("Preliminary", data=False, lumi=lumi, ax=ax)

    mx1_tag = str(mx1).replace(".", "-")
    fname   = f"contour_MX{mx1_tag}_lumi{lumi}_{mode}-xsfit.pdf"
    fig.savefig(os.path.join(PLOTDIR, fname), bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {fname}")


# ── main ──────────────────────────────────────────────────────────────────
def main():
    df_xs  = pd.read_csv(PATH_XS)
    df_eff = pd.read_csv(PATH_EFF)
    df_res = pd.read_csv(PATH_RES)

    print("=== Fitting A per MX1 ===")
    A_map = fit_A_per_mx1(df_xs)

    print("\n=== Building efficiency interpolators ===")
    eff_interp = build_eff_interpolators(df_eff)

    print("\n=== Drawing contours ===")
    for mx1 in [1.0, 1.5, 2.0, 2.5]:
        for lumi in [300, 3000]:
            for mode in ["none", "stats", "sys1", "sys2", "sys3"]:
                plot_contour(mx1, lumi, mode, df_res, A_map, eff_interp)

    print(f"\nAll plots → {PLOTDIR}/")

if __name__ == "__main__":
    main()
