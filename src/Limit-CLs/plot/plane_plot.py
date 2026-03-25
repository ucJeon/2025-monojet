"""
plot/plane_plot.py
------------------
per (lumi, mx1) plane 플랏:
  - heatmap
  - s_up boundary line  (limit_summary.csv 에서 자동으로 읽음)
  - ±1σ, ±2σ band contour
  - 로그 스타일 등고선
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from plot.build_plane import build_plane, interpolate_plane, lam_to_float

# ============================================================
# USER CONFIG  ← 여기서 조절
# ============================================================

CMAP          = "viridis"

SUP_LINE_COLOR = "red"
SUP_LINE_LW    = 2.5
SUP_LINE_LS    = "-"

BAND1_COLOR   = "tomato"
BAND1_LW      = 1.2
BAND1_LS      = "--"
BAND2_COLOR   = "tomato"
BAND2_LW      = 0.8
BAND2_LS      = ":"

LOG_CONTOUR_LEVELS = (
    list(range(1,   10))    +
    list(range(10,  100, 10)) +
    list(range(100, 1000, 100)) +
    list(range(1000, 10001, 1000))
)
LOG_CONTOUR_COLOR   = "white"
LOG_CONTOUR_LW      = 0.7
LOG_CONTOUR_ALPHA   = 0.8
LOG_CONTOUR_FONTSIZE = 7

OUTPUT_DIR = "limit_plots/planes"
DPI        = 150

# ============================================================


def _load_s_up_row(summary_csv: str,
                   lumi, mx1,
                   version=None, ntree=None, maxdepth=None,
                   cut=None, mode=None) -> pd.Series | None:
    """
    limit_summary.csv 에서 조건에 맞는 행을 찾아 반환.
    필터: lumi, mx1, version, ntree, maxdepth, cut, mode
    여러 행이 매칭되면 마지막 행 사용.
    """
    if not os.path.isfile(summary_csv):
        return None

    df = pd.read_csv(summary_csv)
    for col in ["lumi", "mx1", "version", "ntree", "maxdepth", "mode"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    mask = (
        (df["lumi"] == str(int(float(lumi)))) &
        (df["mx1"]  == str(mx1))
    )
    if version  is not None and "version"  in df.columns:
        mask &= (df["version"]  == str(version))
    if ntree    is not None and "ntree"    in df.columns:
        mask &= (df["ntree"]    == str(ntree))
    if maxdepth is not None and "maxdepth" in df.columns:
        mask &= (df["maxdepth"] == str(maxdepth))
    if cut      is not None and "cut"      in df.columns:
        # float 비교: 문자열 변환 후 비교
        df["cut_str"] = df["cut"].astype(str).str.strip()
        mask &= (df["cut_str"] == str(float(cut)))
    if mode     is not None and "mode"     in df.columns:
        mask &= (df["mode"]    == str(mode))

    matched = df[mask]
    if matched.empty:
        print(f"[WARN] no match: lumi={lumi}, mx1={mx1}, "
              f"version={version}, ntree={ntree}, maxdepth={maxdepth}, "
              f"cut={cut}, mode={mode}")
        return None

    return matched.iloc[-1]


def _get_val(row, col):
    if row is None or col not in row.index:
        return None
    v = row[col]
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except Exception:
        return None


def plot_plane(df: pd.DataFrame,
               mx1: str,
               lumi: int | float,
               summary_csv: str = "results/limit_summary.csv",
               version=None, ntree=None, maxdepth=None,
               cut=None, mode="asymptotic",
               col: str = "sg after",
               save: bool = True,
               show: bool = False) -> plt.Axes:

    # ---- plane 생성 ----
    plane        = build_plane(df, mx1, col=col)
    plane_interp = interpolate_plane(plane)

    xi = plane_interp.columns.to_numpy(float)
    yi = plane_interp.index.to_numpy(float)
    Z  = np.ma.masked_invalid(plane_interp.to_numpy(float))
    X, Y = np.meshgrid(xi, yi)

    # ---- summary CSV 조회 ----
    row = _load_s_up_row(summary_csv, lumi, mx1,
                         version=version, ntree=ntree, maxdepth=maxdepth,
                         cut=cut, mode=mode)

    s_up    = _get_val(row, "s_up")
    s_up_m1 = _get_val(row, "s_up_m1")
    s_up_p1 = _get_val(row, "s_up_p1")
    s_up_m2 = _get_val(row, "s_up_m2")
    s_up_p2 = _get_val(row, "s_up_p2")

    # ---- figure ----
    fig, ax = plt.subplots(figsize=(6, 5))

    im = ax.imshow(
        Z, origin="lower", aspect="auto",
        extent=[xi.min(), xi.max(), yi.min(), yi.max()],
        cmap=CMAP,
    )
    fig.colorbar(im, ax=ax, label=col)

    # log-style contour
    z_max = float(np.nanmax(Z))
    levels_valid = [lv for lv in LOG_CONTOUR_LEVELS if lv < z_max]
    if levels_valid:
        cs = ax.contour(X, Y, Z, levels=levels_valid,
                        colors=LOG_CONTOUR_COLOR,
                        linewidths=LOG_CONTOUR_LW,
                        alpha=LOG_CONTOUR_ALPHA)
        if LOG_CONTOUR_FONTSIZE is not None:
            ax.clabel(cs, fmt="%g", fontsize=LOG_CONTOUR_FONTSIZE)

    # ±2σ band
    for val, ls, lw, label in [
        (s_up_m2, BAND2_LS, BAND2_LW, r"$-2\sigma$"),
        (s_up_p2, BAND2_LS, BAND2_LW, r"$+2\sigma$"),
        (s_up_m1, BAND1_LS, BAND1_LW, r"$-1\sigma$"),
        (s_up_p1, BAND1_LS, BAND1_LW, r"$+1\sigma$"),
    ]:
        if val is not None:
            ax.contour(X, Y, Z, levels=[val],
                       colors=[BAND2_COLOR], linewidths=lw, linestyles=ls)

    # median (s_up) 빨간 선
    if s_up is not None:
        cs_sup = ax.contour(X, Y, Z, levels=[s_up],
                            colors=[SUP_LINE_COLOR],
                            linewidths=SUP_LINE_LW,
                            linestyles=SUP_LINE_LS)
        ax.clabel(cs_sup, fmt=f"s_up={s_up:.1f}", fontsize=8)
    else:
        print(f"[WARN] s_up not found: lumi={lumi}, mx1={mx1}, cut={cut}, mode={mode}")

    ax.set_xlabel(r"$\lambda_{1}$")
    ax.set_ylabel(r"$\lambda_{2}$")

    cut_str  = f", cut={cut}" if cut is not None else ""
    mode_str = f" [{mode}]" if mode else ""
    ax.set_title(
        rf"$M_{{X_1}}$ = {lam_to_float(mx1):.1f} TeV, "
        rf"$\mathcal{{L}}$ = {int(lumi)} fb$^{{-1}}${cut_str}{mode_str}"
    )

    plt.tight_layout()

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cut_tag = f"_cut{str(cut).replace('.','p')}" if cut is not None else ""
        fname   = f"{OUTPUT_DIR}/plane_lumi{int(lumi)}_mx1{mx1}{cut_tag}_{mode}.png"
        plt.savefig(fname, dpi=DPI)
        print(f"[SAVE] {fname}")

    if show:
        plt.show()

    plt.close()
    return ax


def plot_all_planes(plot_points: list,
                    summary_csv: str = "results/limit_summary.csv",
                    version=None, ntree=None, maxdepth=None,
                    cut=None, mode="asymptotic",
                    col: str = "sg after",
                    show: bool = False):
    """
    plot_points = [(lumi, mx1, csv_path), ...]
    """
    for lumi, mx1, csv_path in plot_points:
        print(f"\n[PLANE] lumi={lumi}, mx1={mx1}, cut={cut}, mode={mode}")
        df = pd.read_csv(csv_path)
        plot_plane(df, mx1=mx1, lumi=lumi,
                   summary_csv=summary_csv,
                   version=version, ntree=ntree, maxdepth=maxdepth,
                   cut=cut, mode=mode,
                   col=col, save=True, show=show)

