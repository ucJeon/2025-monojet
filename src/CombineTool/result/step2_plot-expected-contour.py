#!/usr/bin/env python3
"""
step2_plot-expected-contour.py (updated)
-----------------------------------------
수정 사항: 
- 그리드 근사치 대신 1D 선형 보간을 통한 정밀한 lam_crit 산출
- 최신 BDT 결과 경로 반영 (SPLIT 디렉토리)
"""

# ============================================================
# ██████████████████████  CONFIG  ████████████████████████████
# ============================================================

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import mplhep as hep
hep.style.use("CMS")
# ── Input Paths ──────────────────────────────────────────────

RESULTCARD   = _os.path.join(_HERE, "resultcard_expected.txt")

DATACARD_DIR = ("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
                "CombineTool/datacards")

SIG_BASE     = ("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
                "BDT_cut/out")

# Per-mass signal-CSV directories and cut tags
LOG_SCALE = True           # default scale; --log CLI flag adds the other scale

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

COLOR_MAP  = {
    "1-0": "cornflowerblue",
    "1-5": "goldenrod",
    "2-0": "coral",
    "2-5": "#8B0000",
}

X_TICKS   = [0.1, 0.3, 0.5, 0.7, 1.0]
Y_TICKS   = [0.1, 0.3, 0.5, 0.7, 1.0]
X_LIM_LOG = (0.03, 1.0)
Y_LIM_LOG = (0.04, 1.0)
X_LIM_LIN = (0.03, 1.0)
Y_LIM_LIN = (0.04, 1.0)

LEG_LOC  = "upper right"   # legend anchor
LUMI_POS = (0.98, 1.01)    # axes-fraction coords for luminosity text

DPI     = 200
OUT_DIR = _os.path.join(_HERE, "plots_expected")


# ── Physics Configuration ────────────────────────────────────

LUMI_LIST        = [300, 3000]
DEFAULT_MX1_LIST = ["1-0", "1-5", "2-0", "2-5"]

MASS_POINTS = [
    ("MX10", "1-0", 1000, "0p1050"),
    ("MX15", "1-5", 1500, "0p1350"),
    ("MX20", "2-0", 2000, "0p1440"),
    ("MX25", "2-5", 2500, "0p1520"),
]

MODES_ALL = [
    ("none",  "No uncertainty"),
    ("stats", "BKG stat only"),
    ("sys1",  "stats + xsec (10%)"),
    ("sys2",  "stats + xsec + JES (5%)"),
    ("sys3",  "stats + xsec + JES + MET (4%)"),
]

# λ grid (for contour)
LAM1_LIST = ["0-03", "0-05", "0-07", "0-08", "0-1", "0-15", "0-2", "0-3", "0-4", "0-5", "0-6", "0-7", "0-8", "0-9", "1-0"]
LAM2_LIST = ["0-04", "0-06", "0-08", "0-1", "0-15", "0-2", "0-3", "0-4", "0-5", "0-6", "0-7", "0-8", "0-9", "1-0"]

