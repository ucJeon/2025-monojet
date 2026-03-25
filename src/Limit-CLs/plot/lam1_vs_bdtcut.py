"""
plot/lam1_vs_bdtcut.py
-----------------------
x축: BDT cut value
y축: lam2=0.15 에서 s_up 을 넘는 lam1 (critical lam1)

- 4개의 mx1 선 + ±1σ, ±2σ shaded band
- lumi=300, lumi=3000 각각 별도 플랏
"""

import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# ============================================================
# USER CONFIG  ← 여기서 조절
# ============================================================

BDT_CUT_BASE = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_cut/out"
LIMIT_BASE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

REF_LAM2  = "0-5"
LUMI_LIST = [300, 3000]
MX1_LIST  = ["1-0", "1-5", "2-0", "2-5"]

COLOR_MAP = {
    "1-0": "cornflowerblue",
    "1-5": "goldenrod",
    "2-0": "coral",
    "2-5": "#8B0000",
}

LINE_LW       = 1.8
MARKER        = "x"
MSIZE         = 6
BAND1_ALPHA   = 0.30   # ±1σ band 투명도
BAND2_ALPHA   = 0.15   # ±2σ band 투명도

OUTPUT_DIR = os.path.join(LIMIT_BASE, "limit_plots")
DPI        = 150

# ============================================================


def lam_to_float(v: str) -> float:
    return float(v.replace("-", "."))


def cut_to_tag(cut: float) -> str:
    if cut < 0:
        return "m" + f"{abs(cut):.4f}".replace(".", "p")
    return f"{cut:.4f}".replace(".", "p")


# ============================================================
# lam1_critical 계산
# ============================================================

def get_sig_vs_lam1(bdt_dir, lumi, mx1, ref_lam2=REF_LAM2):
    csv_path = os.path.join(bdt_dir, f"sig_lumi{lumi}_mx1{mx1}.csv")
    if not os.path.isfile(csv_path):
        return None, None
    df = pd.read_csv(csv_path)

    def extract_lams(sig_name):
        parts = str(sig_name).strip().split("_")
        if len(parts) != 4:
            return "", ""
        return parts[2], parts[3].replace(".0", "")

    lams = df["signal"].apply(extract_lams).tolist()
    df["lam1_tag"] = [x[0] for x in lams]
    df["lam2_tag"] = [x[1] for x in lams]
    df_ref = df[df["lam2_tag"] == ref_lam2].copy()
    if df_ref.empty:
        return None, None
    df_ref["lam1_float"] = df_ref["lam1_tag"].apply(lam_to_float)
    df_ref = df_ref.sort_values("lam1_float")
    return df_ref["lam1_float"].to_numpy(float), df_ref["sg after"].to_numpy(float)


def find_lam1_critical(lam1_arr, sg_arr, s_up):
    if s_up is None or not np.isfinite(s_up):
        return None
    if s_up < sg_arr[0] or s_up > sg_arr[-1]:
        return None
    try:
        f_inv = interp1d(sg_arr, lam1_arr, kind="linear", bounds_error=True)
        return float(f_inv(s_up))
    except Exception:
        return None


# ============================================================
# 데이터 수집
# ============================================================

def collect_points(version, ntree, maxdepth, lumi, summary_csv):
    """
    반환: {mx1: [{"cut": float, "med": float|None,
                  "m1": float|None, "p1": float|None,
                  "m2": float|None, "p2": float|None}, ...]}
    """
    if not os.path.isfile(summary_csv):
        print(f"[WARN] summary CSV not found: {summary_csv}")
        return {}

    df_sum = pd.read_csv(summary_csv)
    for col in ["lumi", "mx1", "version", "ntree", "maxdepth"]:
        df_sum[col] = df_sum[col].astype(str).str.strip()

    mask = (
        (df_sum["version"]  == str(version))  &
        (df_sum["ntree"]    == str(ntree))     &
        (df_sum["maxdepth"] == str(maxdepth))  &
        (df_sum["lumi"]     == str(lumi))
    )
    df_filt = df_sum[mask].copy()

    if df_filt.empty:
        print(f"[WARN] no entries for lumi={lumi}")
        return {}

    # band 컬럼 존재 여부 확인
    has_band = all(c in df_filt.columns for c in
                   ["s_up_m1", "s_up_p1", "s_up_m2", "s_up_p2"])

    result = {mx1: [] for mx1 in MX1_LIST}

    for _, row in df_filt.iterrows():
        mx1  = str(row["mx1"]).strip()
        cut  = float(row["cut"]) if str(row["cut"]).strip() != "" else None
        s_up = row.get("s_up")

        if cut is None or not np.isfinite(float(s_up) if s_up is not None else float("nan")):
            continue

        cut_tag = cut_to_tag(cut)
        bdt_dir = os.path.join(BDT_CUT_BASE,
                               f"{version}_{ntree}_{maxdepth}_{cut_tag}")

        lam1_arr, sg_arr = get_sig_vs_lam1(bdt_dir, int(lumi), mx1)
        if lam1_arr is None:
            continue

        # band s_up 값 읽기
        def _get(col):
            if not has_band:
                return None
            v = row.get(col)
            try:
                return float(v) if v is not None and str(v).strip() != "" else None
            except Exception:
                return None

        entry = {
            "cut": cut,
            "med": find_lam1_critical(lam1_arr, sg_arr, float(s_up)),
            "m1":  find_lam1_critical(lam1_arr, sg_arr, _get("s_up_m1")),
            "p1":  find_lam1_critical(lam1_arr, sg_arr, _get("s_up_p1")),
            "m2":  find_lam1_critical(lam1_arr, sg_arr, _get("s_up_m2")),
            "p2":  find_lam1_critical(lam1_arr, sg_arr, _get("s_up_p2")),
        }
        result[mx1].append(entry)

    for mx1 in result:
        result[mx1].sort(key=lambda x: x["cut"])

    return result


