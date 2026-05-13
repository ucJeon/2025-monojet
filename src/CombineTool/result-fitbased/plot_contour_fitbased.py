#!/usr/bin/env python3
"""
plot_contour_fitbased.py
-------------------------
Base physics : plot_contour-xsfit.py
  - xs analytic formula  A × lam1² × lam2² / (4 lam1² + lam2²)
  - A fitted per MX1 from cross_section_SG.csv
  - eff interpolated from efficiency.csv via RectBivariateSpline
  - N_exc = r_median × rate_sig_ref  (from results-xsfit.csv)
  - signal_yield(lam1,lam2) = xs × lumi × 1000 × eff

Plot style : step2_plot-expected-contour.py
  - all 4 MX1 on one figure, per-MX1 color
  - hadronization regions
  - CMS style, (7,7) figure, identical axis/legend/lumi-text format
  - log-scale  AND  linear-scale versions

Output:
  result-fitbased/plots/
    contour_lumi{L}_{mode}_log.pdf
    contour_lumi{L}_{mode}_lin.pdf

λ_crit printed to stdout after each lumi×mode combination.
"""

import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.interpolate import RectBivariateSpline, interp1d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
import mplhep as hep

hep.style.use("CMS")

# ============================================================
#  PATHS
# ============================================================
SRC      = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src"
HERE     = os.path.dirname(os.path.abspath(__file__))
PATH_XS  = f"{SRC}/23.XS-2Dplot/cross_section_SG.csv"
PATH_EFF = f"{SRC}/Efficiency-signal/efficiency.csv"
PATH_RES = os.path.join(HERE, "..", "results-xsfit.csv")
PLOTDIR  = os.path.join(HERE, "plots")
os.makedirs(PLOTDIR, exist_ok=True)

# ============================================================
#  PHYSICS CONFIG  (from plot_contour-xsfit.py)
# ============================================================
OPTIMAL_CUTS = {1.0: 0.105, 1.5: 0.135, 2.0: 0.144, 2.5: 0.152}
MODEL        = "v2_2500_4"
B_FIXED      = 4.0
GRID_FIT     = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

LUMI_LIST = [300, 3000]
MX1_LIST  = [1.0, 1.5, 2.0, 2.5]

MODES_ALL = [
    ("none",  "No uncertainty"),
    ("stats", "BKG stat only"),
    ("sys1",  "stats + XSEC (10%)"),
    ("sys2",  "stats + XSEC + JES (5%)"),
    ("sys3",  "stats + XSEC + JES + MET (4%)"),
]

MEDIAN_KEY = "N_exc_exp_med"
QUANTILE_BANDS = [
    ("N_exc_exp_m2s", "N_exc_exp_p2s"),  # ±2σ
    ("N_exc_exp_m1s", "N_exc_exp_p1s"),  # ±1σ
]

# dense grid for contour drawing (λ1, λ2)
L1_GRID = np.linspace(0.01, 1.0, 500) # 0.03
L2_GRID = np.linspace(0.01, 1.0, 500) # 0.04

# fine 1D scan for λ_crit
LAM1_SCAN = np.linspace(0.01, 1.0, 4000)
LAM2_SCAN = np.linspace(0.01, 1.0, 4000)
LAM1_REF  = 0.50   # fixed when scanning λ2_crit
LAM2_REF  = 0.50   # fixed when scanning λ1_crit

# ============================================================
#  PLOT STYLE CONFIG  (from step2_plot-expected-contour.py)
# ============================================================
MX1_LABELS = {1.0: "1.0", 1.5: "1.5", 2.0: "2.0", 2.5: "2.5"}
COLOR_MAP  = {
    1.0: "cornflowerblue",
    1.5: "goldenrod",
    2.0: "coral",
    2.5: "#8B0000",
}