# λ grid (for interpolation scan)
LAM1_GRID = [0.03, 0.05, 0.07, 0.08, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
LAM2_GRID = [0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

LAM1_REF = 0.50  # fixed when scanning lam2_crit
LAM2_REF = 0.50  # fixed when scanning lam1_crit

# ── Hadronization Regions 설정 ─────────────────────────────────────
# x: lambda1 하한선 (이 값보다 작으면 Hadronization 발생)
# y: lambda2 하한선 (이 값보다 작으면 Hadronization 발생)
# --- HAD_REGIONS 설정 업데이트 (각 MX1 색상과 매칭) ---
# alpha는 Polygon 자체의 투명도이며, hatching 농도는 '...' 등으로 조절 가능합니다.
HAD_REGIONS = {
    # "1-0": {"x": 0.05, "y": 0.07, "show": True, "color": COLOR_MAP["1-0"], "hatch": ""},
    "1-0": {"x": 0.05, "y": 0.07, "show": True, "color": "#C7C7C7", "hatch": ""},
    # "1-5": {"x": 0.040, "y": 0.057, "show": False, "color": COLOR_MAP["1-5"], "hatch": "////"},
    "1-5": {"x": 0.040, "y": 0.057, "show": True, "color": "#616161", "hatch": "///"},
    # 2.0, 2.5 도 필요시 추가
}

# ── Plotting & Interp ─────────────────────────────────────────

INTERP_METHOD = "cubic"
INTERP_FACTOR = 100
LOG_SCALE     = True
COLOR_MAP     = {"1-0": "cornflowerblue", "1-5": "goldenrod", "2-0": "coral", "2-5": "#8B0000"}
OUT_DIR       = _os.path.join(_HERE, "plots_expected")
DPI           = 300

LEG_LOC  = "upper right"   # legend anchor
LUMI_POS = (0.98, 1.01)    # axes-fraction coords for luminosity text

# ============================================================
# ████████████████  END OF CONFIG  ███████████████████████████
# ============================================================

import argparse, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from scipy.interpolate import RegularGridInterpolator, RectBivariateSpline, interp1d

# --- Helpers ---
def lam_to_float(v: str) -> float:
    return float(v.replace("-", "."))

def _fill_nan_nearest(Z: np.ndarray) -> np.ndarray:
    from scipy.interpolate import NearestNDInterpolator
    mask = np.isfinite(Z)
    if mask.all(): return Z
    rows, cols = np.indices(Z.shape)
    interp = NearestNDInterpolator(list(zip(rows[mask], cols[mask])), Z[mask])
    Z_filled = Z.copy()
    nan_rows, nan_cols = np.where(~mask)
    Z_filled[nan_rows, nan_cols] = interp(nan_rows, nan_cols)
    return Z_filled

def interpolate_plane_str(plane: pd.DataFrame, factor: int = INTERP_FACTOR, method: str = INTERP_METHOD):
    x = np.array([lam_to_float(v) for v in plane.columns], dtype=float)
    y = np.array([lam_to_float(v) for v in plane.index], dtype=float)
    Z = _fill_nan_nearest(plane.to_numpy(dtype=float))

    xi = np.linspace(x.min(), x.max(), len(x) * factor)
    yi = np.linspace(y.min(), y.max(), len(y) * factor)
    XI, YI = np.meshgrid(xi, yi)

    if method == "cubic":
        spline = RectBivariateSpline(y, x, Z)
        ZI = spline(yi, xi)
    else:
        interp = RegularGridInterpolator((y, x), Z, method="linear", bounds_error=False, fill_value=None)
        ZI = interp(np.column_stack([YI.ravel(), XI.ravel()])).reshape(XI.shape)
    return XI, YI, ZI

def parse_resultcard(path, modes, mx1_list):
    mx1_map = {f"{float(m.replace('-', '.')):.1f}": m for m in mx1_list}
    result = {}
    current_lumi = None
    mode_cols = {}
    
    if not _os.path.exists(path): return {}

    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            m_lumi = re.search(r"lumi=(\d+)", line, re.I)
            if m_lumi:
                current_lumi = int(m_lumi.group(1))
                mode_cols = {}
                result.setdefault(current_lumi, {m: {} for m in modes})
                continue
            if current_lumi is None or not line.startswith("|"): continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if not mode_cols:
                for mode in modes:
                    if mode in cells: mode_cols[mode] = cells.index(mode)
                continue
            try:
                mx1_key = f"{float(cells[0]):.1f}"
                mx1 = mx1_map.get(mx1_key)
                if mx1:
                    for mode, idx in mode_cols.items():
                        result[current_lumi][mode][mx1] = float(cells[idx])
            except: continue
    return result

def get_s0_from_datacard(card_path):
    try:
        with open(card_path) as f:
            for line in f:
                if line.startswith("rate"): return float(line.split()[1])
    except: return None

# --- Critical Value Logic ---

def find_critical(scan_arr, s0_arr, s_up):
    """선형 보간을 통해 s_up을 만족하는 coupling 값을 정밀하게 계산"""
    if len(scan_arr) < 2: return None
    # yield가 coupling 증가에 따라 증가하는 경우 가정 (상황에 따라 flip 필요할 수 있음)
    if s_up < s0_arr.min(): return f"<{scan_arr[0]:.2f}"
    if s_up > s0_arr.max(): return f">{scan_arr[-1]:.2f}"
    
    try:
        # 1D Interpolation: s0(yield) -> scan_val(coupling)
        f = interp1d(s0_arr, scan_arr, kind='linear')
        return float(f(s_up))
    except:
        return None

def get_s0_slice(df, mx1, fixed_name, fixed_val, scan_grid, col="sg after"):
    scan_vals, s0_vals = [], []
    pattern = re.compile(rf"Signal_{mx1}_([\d-]+)_([\d-]+)\.0")
    for _, row in df.iterrows():
        match = pattern.match(str(row["signal"]))
        if not match: continue
        l1, l2 = lam_to_float(match.group(1)), lam_to_float(match.group(2))
        
        if fixed_name == "lam2" and abs(l2 - fixed_val) < 1e-5:
            scan_vals.append(l1); s0_vals.append(float(row[col]))
        elif fixed_name == "lam1" and abs(l1 - fixed_val) < 1e-5:
            scan_vals.append(l2); s0_vals.append(float(row[col]))
            
    if scan_vals:
        res = sorted(zip(scan_vals, s0_vals))
        return np.array([x[0] for x in res]), np.array([x[1] for x in res])
    return np.array([]), np.array([])

# ── signal-yield plane builder ───────────────────────────────

def _get_signal_value(df: pd.DataFrame, mx1: str,
                      lam1: str, lam2: str,
                      col: str = "sg after") -> float:
    key = f"Signal_{mx1}_{lam1}_{lam2}.0"
    s   = df.loc[df["signal"].eq(key), col]
    return float(s.iat[0]) if len(s) else np.nan


def build_plane(sig_csv: str, mx1: str,
                lam1_list: list[str], lam2_list: list[str],
                col: str = "sg after") -> pd.DataFrame:
    df    = pd.read_csv(sig_csv)
    plane = pd.DataFrame(index=lam2_list, columns=lam1_list, dtype=float)
    for lam1 in lam1_list:
        for lam2 in lam2_list:
            plane.loc[lam2, lam1] = _get_signal_value(df, mx1, lam1, lam2, col)
    return plane


# --- Plotting ---
def _style_axes(ax, log_scale: bool) -> None:
    """Apply common axis styling."""
    ax.set_xlabel(r"$\lambda_{1}$", fontsize=16, labelpad=10)
    ax.set_ylabel(r"$\lambda_{2}$", fontsize=16, labelpad=10)
    ax.tick_params(axis='both', which='major', labelsize=13, top=True, right=True)
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
        ax.get_xaxis().set_minor_formatter(ticker.NullFormatter()) # 지저분한 보조 눈금 라벨 제거
        ax.get_yaxis().set_minor_formatter(ticker.NullFormatter())

        ## ax.minorticks_off()
        #ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        #ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    else:
        ax.set_xlim(*X_LIM_LIN)
        ax.set_ylim(*Y_LIM_LIN)

def _draw_hadronization(ax):
    """
    각 MX1 색상에 맞춰 hatching이 들어간 영역을 그림.
    """
    _large = 5.0
    legend_entries = []

    for mx1_key, cfg in HAD_REGIONS.items():
        if not cfg["show"]: continue
        
        hx, hy = cfg["x"], cfg["y"]
        # Polygon 생성 (색상은 연하게 alpha=0.2, hatching 추가)
        # _prefix = 0.05
        # poly = mpatches.Polygon(
        #     [(0,0), 
        #      (_large      , 0), 
        #      (_large      , hy          ), 
        #      (hx          , hy          ), 
        #      (hx          , _large      ), 
        #      (0, _large      )],
        #     closed=True,
        #     #facecolor=cfg["color"],
        #     facecolor="none",
        #     edgecolor=cfg["color"], # 빗금 색상
        #     alpha=0.8,             # 전체적인 투명도
        #     hatch=cfg["hatch"],     # 빗금 패턴 (약간만 보이게)
        #     linewidth=1,            # 테두리는 없앰
        #     zorder=1,
        # )
        _prefix = 0.005
        if mx1_key == "1-0":
            poly = mpatches.Polygon(
                [(0       , 0),
                 (_large  , 0),
                 (_large  , hy          ),
                 (hx      , hy          ),
                 (hx      , _large      ),
                 (0       , _large      )],
                closed=True,
                #facecolor=cfg["color"],
                facecolor=cfg["color"],
                edgecolor="none", # 빗금 색상
                alpha=0.5,             # 전체적인 투명도
                hatch=cfg["hatch"],     # 빗금 패턴 (약간만 보이게)
                linewidth=0,            # 테두리는 없앰
                zorder=1,
            )
        elif mx1_key == "1-5":
            poly = mpatches.Polygon(
                [(0       , 0),
                 (_large  , 0),
                 (_large  , hy          ),
                 (hx      , hy          ),
                 (hx      , _large      ),
                 (0       , _large      )],
                closed=True,
                #facecolor=cfg["color"],
                facecolor="none",
                edgecolor=cfg["color"], # 빗금 색상
                alpha=0.5,             # 전체적인 투명도
                hatch=cfg["hatch"],     # 빗금 패턴 (약간만 보이게)
                linewidth=0,            # 테두리는 없앰
                zorder=1,
            )
        # 2. 경계선 강조 (데이터 좌표를 직접 사용하는 방식)
        # vlines(x, ymin, ymax): x 위치에 hy부터 차트 끝(_large)까지 세로선
        #ax.vlines(x=hx, ymin=hy, ymax=_large, color=cfg["color"], 
        #          lw=1.5, ls='-', alpha=0.9, zorder=2)
        
        # hlines(y, xmin, xmax): y 위치에 hx부터 차트 끝(_large)까지 가로선
        #ax.hlines(y=hy, xmin=hx, xmax=_large, color=cfg["color"], 
        #          lw=1.5, ls='-', alpha=0.9, zorder=2)
        ax.add_patch(poly)
        
        # 범례용 패치 (빗금 포함)
        #legend_entries.append((
        #    mpatches.Patch(facecolor=cfg["color"], alpha=0.3, hatch=cfg["hatch"], edgecolor=cfg["color"]),
        #    f"Hadronization ($m_{{X_1}}$={MX1_LABELS[mx1_key]} TeV)"
        #))
        # 범례용 패치 (마찬가지로 채우기 없이 빗금만)
        legend_entries.append((
            mpatches.Patch(facecolor='none', hatch=cfg["hatch"], edgecolor=cfg["color"], alpha=0.6),
            f"$m_{{X_1}} = {MX1_LABELS[mx1_key]}$ TeV"
        ))
    return legend_entries

def make_limit_plot(lumi, limits, mode, sig_dir_map, lam1_list, lam2_list, log_scale=LOG_SCALE, col: str = "sg after") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7, 7)) # 가독성을 위해 살짝 키움

    # 1. Hadronization 그리기 (Hadronization entries를 가져옴)
    had_entries = _draw_hadronization(ax)

    # 2. Contour 그리기 및 Proxy 생성
    proxy_lines, mass_labels = [], []
    
    for mx1 in DEFAULT_MX1_LIST:
        vals = limits.get(mx1)
        if not vals or vals.get("s_up") is None:
            continue

        s_up = vals["s_up"]
        r_val = vals["r"]

        # 데이터 경로 확인 (연구실 서버 구조 반영)
        sig_dir = sig_dir_map.get(mx1)
        if not sig_dir or not _os.path.isdir(sig_dir):
            print(f"[WARN] mx1={mx1}: 경로를 찾을 수 없음 {sig_dir}")
            continue

        sig_csv = _os.path.join(sig_dir, f"sig_lumi{lumi}_mx1{mx1}.csv")
        if not _os.path.isfile(sig_csv):
            print(f"[WARN] CSV 파일 없음: {sig_csv}")
            continue

        # Signal-yield plane 빌드
        # build_plane은 CSV에서 (lam2, lam1) 매트릭스를 생성함
        plane = build_plane(sig_csv, mx1, lam1_list, lam2_list, col=col)
        
        # 2D 보간 수행 (RectBivariateSpline 사용)
        XI, YI, ZI = interpolate_plane_str(plane)

        # 컨투어 라인 그리기 (배경 Hadronization보다 위인 zorder=2)
        color = COLOR_MAP.get(mx1, "black")
        try:
            # s_up(상한선)과 일치하는 Yield 지점을 찾아 실선으로 연결
            cs = ax.contour(XI, YI, ZI, levels=[s_up],
                            colors=[color], linewidths=2.0, linestyles="-", zorder=2)
            
            # 범례 구성을 위한 프록시 객체 및 라벨 추가
            # (각 mx1 색상별 실선을 범례에 표시하기 위함)
            proxy_lines.append(Line2D([0], [0], color=color, lw=2.0, ls="-"))
            mass_labels.append(rf"$m_{{X_1}}$ = {MX1_LABELS.get(mx1, mx1)} TeV")
            
        except Exception as e:
            print(f"[WARN] contour 생성 실패 (mx1={mx1}): {e}")
            continue
    # 3. 범례 통합 구성
    title_line = Line2D([0], [0], color='none') # 제목용 핸들은 투명하게
    title_label = r"$\mathbf{Median\ Expected\ 95\%\ CL}$"

    had_title_handle = Line2D([0], [0], color='none') # 제목용 핸들은 투명하게
    had_title_label = r"$\mathbf{Hadronization\ Region}$"

    all_handles = ([title_line] + proxy_lines + 
                   [Line2D([0], [0], color='none')] + 
                   [had_title_handle] + [h for h, _ in had_entries])

    all_labels = ([title_label] + mass_labels + 
                  [""] + 
                  [had_title_label] + [lbl for _, lbl in had_entries])

    # 범례 생성
    leg = ax.legend(
        all_handles, all_labels,
        frameon=False,
        loc="upper right",
        bbox_to_anchor=(0.999, 0.999),
        fontsize=11,
        labelspacing=0.3,
        handletextpad=0.5,
        borderpad=1.0,
        handlelength=1.0 # 핸들 길이를 일정하게 고정
    )

    # --- [핵심 수정 부분] 타이틀 왼쪽 강제 정렬 ---
    # 범례의 텍스트 객체들을 순회하며 제목만 왼쪽으로 밀어줍니다.
    for text in leg.get_texts():
        txt = text.get_text()
        if "Median Expected" in txt or "Hadronization Region" in txt:
            # 텍스트를 왼쪽(핸들이 있던 자리)으로 이동시킴
            # -20 ~ -30 사이의 값을 조정하여 위치를 맞추세요.
            text.set_position((-100, 0)) 
            text.set_ha('left') # 왼쪽 정렬 강화

    # 4. 축 스타일링 및 스케일 설정
    _style_axes(ax, log_scale)

    # 5. Luminosity 및 Systematic Mode 정보 텍스트 추가
    #ax.text(
    #    LUMI_POS[0], LUMI_POS[1],
    #    rf"{lumi} fb$^{{-1}}$",
    #    transform=ax.transAxes, fontsize=10, ha="right", fontweight='bold'
    #)
    
    mode_label = dict(MODES_ALL).get(mode, mode)
    #ax.text(
    #    0.02, 1.01,
    #    f"Syst: {mode_label}",
    #    transform=ax.transAxes, fontsize=8, ha="left", color="dimgray"
    #)
    ax.text(
        LUMI_POS[0], LUMI_POS[1],
        rf"{lumi} fb$^{{-1}}$ (13 TeV)",
        transform=ax.transAxes, fontsize=14, ha="right", fontweight='bold'
    )

    plt.tight_layout()
    return fig
