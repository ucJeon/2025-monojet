#!/usr/bin/env python3
"""
step_combined.py  —  All-in-one combined contour plotter
---------------------------------------------------------
Draws on a single figure per luminosity:

  • Solid lines   : expected 95 % CL exclusion contours   (from step2 logic)
  • Dashed lines  : 5 σ Asimov discovery contours         (from step3 logic)

Both contour types use the same colour per Mx1 mass point.

ALL user-tunable parameters live in the CONFIG section at the very top.

Usage
-----
  python3 step_combined.py               # both lumi, linear+log per LOG_SCALE
  python3 step_combined.py --lumi 300    # single luminosity
  python3 step_combined.py --show        # open interactive window
"""

# ============================================================
# ██████████████████████  CONFIG  ████████████████████████████
# ============================================================
# Edit the variables below.  Everything else is auto-derived.
# ============================================================

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))

# ── Input Paths ──────────────────────────────────────────────

RESULTCARD   = _os.path.join(_HERE, "resultcard_expected.txt")

DATACARD_DIR = ("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
                "CombineTool/datacards")

SIG_BASE     = ("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
                "BDT_cut/out")

# Per-mass signal-CSV directories and cut tags
SIG_DIR_MAP  = {
    "1-0": f"{SIG_BASE}/v2_2500_4_0p1050",
    "1-5": f"{SIG_BASE}/v2_2500_4_0p1350",
    "2-0": f"{SIG_BASE}/v2_2500_4_0p1440",
    "2-5": f"{SIG_BASE}/v2_2500_4_0p1520",
}

CUT_TAG_MAP  = {          # used in datacard filename
    "1-0": "0p1050",
    "1-5": "0p1350",
    "2-0": "0p1440",
    "2-5": "0p1520",
}

CUT_MAP      = {          # human-readable BDT cut for legend
    "1-0": "0.1050",
    "1-5": "0.1350",
    "2-0": "0.1440",
    "2-5": "0.1520",
}

MX1_LABELS   = {          # display label per mass key
    "1-0": "1.0",
    "1-5": "1.5",
    "2-0": "2.0",
    "2-5": "2.5",
}

# ── Physics Configuration ────────────────────────────────────

LUMI_LIST    = [300, 3000]          # luminosities to process [fb-1]

MX1_LIST     = ["1-0", "1-5", "2-0", "2-5"]   # mass points to include

MODE_LIST    = ["none", "stats", "sys1", "sys2", "sys3"]
                                    # systematic modes to process for 95 % CL expected limit

Z_THRESHOLD  = 5.0                  # discovery significance threshold [σ]

# λ grid — dash-separated strings for the contour plane
LAM1_LIST = [
    "0-03", "0-05", "0-07", "0-08", "0-1", "0-15",
    "0-2",  "0-3",  "0-4",  "0-5",  "0-6", "0-7", "0-8", "0-9", "1-0",
]
LAM2_LIST = [
    "0-04", "0-06", "0-08", "0-1", "0-15",
    "0-2",  "0-3",  "0-4",  "0-5", "0-6",  "0-7", "0-8", "0-9", "1-0",
]

# ── Hinterpadronization Region ─────────────────────────────────────

SHOW_HADRONIZATION = True           # True: draw the shaded region + legend entry

HAD_REGION_X       = 0.05          # upper λ1 boundary of the shaded band
HAD_REGION_Y       = 0.07          # upper λ2 boundary of the shaded band

HAD_COLOR          = "lightsteelblue"
HAD_ALPHA          = 0.45
HAD_LEGEND_LABEL   = (r"Hadronization region of "
                       r"$m_{X_1}$ = 1 TeV")

# ── Axis Scale ───────────────────────────────────────────────

LOG_SCALE = True                    # True: log scale,  False: linear scale

# ── Plot Styling ─────────────────────────────────────────────

COLOR_MAP  = {
    "1-0": "cornflowerblue",
    "1-5": "goldenrod",
    "2-0": "coral",
    "2-5": "#8B0000",
}

X_TICKS  = [0.1, 0.3, 0.5, 0.7, 1.0]
Y_TICKS  = [0.1, 0.3, 0.5, 0.7, 1.0]

X_LIM_LOG = (0.03, 1.0)            # axis limits for log scale
Y_LIM_LOG = (0.04, 1.0)
X_LIM_LIN = (0.03,  1.0)           # axis limits for linear scale
Y_LIM_LIN = (0.04,  1.0)