X_TICKS   = [0.1, 0.3, 0.5, 0.7, 1.0]
Y_TICKS   = [0.1, 0.3, 0.5, 0.7, 1.0]
#X_LIM_LOG = (0.03, 1.0)
X_LIM_LOG = (0.02, 1.0)
#Y_LIM_LOG = (0.04, 1.0)
Y_LIM_LOG = (0.04, 1.0)
#X_LIM_LIN = (0.03, 1.0)
X_LIM_LIN = (0.02, 1.0)
#Y_LIM_LIN = (0.04, 1.0)
Y_LIM_LIN = (0.04, 1.0)
LUMI_POS  = (0.98, 1.01)    # axes-fraction coords for lumi text
DPI       = 300

# Hadronization invalid regions  (from step2_plot-expected-contour.py — exact same values)
HAD_REGIONS = {
    1.0: {"lam1_min": 0.05,  "lam2_min": 0.07,  "show": True,
          "color": "#C7C7C7", "solid": True},    # light-gray solid fill
    1.5: {"lam1_min": 0.040, "lam2_min": 0.057, "show": True,
          "color": "#616161", "solid": False},   # dark-gray hatch
}


# ============================================================
#  PHYSICS — xs analytic + efficiency interpolation
#  (verbatim from plot_contour-xsfit.py)
# ============================================================

def _xs_model(X, A):
    l1, l2 = X
    return A * (l1**2 * l2**2) / (B_FIXED * l1**2 + l2**2)


def fit_A_per_mx1(df_xs: pd.DataFrame) -> dict:
    """Iterative outlier-robust A fit per MX1."""
    THRESH = 0.10
    A_map  = {}
    for mx1, grp in df_xs.groupby("mx1"):
        df_cur  = grp[grp["lam1"].isin(GRID_FIT) & grp["lam2"].isin(GRID_FIT)].copy().reset_index(drop=True)
        removed = []
        for _ in range(50):
            keep = [i for i, r in df_cur.iterrows()
                    if not any(np.isclose(r["lam1"], l1) and np.isclose(r["lam2"], l2)
                               for l1, l2 in removed)]
            df_it  = df_cur.loc[keep]
            x1, x2 = df_it["lam1"].to_numpy(float), df_it["lam2"].to_numpy(float)
            z,  ze  = df_it["xs"].to_numpy(float),   df_it["xs_err"].to_numpy(float)
            ze = np.where(ze <= 0, np.maximum(1e-12, 0.05 * np.abs(z)), ze)
            popt, _ = curve_fit(_xs_model, (x1, x2), z, p0=[z.max()],
                                sigma=ze, absolute_sigma=True)
            A_opt  = float(popt[0])
            pred   = _xs_model((x1, x2), A_opt)
            reldev = np.abs(z - pred) / z
            if reldev.max() <= THRESH:
                break
            worst = reldev.argmax()
            removed.append((x1[worst], x2[worst]))
        A_map[mx1] = A_opt
        print(f"  mx1={mx1}: A={A_opt:.5g}  (removed {len(removed)} pts)")
    return A_map


def build_eff_interpolators(df_eff: pd.DataFrame) -> dict:
    """Build RectBivariateSpline per MX1 at its optimal BDT cut."""
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


def _sig_grid(mx1: float, lumi: int, A: float, eff_sp) -> np.ndarray:
    """
    Signal yield on meshgrid(L1_GRID, L2_GRID).
    Shape (len(L2_GRID), len(L1_GRID)) — rows→λ2, cols→λ1.
    """
    L1, L2   = np.meshgrid(L1_GRID, L2_GRID)
    xs_grid  = _xs_model((L1, L2), A)
    eff_grid = np.clip(eff_sp(L1_GRID, L2_GRID).T, 0, 1)   # .T: rows→λ2, cols→λ1
    return xs_grid * lumi * 1000 * eff_grid


# ============================================================
#  λ_CRIT  —  1D crossing via fine scan + linear interpolation
# ============================================================

