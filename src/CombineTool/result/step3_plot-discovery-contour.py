#!/usr/bin/env python3
"""
plot_discovery_contour.py
--------------------------
Generates discovery significance contour plots on the λ1 vs λ2 plane
for each Mx1 mass and both luminosities (300, 3000 fb-1),
using only statistical uncertainties (stats-only datacards).

Significance formula (Asimov, from one-bin-counting-experiments-101.md §5.3):
  Z_A = sqrt(2 * [(S+B) * ln(1 + S/B) - S])
where:
  S = s0  (signal yield for a given λ1, λ2 from BDT_cut signal CSV)
  B = b0  (background yield from stats datacard)

Data sources:
  - b0, sigma_b : datacards/datacard_lumi{L}_mx1{MX}_cut{CUT}_stats.txt
  - s0(λ1, λ2) : BDT_cut/out/FINAL/v2_2500_4_{CUT}/sig_lumi{L}_mx1{MX}.csv

Usage:
  python plot_discovery_contour.py [--out-dir OUTDIR] [--log] [--show]
"""

import argparse
import math
import os
import re
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.interpolate import griddata

# ============================================================
# CONFIG
# ============================================================

_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR  = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        ".."
                        )
_BDT_FINAL = os.path.join(_BASE_DIR, "..", "BDT_cut", "out", "FINAL")
_CARD_DIR  = os.path.join(_BASE_DIR, "datacards")

# mx1 tag (in datacard filename) → (mx1 label, cut tag, BDT cut folder)
MX1_CONFIG = {
    "1-0": {"label": "1.0 TeV", "cut_tag": "0p1050", "cut_dir": "v2_2500_4_0p1050"},
    "1-5": {"label": "1.5 TeV", "cut_tag": "0p1350", "cut_dir": "v2_2500_4_0p1350"},
    "2-0": {"label": "2.0 TeV", "cut_tag": "0p1440", "cut_dir": "v2_2500_4_0p1440"},
    "2-5": {"label": "2.5 TeV", "cut_tag": "0p1520", "cut_dir": "v2_2500_4_0p1520"},
}

LUMI_LIST = [300, 3000]

COLOR_MAP = {
    "1-0": "cornflowerblue",
    "1-5": "goldenrod",
    "2-0": "coral",
    "2-5": "#8B0000",
}

# Discovery / evidence thresholds
Z_DISCOVERY = 5.0   # solid line
Z_EVIDENCE  = 3.0   # dashed line

# Excluded-coupling shading (experiment-independent constraint)
LAM1_EXCL = 0.051
LAM2_EXCL = 0.071
SHADE_COLOR = "#EE82EE"
SHADE_ALPHA = 0.35

# Plot aesthetics
X_TICKS   = [0.1, 0.3, 0.5, 0.7, 1.0]
Y_TICKS   = [0.1, 0.3, 0.5, 0.7, 1.0]
X_LIM_LOG = (0.03, 1.0)
Y_LIM_LOG = (0.04, 1.0)
X_LIM_LIN = (0.0, 1.05)
Y_LIM_LIN = (0.0, 1.05)
DPI        = 200
INTERP_FACTOR = 100

# ============================================================
# DATACARD PARSER
# ============================================================

def parse_stats_datacard(path: str) -> dict:
    """
    Parse a stats datacard and return:
      {"b0": float, "sigma_b": float, "s0_ref": float}

    Parses:
      rate   <sig_rate>   <bkg_rate>
      stat_bkg   lnN   -   <kappa>    →  sigma_b = (kappa - 1) * bkg_rate
    """
    result = {}
    rate_re  = re.compile(r"^rate\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)")
    stat_re  = re.compile(r"^stat_bkg\s+lnN\s+-\s+([\d.eE+\-]+)", re.IGNORECASE)

    with open(path) as f:
        for line in f:
            line = line.strip()
            m = rate_re.match(line)
            if m:
                result["s0_ref"] = float(m.group(1))
                result["b0"]     = float(m.group(2))
                continue
            m = stat_re.match(line)
            if m:
                kappa = float(m.group(1))
                # sigma_b = (kappa - 1) * b0  [lnN convention: kappa = 1 + rel_unc]
                result["sigma_b"] = (kappa - 1.0) * result.get("b0", 0.0)

    if "b0" not in result:
        raise RuntimeError(f"Could not parse b0 from {path}")
    if "sigma_b" not in result:
        result["sigma_b"] = 0.0  # stats-only but no stat line found

    return result


