"""
plot/plane_plot.py
------------------
per (lumi, mx1) plane 플랏:
  - heatmap
  - s_up boundary line  (limit_summary.csv 에서 자동으로 읽음)
  - 로그 스타일 등고선
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plot.build_plane import build_plane, interpolate_plane, lam_to_float

# ============================================================
# USER CONFIG  ← 여기서 조절
# ============================================================

# --- heatmap ---
CMAP          = "viridis"   # colormap

# --- s_up boundary ---
SUP_LINE_COLOR = "red"
SUP_LINE_LW    = 2.5
SUP_LINE_LS    = "-"

# --- log-style contour levels ---
# 1 2 3 ... 9  10 20 30 ... 90  100 200 ...
LOG_CONTOUR_LEVELS = (
    list(range(1,   10))   +   # 1–9
    list(range(10,  100, 10)) + # 10–90
    list(range(100, 1000,100)) + # 100–900
    list(range(1000,10001,1000)) # 1000–10000
)
LOG_CONTOUR_COLOR  = "white"
LOG_CONTOUR_LW     = 0.7
LOG_CONTOUR_ALPHA  = 0.8
LOG_CONTOUR_FONTSIZE = 7    # clabel 폰트 크기, None 이면 표시 안 함

# --- output ---
OUTPUT_DIR    = "limit_plots/planes"
DPI           = 600

# ============================================================


def _load_s_up(summary_csv: str, lumi, mx1) -> float | None:
    """
    limit_summary.csv 에서 해당 (lumi, mx1) 의 s_up 를 읽어온다.
    여러 행이 있을 경우 마지막 행(가장 최신)을 사용한다.
    """
    if not os.path.isfile(summary_csv):
        return None

    df = pd.read_csv(summary_csv)
    df["lumi"] = df["lumi"].astype(str).str.strip()
    df["mx1"]  = df["mx1"].astype(str).str.strip()

    matched = df[(df["lumi"] == str(int(float(lumi)))) & (df["mx1"] == str(mx1))]
    if matched.empty:
        return None

    return float(matched.iloc[-1]["s_up"])


def plot_plane(df: pd.DataFrame,
               mx1: str,
               lumi: int | float,
               summary_csv: str = "results/limit_summary.csv",
               col: str = "sg after",
               save: bool = True,
               show: bool = False) -> plt.Axes:
    """
    한 (lumi, mx1) 에 대한 plane 플랏을 생성한다.

    Parameters
    ----------
    df           : signal CSV DataFrame (build_plane 에 전달)
    mx1          : mass label  e.g. "1-0"
    lumi         : luminosity  e.g. 300
    summary_csv  : limit_summary.csv 경로 (s_up 읽기용)
    col          : signal yield 컬럼명
    save         : PNG 저장 여부
    show         : plt.show() 호출 여부
    """

    # ---- plane 생성 ----
    plane        = build_plane(df, mx1, col=col)
    plane_interp = interpolate_plane(plane)

    xi = plane_interp.columns.to_numpy(float)
    yi = plane_interp.index.to_numpy(float)
    Z  = np.ma.masked_invalid(plane_interp.to_numpy(float))
    X, Y = np.meshgrid(xi, yi)

    # ---- figure ----
    fig, ax = plt.subplots(figsize=(6, 5))

    # heatmap
    im = ax.imshow(
        Z,
        origin="lower",
        aspect="auto",
        extent=[xi.min(), xi.max(), yi.min(), yi.max()],
        cmap=CMAP,
    )
    fig.colorbar(im, ax=ax, label=col)

    # log-style contour
    levels_valid = [lv for lv in LOG_CONTOUR_LEVELS if lv < float(np.nanmax(Z))]
    if levels_valid:
        cs = ax.contour(
            X, Y, Z,
            levels=levels_valid,
            colors=LOG_CONTOUR_COLOR,
            linewidths=LOG_CONTOUR_LW,
            alpha=LOG_CONTOUR_ALPHA,
        )
        if LOG_CONTOUR_FONTSIZE is not None:
            ax.clabel(cs, fmt="%g", fontsize=LOG_CONTOUR_FONTSIZE)

    # s_up boundary
    s_up = _load_s_up(summary_csv, lumi, mx1)
    if s_up is not None and np.isfinite(s_up):
        cs_sup = ax.contour(
            X, Y, Z,
            levels=[s_up],
            colors=[SUP_LINE_COLOR],
            linewidths=SUP_LINE_LW,
            linestyles=SUP_LINE_LS,
        )
        ax.clabel(cs_sup, fmt=f"s_up={s_up:.1f}", fontsize=8)
    else:
        print(f"[WARN] s_up not found for lumi={lumi}, mx1={mx1} in {summary_csv}")

    # labels
    ax.set_xlabel(r"$\lambda_{1}$")
    ax.set_ylabel(r"$\lambda_{2}$")
    ax.set_title(
        rf"$M_{{X_1}}$ = {lam_to_float(mx1):.1f} TeV, "
        rf"$\mathcal{{L}}$ = {int(lumi)} fb$^{{-1}}$"
    )

    plt.tight_layout()

    # save
    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        fname = f"{OUTPUT_DIR}/plane_lumi{int(lumi)}_mx1{mx1}.png"
        plt.savefig(fname, dpi=DPI)
        print(f"[SAVE] {fname}")

    if show:
        plt.show()

    return ax


def plot_all_planes(plot_points: list,
                    summary_csv: str = "results/limit_summary.csv",
                    col: str = "sg after",
                    show: bool = False):
    """
    plot_points = [
        (lumi, mx1, csv_path),
        ...
    ]
    총 8개를 순회하면서 plane_plot 저장.
    """
    for lumi, mx1, csv_path in plot_points:
        print(f"\n[PLANE] lumi={lumi}, mx1={mx1}, csv={csv_path}")
        print(f"[DBG] csv_path: {csv_path} @ plot_all_planes")
        df = pd.read_csv(csv_path)
        plot_plane(df, mx1=mx1, lumi=lumi,
                   summary_csv=summary_csv, col=col,
                   save=True, show=show)