def _sig_1d(mx1: float, lumi: int, A: float, eff_sp,
            scan_arr: np.ndarray, fixed_name: str, fixed_val: float) -> np.ndarray:
    """Signal yield array along one λ axis at a fixed counterpart."""
    if fixed_name == "lam2":                # scan λ1, fix λ2
        l1, l2 = scan_arr, np.full_like(scan_arr, fixed_val)
    else:                                   # scan λ2, fix λ1
        l1, l2 = np.full_like(scan_arr, fixed_val), scan_arr
    xs_arr  = _xs_model((l1, l2), A)
    eff_arr = np.clip(eff_sp.ev(l1, l2), 0, 1)
    return xs_arr * lumi * 1000 * eff_arr


def find_lam_crit(scan_arr: np.ndarray, sig_arr: np.ndarray, n_exc: float):
    """Linear interpolation of the crossing point sig_arr == n_exc."""
    if n_exc < sig_arr.min():
        return f"<{scan_arr[0]:.3f}"
    if n_exc > sig_arr.max():
        return f">{scan_arr[-1]:.3f}"
    try:
        return float(interp1d(sig_arr, scan_arr, kind="linear")(n_exc))
    except Exception:
        return None


def _fmt_lam(v) -> str:
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def compute_and_print_lam_crit(mx1: float, lumi: int, mode: str,
                                A: float, eff_sp, n_exc_med: float,
                                n_exc_m1s: float = None, n_exc_p1s: float = None) -> dict:
    """
    Compute λ1_crit (fixed λ2=LAM2_REF) and λ2_crit (fixed λ1=LAM1_REF)
    for median and optionally ±1σ.  Returns dict of results.
    """
    s1_scan = _sig_1d(mx1, lumi, A, eff_sp, LAM1_SCAN, "lam2", LAM2_REF)
    s2_scan = _sig_1d(mx1, lumi, A, eff_sp, LAM2_SCAN, "lam1", LAM1_REF)

    result = {
        "lam1_crit_med": find_lam_crit(LAM1_SCAN, s1_scan, n_exc_med),
        "lam2_crit_med": find_lam_crit(LAM2_SCAN, s2_scan, n_exc_med),
    }
    if n_exc_m1s is not None:
        result["lam2_crit_m1s"] = find_lam_crit(LAM2_SCAN, s2_scan, n_exc_m1s)
    if n_exc_p1s is not None:
        result["lam2_crit_p1s"] = find_lam_crit(LAM2_SCAN, s2_scan, n_exc_p1s)
    return result


# ============================================================
#  STYLE HELPERS  (verbatim from step2_plot-expected-contour.py)
# ============================================================

def _style_axes(ax, log_scale: bool) -> None:
    ax.set_xlabel(r"$\lambda_{1}$", fontsize=16, labelpad=10)
    ax.set_ylabel(r"$\lambda_{2}$", fontsize=16, labelpad=10)
    ax.tick_params(axis="both", which="major", labelsize=13)
    ax.set_xticks(X_TICKS)
    ax.set_yticks(Y_TICKS)
    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*X_LIM_LOG)
        ax.set_ylim(*Y_LIM_LOG)
        formatter = ticker.FormatStrFormatter("%.1f")
        ax.get_xaxis().set_major_formatter(formatter)
        ax.get_yaxis().set_major_formatter(formatter)
        ax.get_xaxis().set_minor_formatter(ticker.NullFormatter())
        ax.get_yaxis().set_minor_formatter(ticker.NullFormatter())
    else:
        ax.set_xlim(*X_LIM_LIN)
        ax.set_ylim(*Y_LIM_LIN)