# ============================================================
# SIGNAL CSV LOADER
# ============================================================

def lam_str_to_float(s: str) -> float:
    """'0-15' → 0.15,  '1-0' → 1.0"""
    return float(s.replace("-", "."))


def load_signal_plane(sig_csv: str, mx1: str) -> pd.DataFrame:
    """
    Read the signal CSV and build a 2D DataFrame of s0 values,
    indexed by λ2 (rows) and λ1 (columns) as floats.

    Signal name format: Signal_{mx1}_{lam1}_{lam2}.0
    """
    df = pd.read_csv(sig_csv)

    lam1_vals = set()
    lam2_vals = set()
    entries   = []

    for _, row in df.iterrows():
        name  = str(row["signal"]).strip()
        parts = name.split("_")
        if len(parts) != 4:
            continue
        _, f_mx1, f_lam1, f_lam2_raw = parts
        if f_mx1 != mx1:
            continue
        # lam2 may end in ".0" (e.g. "0-04.0") — strip it
        f_lam2 = f_lam2_raw.rstrip(".0") if f_lam2_raw.endswith(".0") else f_lam2_raw
        # Handle "1-0.0" → "1-0", "2-0.0" → "2-0"
        f_lam2 = re.sub(r"\.0$", "", f_lam2_raw.replace("-", "X")).replace("X", "-")
        # Simpler: just strip trailing ".0"
        f_lam2 = f_lam2_raw
        if f_lam2.endswith(".0"):
            f_lam2 = f_lam2[:-2]

        lam1_f = lam_str_to_float(f_lam1)
        lam2_f = lam_str_to_float(f_lam2)
        s0     = float(row["sg after"])

        lam1_vals.add(lam1_f)
        lam2_vals.add(lam2_f)
        entries.append((lam1_f, lam2_f, s0))

    if not entries:
        raise RuntimeError(f"No signal entries found for mx1={mx1} in {sig_csv}")

    lam1_arr = sorted(lam1_vals)
    lam2_arr = sorted(lam2_vals)

    plane = pd.DataFrame(np.nan, index=lam2_arr, columns=lam1_arr)
    for lam1_f, lam2_f, s0 in entries:
        plane.loc[lam2_f, lam1_f] = s0

    return plane


# ============================================================
# SIGNIFICANCE CALCULATOR
# ============================================================

def z_asimov(s: float, b: float) -> float:
    """
    Asimov significance (stats-only, μ=1 hypothesis):
      Z_A = sqrt(2 * [(S+B)*ln(1 + S/B) - S])

    Returns 0 if s <= 0 or b <= 0.
    """
    if s <= 0.0 or b <= 0.0:
        return 0.0
    return math.sqrt(max(0.0, 2.0 * ((s + b) * math.log(1.0 + s / b) - s)))


def build_z_plane(sig_plane: pd.DataFrame, b0: float) -> pd.DataFrame:
    """
    For each (λ1, λ2) cell, compute Z_asimov(s0, b0).
    Returns a DataFrame with the same index/columns as sig_plane.
    """
    z_plane = sig_plane.copy()
    for lam2 in sig_plane.index:
        for lam1 in sig_plane.columns:
            s0 = sig_plane.loc[lam2, lam1]
            z_plane.loc[lam2, lam1] = z_asimov(float(s0), b0) if not np.isnan(s0) else np.nan
    return z_plane


# ============================================================
# INTERPOLATION
# ============================================================