# ============================================================
# 플랏
# ============================================================

def plot_lam1_vs_bdtcut(version, ntree, maxdepth, lumi, summary_csv,
                        save=True, show=False):

    points = collect_points(version, ntree, maxdepth, lumi, summary_csv)
    if not any(points.values()):
        print(f"[SKIP] no data for lumi={lumi}")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_yscale("log")

    for mx1 in MX1_LIST:
        pts = points.get(mx1, [])
        if not pts:
            continue

        cuts = np.array([p["cut"] for p in pts])
        med  = np.array([p["med"] if p["med"] is not None else np.nan for p in pts])
        m1   = np.array([p["m1"]  if p["m1"]  is not None else np.nan for p in pts])
        p1   = np.array([p["p1"]  if p["p1"]  is not None else np.nan for p in pts])
        m2   = np.array([p["m2"]  if p["m2"]  is not None else np.nan for p in pts])
        p2   = np.array([p["p2"]  if p["p2"]  is not None else np.nan for p in pts])

        c     = COLOR_MAP.get(mx1, "black")
        label = rf"$M_{{X_1}}$ = {lam_to_float(mx1):.1f} TeV"

        # ±2σ band
        valid2 = np.isfinite(m2) & np.isfinite(p2)
        if valid2.any():
            ax.fill_between(cuts[valid2], m2[valid2], p2[valid2],
                            color=c, alpha=BAND2_ALPHA)

        # ±1σ band
        valid1 = np.isfinite(m1) & np.isfinite(p1)
        if valid1.any():
            ax.fill_between(cuts[valid1], m1[valid1], p1[valid1],
                            color=c, alpha=BAND1_ALPHA)

        # median line
        valid0 = np.isfinite(med)
        ax.plot(cuts[valid0], med[valid0],
                color=c, lw=LINE_LW, marker=MARKER, markersize=MSIZE, label=label)

    ax.set_xlabel("BDT cut value")
    ax.set_ylabel(
        rf"$\lambda_{{1}}^{{\rm crit}}$  "
        rf"($\lambda_2 = {lam_to_float(REF_LAM2):.2f}$, 95% CL)"
    )
    ax.set_title(
        rf"Expected limit: $\lambda_1$ vs BDT cut  "
        rf"($\mathcal{{L}}$ = {lumi} fb$^{{-1}}$)"
    )
    ax.legend(frameon=False, loc="best", fontsize=9)
    ax.text(0.98, 0.02, f"{version}, ntree={ntree}, maxdepth={maxdepth}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color="gray")

    plt.tight_layout()

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        fname = os.path.join(
            OUTPUT_DIR,
            f"lam1_vs_bdtcut_{version}_{ntree}_{maxdepth}_lumi{lumi}.png"
        )
        plt.savefig(fname, dpi=DPI)
        print(f"[SAVE] {fname}")

    if show:
        plt.show()

    plt.close()
    return fig


def plot_all(version, ntree, maxdepth, show=False):
    summary_csv = os.path.join(
        LIMIT_BASE, "results",
        f"{version}_{ntree}_{maxdepth}",
        "limit_summary.csv"
    )
    for lumi in LUMI_LIST:
        plot_lam1_vs_bdtcut(version, ntree, maxdepth,
                            lumi=lumi, summary_csv=summary_csv,
                            save=True, show=show)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version",  required=True)
    parser.add_argument("--ntree",    required=True, type=int)
    parser.add_argument("--maxdepth", required=True, type=int)
    parser.add_argument("--show",     action="store_true")
    args = parser.parse_args()
    plot_all(args.version, args.ntree, args.maxdepth, show=args.show)