def _draw_hadronization(ax) -> list:
    """
    Draw hadronization-invalid polygons.
    Returns legend entries [(patch, label), ...].
    """
    _INF = 5.0
    legend_entries = []
    for mx1, cfg in HAD_REGIONS.items():
        if not cfg["show"]:
            continue
        hx, hy = cfg["lam1_min"], cfg["lam2_min"]
        verts = [(0, 0), (_INF, 0), (_INF, hy), (hx, hy), (hx, _INF), (0, _INF)]
        if cfg["solid"]:
            poly = mpatches.Polygon(
                verts, closed=True,
                facecolor=cfg["color"], edgecolor="none",
                alpha=0.5, hatch="", linewidth=0, zorder=1,
            )
            leg_patch = mpatches.Patch(
                facecolor=cfg["color"], edgecolor="none", alpha=0.5,
            )
        else:
            poly = mpatches.Polygon(
                verts, closed=True,
                facecolor="none", edgecolor=cfg["color"],
                alpha=0.5, hatch="///", linewidth=0, zorder=1,
            )
            leg_patch = mpatches.Patch(
                facecolor="none", hatch="///", edgecolor=cfg["color"], alpha=0.6,
            )
        ax.add_patch(poly)
        legend_entries.append(
            (leg_patch, rf"$m_{{X_1}} = {MX1_LABELS[mx1]}$ TeV")
        )
    return legend_entries


# ============================================================
#  COMBINED CONTOUR PLOT  — all MX1 on one figure
# ============================================================

def make_combined_plot(lumi: int, mode: str,
                       df_res: pd.DataFrame,
                       A_map: dict, eff_interp: dict,
                       log_scale: bool) -> tuple:
    """
    Returns (fig, lam_crit_rows) where lam_crit_rows is a list of dicts
    for the λ_crit table.
    """
    L1, L2 = np.meshgrid(L1_GRID, L2_GRID)

    fig, ax = plt.subplots(figsize=(7, 7))

    # ── 1. hadronization regions (step2 style) ──────────────────────
    had_entries = _draw_hadronization(ax)

    # ── 2. contour per MX1 ──────────────────────────────────────────
    proxy_lines  = []
    mass_labels  = []
    lam_crit_rows = []

    for mx1 in MX1_LIST:
        row = df_res[(df_res["mx1"]  == mx1) &
                     (df_res["lumi"] == lumi) &
                     (df_res["mode"] == mode)]
        if row.empty:
            print(f"  [SKIP] mx1={mx1} lumi={lumi} mode={mode}")
            continue

        row    = row.iloc[0]
        A      = A_map[mx1]
        sp     = eff_interp[mx1]
        n_med  = float(row[MEDIAN_KEY])
        n_m1s  = float(row["N_exc_exp_m1s"])
        n_p1s  = float(row["N_exc_exp_p1s"])
        color  = COLOR_MAP[mx1]

        sig_grid = _sig_grid(mx1, lumi, A, sp)

        try:
            cs = ax.contour(L1, L2, sig_grid, levels=[n_med],
                            colors=[color], linewidths=2.0, linestyles="-", zorder=3)
            proxy_lines.append(Line2D([0], [0], color=color, lw=2.0, ls="-"))
            mass_labels.append(rf"$m_{{X_1}}$ = {MX1_LABELS[mx1]} TeV")
        except Exception as e:
            print(f"  [WARN] contour mx1={mx1}: {e}")
            continue

        # λ_crit for this point
        crit = compute_and_print_lam_crit(mx1, lumi, mode, A, sp,
                                          n_med, n_m1s, n_p1s)
        lam_crit_rows.append({
            "mx1": mx1, "lumi": lumi, "mode": mode,
            "N_exc_med": n_med, "N_exc_m1s": n_m1s, "N_exc_p1s": n_p1s,
            **crit,
        })

    # ── 3. legend (step2 style) ──────────────────────────────────────
    title_h = Line2D([0], [0], color="none")
    had_h   = Line2D([0], [0], color="none")

    all_handles = ([title_h] + proxy_lines +
                   [Line2D([0], [0], color="none")] +
                   [had_h] + [h for h, _ in had_entries])
    all_labels  = ([r"$\mathbf{Median\ Expected\ 95\%\ CL}$"] + mass_labels +
                   [""] +
                   [r"$\mathbf{Hadronization\ Region}$"] + [lbl for _, lbl in had_entries])

    leg = ax.legend(
        all_handles, all_labels,
        frameon=False, loc="upper right",
        bbox_to_anchor=(0.999, 0.999),
        fontsize=11, labelspacing=0.3,
        handletextpad=0.5, borderpad=1.0, handlelength=1.0,
    )
    for text in leg.get_texts():
        if "Median Expected" in text.get_text() or "Hadronization Region" in text.get_text():
            text.set_position((-100, 0))
            text.set_ha("left")

    # ── 4. axis style (step2 style) ──────────────────────────────────
    _style_axes(ax, log_scale)

    # ── 5. lumi text (step2 style, exact position and format) ────────
    ax.text(
        LUMI_POS[0], LUMI_POS[1],
        rf"{lumi} fb$^{{-1}}$ (13 TeV)",
        transform=ax.transAxes, fontsize=14, ha="right", fontweight="bold",
    )

    # hep.cms.label("Preliminary", data=False, ax=ax, fontsize=14, loc=0)
    plt.tight_layout()
    return fig, lam_crit_rows