def interpolate_plane(plane: pd.DataFrame, factor: int = INTERP_FACTOR) -> tuple:
    """
    Returns (XI, YI, ZI) as 2D numpy arrays on a fine grid.
    XI: λ1 grid, YI: λ2 grid, ZI: interpolated values.
    """
    x  = np.array(plane.columns.tolist(), dtype=float)
    y  = np.array(plane.index.tolist(),   dtype=float)
    X, Y = np.meshgrid(x, y)
    Z    = plane.to_numpy(dtype=float)
    mask = np.isfinite(Z)

    xi = np.linspace(x.min(), x.max(), len(x) * factor)
    yi = np.linspace(y.min(), y.max(), len(y) * factor)
    XI, YI = np.meshgrid(xi, yi)

    pts  = np.column_stack([X[mask], Y[mask]])
    vals = Z[mask]
    ZI   = griddata(pts, vals, (XI, YI), method="linear")
    return XI, YI, ZI


# ============================================================
# PLOT
# ============================================================

def make_discovery_plot(lumi: int, results: dict,
                        log_scale: bool = False) -> plt.Figure:
    """
    results: {mx1: {"z_plane_interp": (XI, YI, ZI), "b0": float, ...}}
    Draws Z=5 (solid) and Z=3 (dashed) contours for each mx1.
    """
    fig, ax = plt.subplots(figsize=(6, 5))

    # Excluded-coupling shading
    ax.axvspan(0.0, LAM1_EXCL, color=SHADE_COLOR, alpha=SHADE_ALPHA, zorder=0)
    ax.axhspan(0.0, LAM2_EXCL, color=SHADE_COLOR, alpha=SHADE_ALPHA, zorder=0)

    proxy_lines = []
    labels      = []

    for mx1, data in results.items():
        XI, YI, ZI = data["z_plane_interp"]
        color       = COLOR_MAP.get(mx1, "black")

        # Z = 5 (discovery): solid
        cs5 = ax.contour(XI, YI, ZI, levels=[Z_DISCOVERY],
                         colors=[color], linewidths=2.0, linestyles="-")
        # Z = 3 (evidence): dashed
        cs3 = ax.contour(XI, YI, ZI, levels=[Z_EVIDENCE],
                         colors=[color], linewidths=1.5, linestyles="--")

        cfg    = MX1_CONFIG[mx1]
        b0_val = data["b0"]
        labels.append(
            rf"$M_{{X_1}}$ = {cfg['label']}  "
            rf"(cut = {cfg['cut_tag'].replace('0p', '0.')}, "
            rf"$B$ = {b0_val:.0f})"
        )
        proxy_lines.append(Line2D([0], [0], color=color, lw=2.0, ls="-"))

    # Legend for threshold lines
    leg_thresh = [
        Line2D([0], [0], color="gray", lw=2.0, ls="-",  label=rf"$Z = {Z_DISCOVERY:.0f}\sigma$ (discovery)"),
        Line2D([0], [0], color="gray", lw=1.5, ls="--", label=rf"$Z = {Z_EVIDENCE:.0f}\sigma$ (evidence)"),
    ]

    # Axes style
    ax.set_xlabel(r"$\lambda_{1}$", fontsize=12)
    ax.set_ylabel(r"$\lambda_{2}$", fontsize=12)

    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*X_LIM_LOG)
        ax.set_ylim(*Y_LIM_LOG)
        ax.minorticks_off()
        ax.set_xticks(X_TICKS)
        ax.set_yticks(Y_TICKS)
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    else:
        ax.set_xlim(*X_LIM_LIN)
        ax.set_ylim(*Y_LIM_LIN)
        ax.set_xticks(X_TICKS)
        ax.set_yticks(Y_TICKS)

    # Two-part legend: mx1 curves + threshold lines
    leg1 = ax.legend(proxy_lines, labels, frameon=False,
                     loc="upper left", fontsize=7.5,
                     title=r"$M_{X_1}$ (stats-only)", title_fontsize=8)
    ax.add_artist(leg1)
    ax.legend(handles=leg_thresh, frameon=False,
              loc="lower right", fontsize=8)

    ax.text(0.98, 1.01, rf"{lumi} fb$^{{-1}}$  (stats-only unc.)",
            transform=ax.transAxes, fontsize=8, ha="right")
    ax.set_title("Discovery Contour", fontsize=11)

    plt.tight_layout()
    return fig


