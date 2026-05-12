#!/usr/bin/env python3
"""
verify_grids.py  —  signal grid validation diagnostics

For each MX1, generates:
  [A] Per-MX1 3-panel figure
        Left  : log10(xs_analytic) heatmap  + actual xs data scatter
        Middle : eff_gb heatmap              + actual eff data scatter
        Right  : log10(sig_yield) heatmap    + N_exc median contour (lumi=300, mode=none)

  [B] xs residual figure (all 4 MX1)
        (xs_analytic - xs_data) / xs_data  scatter, colored by lam1 or lam2

Output: result-fitbased/verify/
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.colors import LogNorm

# ── import physics from main script ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_contour_fitbased import (
    _xs_model, fit_A_per_mx1, build_eff_interpolators, _sig_grid,
    PATH_XS, PATH_EFF, PATH_RES,
    L1_GRID, L2_GRID, MX1_LIST, OPTIMAL_CUTS, MODEL,
)

VERDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify")
os.makedirs(VERDIR, exist_ok=True)

LUMI_CHECK = 300   # lumi used for sig_grid panel
MODE_CHECK = "none"


# ── helpers ─────────────────────────────────────────────────────────────────

def _log_cmap_kwargs(Z, cmap="viridis"):
    Zpos = Z[Z > 0]
    vmin, vmax = Zpos.min(), Zpos.max()
    return dict(cmap=cmap, norm=LogNorm(vmin=vmin, vmax=vmax))


def _add_colorbar(fig, mappable, ax, label, shrink=0.85):
    cb = fig.colorbar(mappable, ax=ax, shrink=shrink, pad=0.02)
    cb.set_label(label, fontsize=10)
    return cb


# ── [A] per-MX1 three-panel heatmap ─────────────────────────────────────────

def plot_grid_panels(mx1: float, A: float, eff_sp, df_xs: pd.DataFrame,
                     df_eff: pd.DataFrame, df_res: pd.DataFrame) -> None:
    L1, L2 = np.meshgrid(L1_GRID, L2_GRID)

    # --- compute grids ---
    xs_grid  = _xs_model((L1, L2), A)                           # analytic xs

    eff_raw  = eff_sp(L1_GRID, L2_GRID)                        # shape (l1, l2)
    eff_grid = np.clip(eff_raw.T, 0, 1)                        # (l2, l1)

    sig_grid = xs_grid * LUMI_CHECK * 1000 * eff_grid

    # --- actual data points ---
    xs_data = df_xs[df_xs["mx1"] == mx1].copy()

    cut = OPTIMAL_CUTS[mx1]
    eff_data = df_eff[(df_eff["mx1"] == mx1) &
                      (df_eff["model"] == MODEL) &
                      (df_eff["bdt_cut"] == cut)].copy()

    # N_exc for contour overlay
    row_res = df_res[(df_res["mx1"]  == mx1) &
                     (df_res["lumi"] == LUMI_CHECK) &
                     (df_res["mode"] == MODE_CHECK)]
    n_exc = float(row_res.iloc[0]["N_exc_exp_med"]) if not row_res.empty else None

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle(rf"Grid validation  |  $m_{{X_1}}$ = {mx1} TeV", fontsize=14)

    # ── panel 1 : xs_analytic heatmap ────────────────────────────────
    ax = axes[0]
    kw = _log_cmap_kwargs(xs_grid)
    pm = ax.pcolormesh(L1, L2, xs_grid, shading="auto", **kw)
    _add_colorbar(fig, pm, ax, r"$\sigma$ [pb]")

    # overlay actual data (scatter, same log colorscale)
    sc = ax.scatter(xs_data["lam1"], xs_data["lam2"],
                    c=xs_data["xs"], s=18, edgecolors="white", linewidths=0.4,
                    norm=kw["norm"], cmap=kw["cmap"], zorder=5)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"$\lambda_1$"); ax.set_ylabel(r"$\lambda_2$")
    ax.set_title(r"xs analytic (heatmap) vs data (dots)")

    # ── panel 2 : eff_gb heatmap ─────────────────────────────────────
    ax = axes[1]
    pm2 = ax.pcolormesh(L1, L2, eff_grid, shading="auto",
                        cmap="plasma", vmin=0, vmax=eff_grid.max())
    _add_colorbar(fig, pm2, ax, r"$\varepsilon_{gb}$")

    sc2 = ax.scatter(eff_data["lam1"], eff_data["lam2"],
                     c=eff_data["eff_gb"], s=18, edgecolors="white", linewidths=0.4,
                     cmap="plasma", vmin=0, vmax=eff_grid.max(), zorder=5)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"$\lambda_1$"); ax.set_ylabel(r"$\lambda_2$")
    ax.set_title(rf"Efficiency (BDT cut={cut})")

    # ── panel 3 : sig_yield heatmap + N_exc contour ───────────────────
    ax = axes[2]
    kw3 = _log_cmap_kwargs(sig_grid, cmap="inferno")
    pm3 = ax.pcolormesh(L1, L2, sig_grid, shading="auto", **kw3)
    _add_colorbar(fig, pm3, ax, rf"$N_{{sig}}$ (L={LUMI_CHECK} fb$^{{-1}}$)")

    if n_exc is not None:
        cs = ax.contour(L1, L2, sig_grid, levels=[n_exc],
                        colors=["cyan"], linewidths=1.8, zorder=5)
        ax.clabel(cs, fmt=f"N_exc={n_exc:.1f}", fontsize=8, colors="cyan")

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"$\lambda_1$"); ax.set_ylabel(r"$\lambda_2$")
    ax.set_title(rf"Signal yield  |  mode={MODE_CHECK}  (contour = N_exc)")

    plt.tight_layout()
    mx1_tag = str(mx1).replace(".", "-")
    fname = os.path.join(VERDIR, f"grid_panels_MX{mx1_tag}.pdf")
    fig.savefig(fname, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  saved: {fname}")


# ── [B] xs residual scatter ──────────────────────────────────────────────────

def plot_xs_residual(A_map: dict, df_xs: pd.DataFrame) -> None:
    """
    (xs_analytic - xs_data) / xs_data  for all MX1 on one figure.
    Left: 2D scatter in (lam1, lam2) colored by residual.
    Right: histogram of residuals.
    """
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    fig.suptitle(r"xs analytic residual  $(σ_{an} - σ_{data})\,/\,σ_{data}$", fontsize=13)

    for col, mx1 in enumerate(MX1_LIST):
        A      = A_map[mx1]
        sub    = df_xs[df_xs["mx1"] == mx1].copy()
        xs_an  = _xs_model((sub["lam1"].to_numpy(), sub["lam2"].to_numpy()), A)
        resid  = (xs_an - sub["xs"].to_numpy()) / sub["xs"].to_numpy()

        # --- 2D scatter colored by residual ---
        ax_top = axes[0, col]
        vabs   = max(abs(resid.min()), abs(resid.max()), 0.01)
        sc = ax_top.scatter(sub["lam1"], sub["lam2"], c=resid,
                            cmap="RdBu_r", vmin=-vabs, vmax=vabs,
                            s=35, edgecolors="k", linewidths=0.3)
        cb = fig.colorbar(sc, ax=ax_top, shrink=0.85, pad=0.02)
        cb.set_label("residual", fontsize=9)
        ax_top.set_xscale("log"); ax_top.set_yscale("log")
        ax_top.set_xlabel(r"$\lambda_1$"); ax_top.set_ylabel(r"$\lambda_2$")
        ax_top.set_title(rf"$m_{{X_1}}$={mx1} TeV", fontsize=11)

        # percentage annotation
        ax_top.text(0.03, 0.97,
                    f"max |res| = {abs(resid).max()*100:.1f}%\n"
                    f"mean res  = {resid.mean()*100:.1f}%",
                    transform=ax_top.transAxes, va="top", fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

        # --- histogram ---
        ax_bot = axes[1, col]
        ax_bot.hist(resid * 100, bins=25, color="steelblue", edgecolor="k", linewidth=0.5)
        ax_bot.axvline(0, color="red", lw=1.2, ls="--")
        ax_bot.set_xlabel("residual [%]"); ax_bot.set_ylabel("count")
        ax_bot.set_title(f"N={len(resid)} pts")

    plt.tight_layout()
    fname = os.path.join(VERDIR, "xs_residual_all.pdf")
    fig.savefig(fname, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  saved: {fname}")


# ── [C] eff 1D slice comparison  (interp vs data) ───────────────────────────

def plot_eff_slices(eff_interp: dict, df_eff: pd.DataFrame) -> None:
    """
    For each MX1: eff_gb vs lam2 at several fixed lam1 values.
    Checks that the spline passes through the data points correctly.
    """
    lam1_slices = [0.1, 0.3, 0.5, 0.8]
    lam2_dense  = np.linspace(0.04, 1.0, 300)

    fig, axes = plt.subplots(len(MX1_LIST), len(lam1_slices),
                             figsize=(5 * len(lam1_slices), 4 * len(MX1_LIST)),
                             sharex=True)

    for row, mx1 in enumerate(MX1_LIST):
        cut = OPTIMAL_CUTS[mx1]
        sp  = eff_interp[mx1]
        sub = df_eff[(df_eff["mx1"] == mx1) &
                     (df_eff["model"] == MODEL) &
                     (df_eff["bdt_cut"] == cut)].copy()

        for col, l1_fix in enumerate(lam1_slices):
            ax = axes[row, col]

            # data points at this lam1 (closest available grid value)
            l1_avail = sorted(sub["lam1"].unique())
            l1_near  = l1_avail[np.argmin([abs(v - l1_fix) for v in l1_avail])]
            pts      = sub[np.isclose(sub["lam1"], l1_near)].sort_values("lam2")

            # spline prediction along lam2 at fixed lam1
            l1_arr   = np.full_like(lam2_dense, l1_fix)
            eff_pred = np.clip(sp.ev(l1_arr, lam2_dense), 0, 1)

            ax.plot(lam2_dense, eff_pred, "b-", lw=1.5, label=f"spline (λ1={l1_fix})")
            ax.scatter(pts["lam2"], pts["eff_gb"],
                       color="red", s=30, zorder=5,
                       label=f"data (λ1≈{l1_near})")

            ax.set_ylim(0, None)
            ax.set_xlabel(r"$\lambda_2$")
            ax.set_ylabel(r"$\varepsilon_{gb}$")
            ax.set_title(rf"MX1={mx1}, λ1={l1_fix}")
            ax.legend(fontsize=7)
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fname = os.path.join(VERDIR, "eff_slices_all.pdf")
    fig.savefig(fname, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  saved: {fname}")


# ── [D] sig_grid ratio  xs-only vs full (lumi effect check) ─────────────────

def plot_sig_ratio_lumi(mx1: float, A: float, eff_sp, df_res: pd.DataFrame) -> None:
    """
    For one MX1, show sig_grid for lumi=300 and lumi=3000 side by side,
    with N_exc contour for mode=none overlaid on each.
    """
    L1, L2 = np.meshgrid(L1_GRID, L2_GRID)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(rf"Signal yield  |  $m_{{X_1}}$={mx1} TeV  |  mode=none", fontsize=13)

    for ax, lumi in zip(axes, [300, 3000]):
        sig = _sig_grid(mx1, lumi, A, eff_sp)
        kw  = _log_cmap_kwargs(sig, cmap="inferno")
        pm  = ax.pcolormesh(L1, L2, sig, shading="auto", **kw)
        _add_colorbar(fig, pm, ax, rf"$N_{{sig}}$", shrink=0.9)

        row_res = df_res[(df_res["mx1"]  == mx1) &
                         (df_res["lumi"] == lumi) &
                         (df_res["mode"] == "none")]
        if not row_res.empty:
            n_med = float(row_res.iloc[0]["N_exc_exp_med"])
            n_m1s = float(row_res.iloc[0]["N_exc_exp_m1s"])
            n_p1s = float(row_res.iloc[0]["N_exc_exp_p1s"])
            for n_exc, ls, label in [(n_m1s, "--", "-1σ"),
                                     (n_med,  "-", "med"),
                                     (n_p1s, ":",  "+1σ")]:
                try:
                    cs = ax.contour(L1, L2, sig, levels=[n_exc],
                                    colors=["cyan"], linewidths=1.5,
                                    linestyles=[ls], zorder=5)
                    ax.clabel(cs, fmt=f"{label}: {n_exc:.0f}", fontsize=7, colors="cyan")
                except Exception:
                    pass

        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel(r"$\lambda_1$"); ax.set_ylabel(r"$\lambda_2$")
        ax.set_title(rf"L = {lumi} fb$^{{-1}}$  (N_exc med shown)")

    plt.tight_layout()
    mx1_tag = str(mx1).replace(".", "-")
    fname   = os.path.join(VERDIR, f"sig_lumi_compare_MX{mx1_tag}.pdf")
    fig.savefig(fname, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  saved: {fname}")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("Loading data …")
    df_xs  = pd.read_csv(PATH_XS)
    df_eff = pd.read_csv(PATH_EFF)
    df_res = pd.read_csv(PATH_RES)

    print("Fitting A …")
    A_map = fit_A_per_mx1(df_xs)

    print("Building eff interpolators …")
    eff_interp = build_eff_interpolators(df_eff)

    print("\n[A] Per-MX1 grid panels (xs / eff / sig) …")
    for mx1 in MX1_LIST:
        plot_grid_panels(mx1, A_map[mx1], eff_interp[mx1], df_xs, df_eff, df_res)

    print("\n[B] xs residual (analytic vs data) …")
    plot_xs_residual(A_map, df_xs)

    print("\n[C] eff 1D slice check (spline vs data) …")
    plot_eff_slices(eff_interp, df_eff)

    print("\n[D] sig lumi comparison (300 vs 3000) …")
    for mx1 in MX1_LIST:
        plot_sig_ratio_lumi(mx1, A_map[mx1], eff_interp[mx1], df_res)

    print(f"\nAll diagnostics → {VERDIR}/")


if __name__ == "__main__":
    main()