LEG_LOC      = "upper right"       # legend anchor
LUMI_POS     = (0.98, 1.01)        # axes-fraction coords for luminosity text

INTERP_FACTOR = 100                # interpolation grid density
DPI           = 200
OUT_DIR       = _os.path.join(_HERE, "plots_combined")

# ============================================================
# ████████████████  END OF CONFIG  ███████████████████████████
# ============================================================


import argparse
import math
import re
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple
from scipy.interpolate import griddata


# ============================================================
# HELPERS
# ============================================================

def lam_to_float(v: str) -> float:
    """'0-15' → 0.15"""
    return float(v.replace("-", "."))


# ── resultcard parser (step2 logic) ─────────────────────────

def parse_resultcard(path: str, mode: str,
                     mx1_list: list) -> dict:
    """
    Returns { lumi (int): { mx1 (str): r (float) } }
    for the requested mode.
    """
    mx1_map  = {f"{float(m.replace('-', '.')):.1f}": m for m in mx1_list}
    lumi_re  = re.compile(r"##\s+Summary:\s+lumi=(\d+)", re.IGNORECASE)
    sep_re   = re.compile(r"^:?-+:?$")

    result        = {}
    current_lumi  = None
    mode_col      = None

    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue

            m = lumi_re.search(line)
            if m:
                current_lumi = int(m.group(1))
                mode_col     = None
                result.setdefault(current_lumi, {})
                continue

            if current_lumi is None or not line.startswith("|"):
                continue

            cells = [c.strip() for c in line.split("|")[1:-1]]
            if not cells:
                continue

            if all(sep_re.match(c) for c in cells if c):
                continue

            if mode_col is None:
                try:
                    float(cells[0])
                except ValueError:
                    if mode in cells:
                        mode_col = cells.index(mode)
                continue

            try:
                key = f"{float(cells[0]):.1f}"
            except ValueError:
                continue

            mx1 = mx1_map.get(key)
            if mx1 is None or mode_col >= len(cells):
                continue
            try:
                result[current_lumi][mx1] = float(cells[mode_col])
            except ValueError:
                pass

    return result


def get_s0_from_datacard(card_path: str):
    """Read the signal rate from a combine datacard (first number on 'rate' line)."""
    try:
        with open(card_path) as f:
            for line in f:
                if line.strip().startswith("rate"):
                    return float(line.split()[1])
    except Exception:
        pass
    return None


# ── signal plane builder (step2 logic) ──────────────────────

def _get_signal_value(df: pd.DataFrame, mx1: str,
                      lam1: str, lam2: str,
                      col: str = "sg after") -> float:
    key = f"Signal_{mx1}_{lam1}_{lam2}.0"
    s   = df.loc[df["signal"].eq(key), col]
    return float(s.iat[0]) if len(s) else np.nan


def build_signal_plane(sig_csv: str, mx1: str,
                       lam1_list: list, lam2_list: list,
                       col: str = "sg after") -> pd.DataFrame:
    df    = pd.read_csv(sig_csv)
    plane = pd.DataFrame(index=lam2_list, columns=lam1_list, dtype=float)
    for lam1 in lam1_list:
        for lam2 in lam2_list:
            plane.loc[lam2, lam1] = _get_signal_value(df, mx1, lam1, lam2, col)
    return plane


# ── interpolation (shared) ───────────────────────────────────
# 이 내용을 step_combined.py의 interpolate_plane_str / interpolate_plane_float 함수와 교체

from scipy.interpolate import RegularGridInterpolator
import numpy as np


def _fill_nan_nearest(Z: np.ndarray) -> np.ndarray:
    """
    2D array의 NaN을 nearest 유효값으로 채운다.
    scipy.interpolate.NearestNDInterpolator 사용.
    """
    from scipy.interpolate import NearestNDInterpolator
    mask = np.isfinite(Z)
    if mask.all():
        return Z
    rows, cols = np.indices(Z.shape)
    interp = NearestNDInterpolator(
        list(zip(rows[mask], cols[mask])),
        Z[mask]
    )
    Z_filled = Z.copy()
    nan_rows, nan_cols = np.where(~mask)
    Z_filled[nan_rows, nan_cols] = interp(nan_rows, nan_cols)
    return Z_filled