# ============================================================
# MAIN
# ============================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="Discovery contour plotter (stats-only, Asimov Z)"
    )
    p.add_argument("--out-dir", default="plots_discovery",
                   help="Output directory for PNG files (default: discovery_plots)")
    p.add_argument("--log", action="store_true",
                   help="Also save log-scale version")
    p.add_argument("--show", action="store_true",
                   help="Display interactive plot window")
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    for lumi in LUMI_LIST:
        print(f"\n{'='*60}")
        print(f"  Lumi = {lumi} fb-1")
        print(f"{'='*60}")

        results = {}

        for mx1, cfg in MX1_CONFIG.items():
            print(f"\n  --- mx1 = {mx1} ({cfg['label']}) ---")

            # ── 1. Parse stats datacard ──
            # Filename convention: "mx1" prefix + mx1 tag, e.g. mx1="1-0" → "mx11-0"
            card_name = f"datacard_lumi{lumi}_mx1{mx1}_cut{cfg['cut_tag']}_stats.txt"
            card_path = os.path.join(_CARD_DIR, card_name)
            if not os.path.isfile(card_path):
                print(f"  [WARN] datacard not found: {card_path}, skipping")
                continue

            print(f"  datacard: {os.path.basename(card_path)}")
            card_data = parse_stats_datacard(card_path)
            b0        = card_data["b0"]
            sigma_b   = card_data["sigma_b"]
            print(f"  b0      = {b0:.4f}")
            print(f"  sigma_b = {sigma_b:.4f}  (rel = {sigma_b/b0*100:.2f}%)")

            # ── 2. Load signal plane ──
            sig_csv = os.path.join(
                _BDT_FINAL, cfg["cut_dir"],
                f"sig_lumi{lumi}_mx1{mx1}.csv"
            )
            if not os.path.isfile(sig_csv):
                print(f"  [WARN] signal CSV not found: {sig_csv}, skipping")
                continue

            print(f"  sig CSV : {sig_csv}")
            sig_plane = load_signal_plane(sig_csv, mx1)
            print(f"  plane   : {sig_plane.shape[1]} λ1 × {sig_plane.shape[0]} λ2 points")

            # ── 3. Compute Z plane ──
            z_plane = build_z_plane(sig_plane, b0)

            z_vals = z_plane.to_numpy(dtype=float).flatten()
            z_vals = z_vals[np.isfinite(z_vals)]
            print(f"  Z range : [{z_vals.min():.2f}, {z_vals.max():.2f}]")

            # ── 4. Interpolate ──
            XI, YI, ZI = interpolate_plane(z_plane)

            results[mx1] = {
                "b0":              b0,
                "sigma_b":         sigma_b,
                "z_plane":         z_plane,
                "z_plane_interp":  (XI, YI, ZI),
            }

        if not results:
            print(f"[WARN] No results for lumi={lumi}, skipping plot.")
            continue

        # ── 5. Plot ──
        for log_scale in ([False, True] if args.log else [False]):
            fig = make_discovery_plot(lumi=lumi, results=results, log_scale=log_scale)
            scale_tag = "log" if log_scale else "linear"
            fname = os.path.join(args.out_dir, f"discovery_lumi{lumi}_{scale_tag}.png")
            fig.savefig(fname, dpi=DPI)
            print(f"\n[SAVE] {fname}")
            if args.show:
                plt.show()
            plt.close(fig)

    print("\n[DONE]")


if __name__ == "__main__":
    main()