# ============================================================
#  λ_CRIT TABLE  —  stdout print
# ============================================================

def print_lam_crit_table(rows: list, lumi: int, mode: str) -> None:
    print(f"\n  {'─'*62}")
    print(f"  λ_crit  |  lumi={lumi} fb⁻¹  |  mode={mode}")
    print(f"  Fixed λ2={LAM2_REF} → λ1_crit  |  Fixed λ1={LAM1_REF} → λ2_crit")
    print(f"  {'─'*62}")
    print(f"  {'mx1':>5}  {'λ1_crit (med)':>16}  {'λ2_crit (med)':>16}  "
          f"{'λ2_crit (-1σ)':>16}  {'λ2_crit (+1σ)':>16}")
    print(f"  {'─'*62}")
    for r in rows:
        print(f"  {r['mx1']:>5.1f}  "
              f"{_fmt_lam(r.get('lam1_crit_med')):>16}  "
              f"{_fmt_lam(r.get('lam2_crit_med')):>16}  "
              f"{_fmt_lam(r.get('lam2_crit_m1s')):>16}  "
              f"{_fmt_lam(r.get('lam2_crit_p1s')):>16}")


# ============================================================
#  MAIN
# ============================================================

def main():
    print("Loading data …")
    df_xs  = pd.read_csv(PATH_XS)
    df_eff = pd.read_csv(PATH_EFF)
    df_res = pd.read_csv(PATH_RES)

    print("=== Fitting A per MX1 ===")
    A_map = fit_A_per_mx1(df_xs)

    print("\n=== Building efficiency interpolators ===")
    eff_interp = build_eff_interpolators(df_eff)

    print("\n=== Drawing contours ===")
    all_crit_rows = []

    for lumi in LUMI_LIST:
        for mode, _ in MODES_ALL:
            crit_rows_lumi_mode = []
            for log_scale in [True, False]:
                scale_tag = "log" if log_scale else "lin"
                fig, crit_rows = make_combined_plot(
                    lumi, mode, df_res, A_map, eff_interp, log_scale
                )
                fname = f"contour_lumi{lumi}_{mode}_{scale_tag}.png"
                fig.savefig(os.path.join(PLOTDIR, fname), bbox_inches="tight", dpi=DPI)
                plt.close(fig)
                print(f"  saved: {fname}")

                if log_scale:
                    crit_rows_lumi_mode = crit_rows   # same physics, print once

            print_lam_crit_table(crit_rows_lumi_mode, lumi, mode)
            all_crit_rows.extend(crit_rows_lumi_mode)

    # Save λ_crit summary to CSV for easy reference
    if all_crit_rows:
        df_crit = pd.DataFrame(all_crit_rows)
        crit_path = os.path.join(HERE, "lam_crit_summary.csv")
        df_crit.to_csv(crit_path, index=False, float_format="%.4f")
        print(f"\nλ_crit saved: {crit_path}")

    print(f"\nAll plots → {PLOTDIR}/")


if __name__ == "__main__":
    main()