def interpolate_plane_str(plane, factor=100):
    """
    plane: dash-string index/columns DataFrame
    returns: (XI, YI, ZI) numpy arrays  — NO NaN gaps
    """
    x = np.array([lam_to_float(v) for v in plane.columns], dtype=float)
    y = np.array([lam_to_float(v) for v in plane.index],   dtype=float)
    Z = plane.to_numpy(dtype=float)

    # NaN 채우기 (nearest)
    Z = _fill_nan_nearest(Z)

    xi = np.linspace(x.min(), x.max(), len(x) * factor)
    yi = np.linspace(y.min(), y.max(), len(y) * factor)

    # RegularGridInterpolator: 직사각형 그리드에 최적
    interp = RegularGridInterpolator(
        (y, x), Z,
        method="linear",
        bounds_error=False,
        fill_value=None          # 범위 밖도 외삽 (잘림 방지)
    )
    XI, YI = np.meshgrid(xi, yi)
    pts = np.column_stack([YI.ravel(), XI.ravel()])
    ZI  = interp(pts).reshape(XI.shape)

    return XI, YI, ZI


def interpolate_plane_float(plane, factor=100):
    """
    plane: float index/columns DataFrame
    returns: (XI, YI, ZI) numpy arrays  — NO NaN gaps
    """
    x = np.array(plane.columns.tolist(), dtype=float)
    y = np.array(plane.index.tolist(),   dtype=float)
    Z = plane.to_numpy(dtype=float)

    # NaN 채우기 (nearest)
    Z = _fill_nan_nearest(Z)

    xi = np.linspace(x.min(), x.max(), len(x) * factor)
    yi = np.linspace(y.min(), y.max(), len(y) * factor)

    interp = RegularGridInterpolator(
        (y, x), Z,
        method="linear",
        bounds_error=False,
        fill_value=None
    )
    XI, YI = np.meshgrid(xi, yi)
    pts = np.column_stack([YI.ravel(), XI.ravel()])
    ZI  = interp(pts).reshape(XI.shape)

    return XI, YI, ZI
# ── stats-datacard parser (step3 logic) ─────────────────────

def parse_stats_datacard(path: str) -> dict:
    """Returns {"b0": float, "sigma_b": float}."""
    result  = {}
    rate_re = re.compile(r"^rate\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)")
    stat_re = re.compile(r"^stat_bkg\s+lnN\s+-\s+([\d.eE+\-]+)", re.IGNORECASE)

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
                result["sigma_b"] = (kappa - 1.0) * result.get("b0", 0.0)

    if "b0" not in result:
        raise RuntimeError(f"Could not parse b0 from {path}")
    result.setdefault("sigma_b", 0.0)
    return result


# ── signal plane loader (step3 logic, float-indexed) ─────────

def load_signal_plane_float(sig_csv: str, mx1: str) -> pd.DataFrame:
    df       = pd.read_csv(sig_csv)
    lam1_set = set()
    lam2_set = set()
    entries  = []

    for _, row in df.iterrows():
        name  = str(row["signal"]).strip()
        parts = name.split("_")
        if len(parts) != 4:
            continue
        _, f_mx1, f_lam1, f_lam2_raw = parts
        if f_mx1 != mx1:
            continue
        # strip trailing ".0" from lam2 part
        f_lam2 = f_lam2_raw[:-2] if f_lam2_raw.endswith(".0") else f_lam2_raw

        lam1_f = lam_to_float(f_lam1)
        lam2_f = lam_to_float(f_lam2)
        s0     = float(row["sg after"])

        lam1_set.add(lam1_f)
        lam2_set.add(lam2_f)
        entries.append((lam1_f, lam2_f, s0))

    if not entries:
        raise RuntimeError(f"No signal entries for mx1={mx1} in {sig_csv}")

    lam1_arr = sorted(lam1_set)
    lam2_arr = sorted(lam2_set)
    plane    = pd.DataFrame(np.nan, index=lam2_arr, columns=lam1_arr)
    for lam1_f, lam2_f, s0 in entries:
        plane.loc[lam2_f, lam1_f] = s0
    return plane


# ── Asimov significance ──────────────────────────────────────
# ── Asimov significance ──────────────────────────────────────

