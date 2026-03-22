"""
plot/limit_plot.py
------------------
luminosity별 combined exclusion limit figure.
  - linear scale & log scale 두 버전
  - s_up 는 limit_summary.csv 에서 자동으로 읽음
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from plot.build_plane import build_plane, interpolate_plane, lam_to_float

# ============================================================
# USER CONFIG  ← 여기서 조절
# ============================================================

# --- exclusion boundary line ---
LINE_LW   = 2.0
LINE_LS   = "-"

# --- shaded exclusion (theoretical lower bound) ---
LAM1_EXCL = 0.051   # lam1 < 이 값이면 이론 제한으로 excluded
LAM2_EXCL = 0.071   # lam2 < 이 값이면 이론 제한으로 excluded
SHADE_COLOR = "#EE82EE"
SHADE_ALPHA = 0.35

# --- color per mass point ---
COLOR_MAP = {
    "1-0": "cornflowerblue",
    "1-5": "goldenrod",
    "2-0": "coral",
    "2-5": "#8B0000",
}

# --- axis ticks ---
X_TICKS = [0.1, 0.3, 0.5, 0.7, 1.0]
Y_TICKS = [0.1, 0.3, 0.5, 0.7, 1.0]

# --- log axis range ---
X_LIM_LOG = (0.03, 1.0)
Y_LIM_LOG = (0.04, 1.0)

# --- output ---
OUTPUT_DIR = "limit_plots"
DPI        = 200

# ============================================================


def _load_s_up(summary_csv: str, lumi, mx1) -> float | None:
    if not os.path.isfile(summary_csv):
        return None
    df = pd.read_csv(summary_csv)
    df["lumi"] = df["lumi"].astype(str).str.strip()
    df["mx1"]  = df["mx1"].astype(str).str.strip()
    matched = df[(df["lumi"] == str(int(float(lumi)))) & (df["mx1"] == str(mx1))]
    if matched.empty:
        return None
    return float(matched.iloc[-1]["s_up"])


def _add_boundary(ax, plane_interp: pd.DataFrame, s_up: float,
                  color, lw=LINE_LW, ls=LINE_LS):
    xi = plane_interp.columns.to_numpy(float)
    yi = plane_interp.index.to_numpy(float)
    Z  = np.ma.masked_invalid(plane_interp.to_numpy(float))
    X, Y = np.meshgrid(xi, yi)
    ax.contour(X, Y, Z, levels=[s_up],
               colors=[color], linewidths=lw, linestyles=ls)


def _make_fig(lumi: int,
              plot_points: list,
              summary_csv: str,
              log_scale: bool,
              col: str = "sg after") -> plt.Figure:
    """
    plot_points = [(lumi, mx1, csv_path), ...]  — 이미 해당 lumi 로 필터된 것
    """
    fig, ax = plt.subplots(figsize=(6, 5))

    # shaded excluded region
    ax.axvspan(0.0, LAM1_EXCL, color=SHADE_COLOR, alpha=SHADE_ALPHA, zorder=0)
    ax.axhspan(0.0, LAM2_EXCL, color=SHADE_COLOR, alpha=SHADE_ALPHA, zorder=0)

    proxy_lines = []
    labels      = []

    for _, mx1, csv_path in plot_points:
        s_up = _load_s_up(summary_csv, lumi, mx1)
        if s_up is None:
            print(f"[WARN] s_up not found for lumi={lumi}, mx1={mx1} → skipping")
            continue

        df           = pd.read_csv(csv_path)
        plane        = build_plane(df, mx1, col=col)
        plane_interp = interpolate_plane(plane)

        c = COLOR_MAP.get(mx1, "black")
        _add_boundary(ax, plane_interp, s_up, color=c)

        labels.append(rf"$M_{{X_1}}$ = {lam_to_float(mx1):.1f} TeV (95% CL)")
        proxy_lines.append(Line2D([0], [0], color=c, lw=LINE_LW, ls=LINE_LS))

    # axis style
    ax.set_xlabel(r"$\lambda_{1}$")
    ax.set_ylabel(r"$\lambda_{2}$")
    ax.set_xticks(X_TICKS)
    ax.set_yticks(Y_TICKS)

    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*X_LIM_LOG)
        ax.set_ylim(*Y_LIM_LOG)
        ax.minorticks_off()
    else:
        ax.set_xlim(left=0.0)
        ax.set_ylim(bottom=0.0)

    ax.legend(proxy_lines, labels, frameon=False, loc="best", fontsize=9)
    ax.text(0.87, 1.01, rf"{lumi} fb$^{{-1}}$", transform=ax.transAxes, fontsize=9)

    plt.tight_layout()
    return fig


def plot_limit_combined(lumi: int,
                        plot_points: list,
                        summary_csv: str = "results/limit_summary.csv",
                        col: str = "sg after",
                        log_scale: bool = False,
                        show: bool = False):
    """
    Parameters
    ----------
    lumi         : luminosity (300 or 3000)
    plot_points  : [(lumi, mx1, csv_path), ...]  全부 넘겨도 됨, lumi로 필터함
    summary_csv  : limit_summary.csv 경로
    log_scale    : True → log/log axes
    show         : plt.show() 호출 여부
    """
    filtered = [(L, m, p) for L, m, p in plot_points if int(L) == int(lumi)]

    fig = _make_fig(lumi, filtered, summary_csv, log_scale=log_scale, col=col)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scale_tag = "log" if log_scale else "linear"
    fname     = f"{OUTPUT_DIR}/limit_lumi{lumi}_{scale_tag}.png"
    fig.savefig(fname, dpi=DPI)
    print(f"[SAVE] {fname}")

    if show:
        plt.show()

    return fig


def plot_all_limits(plot_points: list,
                    summary_csv: str = "results/limit_summary.csv",
                    col: str = "sg after",
                    show: bool = False):
    """
    lumi=300 / lumi=3000 × linear / log → 총 4장 저장.
    """
    for lumi in [300, 3000]:
        for log_scale in [False, True]:
            plot_limit_combined(
                lumi, plot_points,
                summary_csv=summary_csv,
                col=col,
                log_scale=log_scale,
                show=show,
            )