# --- Main Logic ---

def main():
    _os.makedirs(OUT_DIR, exist_ok=True)
    r_table = parse_resultcard(RESULTCARD, [m for m, _ in MODES_ALL], DEFAULT_MX1_LIST)
    
    for lumi in LUMI_LIST:
        if lumi not in r_table: continue
        print(f"\n>>> Processing Lumi: {lumi} fb-1")
        
        for mode, m_lab in MODES_ALL:
            r_by_mx1 = r_table[lumi].get(mode, {})
            limits = {}
            print(f"  Mode: {mode}")
            
            for mx1 in DEFAULT_MX1_LIST:
                r_val = r_by_mx1.get(mx1)
                if r_val is None: continue
                card = _os.path.join(DATACARD_DIR, f"datacard_lumi{lumi}_mx1{mx1}_cut{CUT_TAG_MAP[mx1]}_{mode}.txt")
                s0 = get_s0_from_datacard(card)
                if s0: limits[mx1] = {"r": r_val, "s0": s0, "s_up": r_val * s0}

            # Plot
            fig = make_limit_plot(lumi, limits, mode, SIG_DIR_MAP, LAM1_LIST, LAM2_LIST)
            fig.savefig(_os.path.join(OUT_DIR, f"limit_{mode}_lumi{lumi}.png"), dpi=DPI)
            fig.savefig(_os.path.join(OUT_DIR, f"limit_{mode}_lumi{lumi}.eps"))
            plt.close(fig)

            # Critical Values Table (Markdown Style)
            print(f"| MX1 | lam1_crit (fixed lam2={LAM2_REF}) | lam2_crit (fixed lam1={LAM1_REF}) |")
            print("|---|---|---|")
            for mx1 in DEFAULT_MX1_LIST:
                if mx1 not in limits: continue
                df = pd.read_csv(_os.path.join(SIG_DIR_MAP[mx1], f"sig_lumi{lumi}_mx1{mx1}.csv"))
                
                # Lam1 Scan
                l1_a, s0_l1 = get_s0_slice(df, mx1, "lam2", LAM2_REF, LAM1_GRID)
                l1_c = find_critical(l1_a, s0_l1, limits[mx1]["s_up"])
                
                # Lam2 Scan
                l2_a, s0_l2 = get_s0_slice(df, mx1, "lam1", LAM1_REF, LAM2_GRID)
                l2_c = find_critical(l2_a, s0_l2, limits[mx1]["s_up"])
                
                def fmt(v): return f"{v:.3f}" if isinstance(v, float) else str(v)
                print(f"| {MX1_LABELS[mx1]} | {fmt(l1_c)} | {fmt(l2_c)} |")

if __name__ == "__main__":
    main()