def z_asimov(s: float, b: float, sigma_b: float = 0.0) -> float:
    """
    Asimov expected discovery significance.

    sigma_b == 0  →  교과서 Eq. 3.9 (stat-only):
        Z = sqrt(2 * [(s+b)*ln(1 + s/b) - s])

    sigma_b > 0   →  Cowan et al. EPJC 71 (2011) 1554, Eq. 97:
        Z = sqrt(2 * [(s+b)*ln((s+b)(b+σ²)) / (b²+(s+b)σ²))
                      - (b²/σ²)*ln(1 + σ²s / (b(b+σ²)))])
    """
    if s <= 0.0 or b <= 0.0:
        return 0.0

    if sigma_b <= 0.0:
        # stat-only
        return math.sqrt(max(0.0, 2.0 * ((s + b) * math.log(1.0 + s / b) - s)))

    # with background systematic
    sb  = sigma_b * sigma_b          # σ_b²
    spb = s + b                      # s + b
    term1 = spb * math.log((spb * (b + sb)) / (b * b + spb * sb))
    term2 = (b * b / sb) * math.log(1.0 + sb * s / (b * (b + sb)))
    return math.sqrt(max(0.0, 2.0 * (term1 - term2)))


def build_z_plane(sig_plane: pd.DataFrame,
                  b0: float,
                  sigma_b: float = 0.0) -> pd.DataFrame:
    z_plane = sig_plane.copy()
    for lam2 in sig_plane.index:
        for lam1 in sig_plane.columns:
            s0 = sig_plane.loc[lam2, lam1]
            z_plane.loc[lam2, lam1] = (
                z_asimov(float(s0), b0, sigma_b)
                if not np.isnan(s0) else np.nan
            )
    return z_plane
# ============================================================
# DATA LOADING
# ============================================================

def load_expected(lumi: int, mode: str) -> dict:
    """
    Returns { mx1: {"s_up": float, "r": float} } for the given mode.
    s_up = r × s0_ref  is the signal-yield threshold for the 95 % CL contour.
    """
    r_table = parse_resultcard(RESULTCARD, mode, MX1_LIST)
    r_by_mx1 = r_table.get(lumi, {})

    out = {}
    for mx1 in MX1_LIST:
        r_val = r_by_mx1.get(mx1)
        if r_val is None:
            print(f"[WARN] expected: r not in resultcard for "
                  f"lumi={lumi} mode={mode} mx1={mx1}")
            continue

        cut_tag   = CUT_TAG_MAP[mx1]
        card_path = _os.path.join(
            DATACARD_DIR,
            f"datacard_lumi{lumi}_mx1{mx1}_cut{cut_tag}_{mode}.txt"
        )
        s0 = get_s0_from_datacard(card_path)
        if s0 is None:
            print(f"[WARN] expected: s0 not found in {card_path}")
            continue

        s_up = r_val * s0
        sig_csv = _os.path.join(
            SIG_DIR_MAP[mx1], f"sig_lumi{lumi}_mx1{mx1}.csv"
        )
        if not _os.path.isfile(sig_csv):
            print(f"[WARN] expected: signal CSV not found: {sig_csv}")
            continue

        plane       = build_signal_plane(sig_csv, mx1, LAM1_LIST, LAM2_LIST)
        XI, YI, ZI  = interpolate_plane_str(plane)

        out[mx1] = {"r": r_val, "s0": s0, "s_up": s_up,
                    "interp": (XI, YI, ZI)}
        print(f"  [expected] mx1={mx1}  r={r_val:.4f}  "
              f"s0={s0:.4f}  s_up={s_up:.4f}")

    return out


MODE_LABEL = {
    "none": "stat only (no syst)",
    "stats": "stat + bkg stat",
    "sys1":  "stat + sys1",
    "sys2":  "stat + sys2",
    "sys3":  "stat + sys3",
}

def load_discovery(lumi: int) -> dict:
    out = {}
    for mx1 in MX1_LIST:
        cut_tag  = CUT_TAG_MAP[mx1]
        card_name = (f"datacard_lumi{lumi}_mx1{mx1}"
                     f"_cut{cut_tag}_stats.txt")
        card_path = _os.path.join(DATACARD_DIR, card_name)

        if not _os.path.isfile(card_path):
            print(f"[WARN] discovery: stats datacard not found: {card_path}")
            continue

        card_data = parse_stats_datacard(card_path)
        b0        = card_data["b0"]
        sigma_b   = card_data["sigma_b"]          # ← 추가

        sig_csv = _os.path.join(
            SIG_DIR_MAP[mx1], f"sig_lumi{lumi}_mx1{mx1}.csv"
        )
        if not _os.path.isfile(sig_csv):
            print(f"[WARN] discovery: signal CSV not found: {sig_csv}")
            continue

        sig_plane    = load_signal_plane_float(sig_csv, mx1)
        z_plane      = build_z_plane(sig_plane, b0, sigma_b)  # ← sigma_b 전달
        XI, YI, ZI   = interpolate_plane_float(z_plane)

        z_vals = z_plane.to_numpy(dtype=float).flatten()
        z_vals = z_vals[np.isfinite(z_vals)]
        print(f"  [discovery] mx1={mx1}  b0={b0:.2f}  "
              f"sigma_b={sigma_b:.2f}  "                       # ← 로그 추가
              f"Z range=[{z_vals.min():.2f}, {z_vals.max():.2f}]")

        out[mx1] = {"b0": b0, "sigma_b": sigma_b,             # ← 저장
                     "z_interp": (XI, YI, ZI)}

    return out
# ============================================================
# PLOTTING
# ============================================================

def _style_axes(ax, log_scale: bool):
    ax.set_xlabel(r"$\lambda_{1}$", fontsize=12)
    ax.set_ylabel(r"$\lambda_{2}$", fontsize=12)
    ax.set_xticks(X_TICKS)
    ax.set_yticks(Y_TICKS)

    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*X_LIM_LOG)
        ax.set_ylim(*Y_LIM_LOG)
        ax.minorticks_off()
        ax.get_xaxis().set_major_formatter(
            matplotlib.ticker.ScalarFormatter())
        ax.get_yaxis().set_major_formatter(
            matplotlib.ticker.ScalarFormatter())
    else:
        ax.set_xlim(*X_LIM_LIN)
        ax.set_ylim(*Y_LIM_LIN)


def make_combined_plot(lumi: int,
                       expected: dict,
                       discovery: dict,
                       mode: str = "stats",
                       log_scale: bool = LOG_SCALE) -> plt.Figure:
    """
    expected  : output of load_expected()
    discovery : output of load_discovery()
    """
    fig, ax = plt.subplots(figsize=(6, 5))

    # ── Hadronization region ─────────────────────────────────
    if SHOW_HADRONIZATION:
        # Single L-shaped polygon to avoid double-alpha at the overlap corner
        _large = 2.0   # safely beyond any axis limit
        had_poly = mpatches.Polygon(
            [
                (0,              0),
                (_large,         0),
                (_large,         HAD_REGION_Y),
                (HAD_REGION_X,   HAD_REGION_Y),
                (HAD_REGION_X,   _large),
                (0,              _large),
            ],
            closed=True,
            color=HAD_COLOR, alpha=HAD_ALPHA, zorder=0,
        )
        ax.add_patch(had_poly)

    # ── Contours ─────────────────────────────────────────────
    dual_handles = []   # list of (solid_line, dashed_line) per mass
    mass_labels  = []

    for mx1 in MX1_LIST:
        color = COLOR_MAP.get(mx1, "black")
        plotted_solid  = False
        plotted_dashed = False

        # Solid: 95 % CL expected
        if mx1 in expected:
            XI, YI, ZI = expected[mx1]["interp"]
            s_up        = expected[mx1]["s_up"]
            try:
                ax.contour(XI, YI, ZI, levels=[s_up],
                           colors=[color], linewidths=2.0, linestyles="-",
                           zorder=2)
                plotted_solid = True
            except Exception as e:
                print(f"[WARN] expected contour failed mx1={mx1}: {e}")

        # Dashed: discovery Z = Z_THRESHOLD σ
        if mx1 in discovery:
            XI, YI, ZI = discovery[mx1]["z_interp"]
            try:
                ax.contour(XI, YI, ZI, levels=[Z_THRESHOLD],
                           colors=[color], linewidths=1.5, linestyles="--",
                           zorder=2)
                plotted_dashed = True
            except Exception as e:
                print(f"[WARN] discovery contour failed mx1={mx1}: {e}")

        if plotted_solid or plotted_dashed:
            h_solid  = Line2D([0], [0], color=color, lw=2.0, ls="-")
            h_dashed = Line2D([0], [0], color=color, lw=1.5, ls="--")
            dual_handles.append((h_solid, h_dashed))
            mass_labels.append(
                rf"$M_{{X_1}}$ = {MX1_LABELS.get(mx1, mx1)} TeV"
            )

    # ── Legend ───────────────────────────────────────────────
    # Header entry: gray solid = 95% CL, gray dashed = 5σ
    h_header = (
        Line2D([0], [0], color="gray", lw=2.0, ls="-"),
        Line2D([0], [0], color="gray", lw=1.5, ls="--"),
    )
    header_label = (
        rf"95% CL"
        rf"$\;\;|\;\;${Z_THRESHOLD:.0f}$\sigma$"
        rf"$\quad m_{{X_1}}$ [TeV]"
    )

    all_handles = [h_header] + dual_handles
    all_labels  = [header_label] + mass_labels

    if SHOW_HADRONIZATION:
        had_patch = mpatches.Patch(
            color=HAD_COLOR, alpha=HAD_ALPHA, label=HAD_LEGEND_LABEL
        )
        all_handles.append(had_patch)
        all_labels.append(HAD_LEGEND_LABEL)

    ax.legend(
        all_handles, all_labels,
        handler_map={tuple: HandlerTuple(ndivide=None, pad=0.5)},
        frameon=False,
        loc=LEG_LOC,
        fontsize=8,
    )

    # ── Axes styling ─────────────────────────────────────────
    _style_axes(ax, log_scale)

    # ── Luminosity annotation ─────────────────────────────────
    ax.text(
        LUMI_POS[0], LUMI_POS[1],
        rf"{lumi} fb$^{{-1}}$",
        transform=ax.transAxes, fontsize=9, ha="right",
    )
    mode_label = MODE_LABEL.get(mode, mode)
    ax.text(
        0.02, 1.01,
        f"syst: {mode_label}",
        transform=ax.transAxes, fontsize=7, ha="left", color="dimgray",
    )

    plt.tight_layout()
    return fig


# ============================================================
# MAIN
# ============================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="Combined 95% CL expected + discovery contour plotter"
    )
    p.add_argument("--lumi", type=int, nargs="+",
                   help="Luminosities to process (default: LUMI_LIST in CONFIG)")
    p.add_argument("--mode", nargs="+",
                   choices=["none", "stats", "sys1", "sys2", "sys3"],
                   help="Systematic modes to process (default: all in MODE_LIST)")
    p.add_argument("--log", action="store_true",
                   help="Also save the log-scale version in addition to the "
                        "scale set by LOG_SCALE in CONFIG")
    p.add_argument("--show", action="store_true",
                   help="Display interactive plot window")
    return p.parse_args()


def main():
    args      = parse_args()
    lumi_run  = args.lumi or LUMI_LIST
    mode_run  = args.mode or MODE_LIST

    # Collect which scales to produce:
    #   always produce whatever LOG_SCALE says; --log adds the other scale too.
    scales_to_run = {LOG_SCALE}
    if args.log:
        scales_to_run.add(not LOG_SCALE)   # add the opposite scale
    scales_to_run = sorted(scales_to_run)  # False (linear) before True (log)

    _os.makedirs(OUT_DIR, exist_ok=True)

    for lumi in lumi_run:
        print(f"\n{'='*60}")
        print(f"  Lumi = {lumi} fb-1")
        print(f"{'='*60}")

        # Discovery contour is mode-independent — load once per lumi
        print("\n[Discovery significance]")
        discovery = load_discovery(lumi)

        for mode in mode_run:
            print(f"\n{'─'*60}")
            print(f"  mode = {mode}")
            print(f"{'─'*60}")

            print("\n[Expected 95% CL]")
            expected = load_expected(lumi, mode)

            if not expected and not discovery:
                print(f"[WARN] No data for lumi={lumi} mode={mode}, skipping.")
                continue

            for log_scale in scales_to_run:
                scale_tag = "log" if log_scale else "linear"
                print(f"\n  -- scale = {scale_tag} --")

                fig   = make_combined_plot(lumi, expected, discovery,
                                           mode=mode, log_scale=log_scale)
                fname = _os.path.join(OUT_DIR,
                                      f"combined_lumi{lumi}_{mode}_{scale_tag}.png")
                fig.savefig(fname, dpi=DPI)
                print(f"[SAVE] {fname}")

                if args.show:
                    plt.show()
                plt.close(fig)

    print("\n[DONE]")


if __name__ == "__main__":
    main()
