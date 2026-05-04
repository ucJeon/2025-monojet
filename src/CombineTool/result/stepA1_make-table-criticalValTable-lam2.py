#!/usr/bin/env python3
"""
make_table_44.py
----------------
Table 4.4 스타일:
  lam1 = LAM1_REF (default 0.15) 고정 →
  systematic 단계별 lam2_critical 출력.

출력 예:
  L = 300 fb⁻¹              | 1.0 TeV | 1.5 TeV | 2.0 TeV | 2.5 TeV
  stats only                 | < 0.xx  | < 0.xx  | < 0.xx  | < 0.xx
  stats + xsec (15%)         | < 0.xx  | ...
  stats + xsec + btag (6%)   | < 0.xx  | ...
  stats + xsec + btag + JES  | < 0.xx  | ...
  ... + MET                  | < 0.xx  | ...

Usage:
  python3 make_table_44.py
  python3 make_table_44.py --lam1-ref 0.15
  python3 make_table_44.py --fmt latex --out table44.tex
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

# ============================================================
# CONFIG
# ============================================================

LAM1_REF_DEFAULT = 0.15

LUMI_LIST = [300, 3000]

MASS_POINTS = [
    ("MX10", "1-0", 1000, "0p1050"),
    ("MX15", "1-5", 1500, "0p1350"),
    ("MX20", "2-0", 2000, "0p1440"),
    ("MX25", "2-5", 2500, "0p1520"),
]

LAM2_GRID = [
    0.04, 0.06, 0.08, 0.10, 0.15,
    0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00,
]

SIG_BASE = ("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
            "BDT_cut/out")
SIG_DIR_MAP = {
    "1-0": f"{SIG_BASE}/v2_2500_4_0p1050",
    "1-5": f"{SIG_BASE}/v2_2500_4_0p1350",
    "2-0": f"{SIG_BASE}/v2_2500_4_0p1440",
    "2-5": f"{SIG_BASE}/v2_2500_4_0p1520",
}

DATACARD_DIR = ("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
                "CombineTool/datacards")

# 모드 순서 및 행 레이블
MODES = [
    ("stats", "stats only"),
    ("sys1",  r"stats $+$ $x_{\rm sec}$ (10\%)"),
    ("sys2",  r"stats $+$ $x_{\rm sec}$ $+$ JES (5\%)"),
    ("sys3",  r"stats $+$ $x_{\rm sec}$ $+$ JES $+$ MET (4\%)"),
]

MODES_PLAIN = [
    ("stats", "stats only"),
    ("sys1",  "stats + xsec (10%)"),
    ("sys2",  "stats + xsec + JES (5%)"),
    ("sys3",  "stats + xsec + JES + MET (4%)"),
]

# ============================================================


def lam_dash(v: float) -> str:
    return str(v).replace(".", "-")


def get_s0_from_datacard(card_path: str) -> float | None:
    try:
        with open(card_path) as f:
            for line in f:
                if line.strip().startswith("rate"):
                    return float(line.split()[1])
    except Exception:
        pass
    return None


def get_r_from_resultcard(path: str, lumi: int, mx1: str, mode: str) -> float | None:
    """
    resultcard.txt (make_table.py --out 출력) 에서
    (lumi, mx1, mode) 에 해당하는 r 값을 반환.
    """
    mx1_float_str = f"{float(mx1.replace('-', '.')):.1f}"
    lumi_re = re.compile(r"##\s+Summary:\s+lumi=(\d+)")
    sep_re  = re.compile(r"^:?-+:?$")

    current_lumi: int | None = None
    mode_col: int | None = None

    try:
        with open(path) as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue

                m_l = lumi_re.search(line)
                if m_l:
                    current_lumi = int(m_l.group(1))
                    mode_col = None
                    continue

                if current_lumi != lumi or not line.startswith("|"):
                    continue

                cells = [c.strip() for c in line.split("|")[1:-1]]
                if not cells:
                    continue

                # 구분자 행 skip
                if all(sep_re.match(c) for c in cells):
                    continue

                # 헤더 행: mode 컬럼 인덱스 확정
                if mode_col is None:
                    if mode in cells:
                        mode_col = cells.index(mode)
                    continue

                # 데이터 행
                if len(cells) > mode_col:
                    try:
                        if f"{float(cells[0]):.1f}" == mx1_float_str:
                            return float(cells[mode_col])
                    except ValueError:
                        pass
    except FileNotFoundError:
        return None

    return None


def get_lam2_critical(df: pd.DataFrame, mx1: str,
                      lam1_ref: float, s_up: float,
                      col: str = "sg after") -> float | None:
    """lam1 = lam1_ref 고정, lam2 스캔 → lam2_critical."""
    lam1_d = lam_dash(lam1_ref)

    lam2_vals, s0_vals = [], []
    for lam2 in LAM2_GRID:
        lam2_d = lam_dash(lam2)
        key    = f"Signal_{mx1}_{lam1_d}_{lam2_d}.0"
        row    = df.loc[df["signal"].eq(key), col]
        if len(row):
            lam2_vals.append(lam2)
            s0_vals.append(float(row.iat[0]))

    lam2_arr = np.array(lam2_vals)
    s0_arr   = np.array(s0_vals)

    if len(lam2_arr) < 2:
        return None
    if s_up < s0_arr.min() or s_up > s0_arr.max():
        return None

    try:
        f = interp1d(s0_arr, lam2_arr, kind="linear",
                     bounds_error=False,
                     fill_value=(lam2_arr[0], lam2_arr[-1]))
        return float(f(s_up))
    except Exception:
        return None


def compute_cell(lumi: int, mx1: str, cut_tag: str,
                 mode: str, lam1_ref: float) -> float | None:
    """단일 셀 (lumi, mx1, mode) → lam2_critical."""
    card_path = os.path.join(
        DATACARD_DIR,
        f"datacard_lumi{lumi}_mx1{mx1}_cut{cut_tag}_{mode}.txt"
    )
    s0 = get_s0_from_datacard(card_path)
    if s0 is None:
        print(f"[WARN] s0 not found: {card_path}")
        return None

    resultcard = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resultcard_expected.txt"
    )
    r = get_r_from_resultcard(resultcard, lumi, mx1, mode)
    if r is None:
        print(f"[WARN] r not found: lumi={lumi} mx1={mx1} mode={mode}")
        return None

    s_up = r * s0

    sig_dir = SIG_DIR_MAP.get(mx1)
    sig_csv = os.path.join(sig_dir, f"sig_lumi{lumi}_mx1{mx1}.csv")
    if not os.path.isfile(sig_csv):
        print(f"[WARN] sig CSV not found: {sig_csv}")
        return None

    df = pd.read_csv(sig_csv)
    return get_lam2_critical(df, mx1, lam1_ref, s_up)


def fmt_val(v: float | None) -> str:
    return f"{v:.2f}" if v is not None else "---"
    # return f"{v}" if v is not None else "---"


# ============================================================
# 출력
# ============================================================

def build_data(lumi: int, lam1_ref: float) -> dict:
    """data[mode][mx1] = lam2_critical (float or None)"""
    data = {}
    for mode, _ in MODES_PLAIN:
        data[mode] = {}
        for _, mx1, _, cut_tag in MASS_POINTS:
            data[mode][mx1] = compute_cell(lumi, mx1, cut_tag, mode, lam1_ref)
    return data


def print_markdown(lumi: int, lam1_ref: float, data: dict):
    mx1_list  = [mp[1] for mp in MASS_POINTS]
    col_heads = "".join(f" {m.replace('-','.')} TeV |" for m in mx1_list)

    print(f"\n### L = {lumi} fb⁻¹  (λ₁ = {lam1_ref} fixed)")
    print(f"| Uncertainty |{col_heads}")
    print("|---|" + "---|" * len(mx1_list))

    for mode, label in MODES_PLAIN:
        row = f"| {label} |"
        for mx1 in mx1_list:
            v = data[mode][mx1]
            row += f" < {fmt_val(v)} |"
        print(row)


def print_latex(lumi: int, lam1_ref: float, data: dict) -> str:
    mx1_list = [mp[1] for mp in MASS_POINTS]
    n_col    = 1 + len(mx1_list)
    col_spec = "l" + "c" * len(mx1_list)

    col_header = " & ".join(
        f"${m.replace('-','.')}$~TeV" for m in mx1_list)

    rows_tex = []
    for (mode, label_tex), (_, label_plain) in zip(MODES, MODES_PLAIN):
        vals = " & ".join(
            f"$< {fmt_val(data[mode][mx1])}$" for mx1 in mx1_list)
        rows_tex.append(f"    {label_tex} & {vals} \\\\")

    body = "\n".join(rows_tex)

    return (
        rf"""  \begin{{tabular}}{{{col_spec}}}
    \hline\hline
    $\mathcal{{L}} = {lumi}~\mathrm{{fb}}^{{-1}}$
      & {col_header} \\
    \hline
{body}
    \hline\hline
  \end{{tabular}}"""
    )


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lam1-ref", type=float, default=LAM1_REF_DEFAULT,
                        help=f"고정할 lam1 값 (default: {LAM1_REF_DEFAULT})")
    parser.add_argument("--lumi",     type=int, nargs="+", default=LUMI_LIST)
    parser.add_argument("--fmt",      default="markdown",
                        choices=["markdown", "latex"])
    parser.add_argument("--out",      default=None,
                        help="저장할 .tex 파일 경로 (없으면 stdout)")
    args = parser.parse_args()

    latex_blocks = []

    for lumi in args.lumi:
        print(f"[INFO] computing lumi={lumi}, lam1_ref={args.lam1_ref} ...")
        data = build_data(lumi, args.lam1_ref)

        if args.fmt == "latex":
            latex_blocks.append(print_latex(lumi, args.lam1_ref, data))
        else:
            print_markdown(lumi, args.lam1_ref, data)

    if args.fmt == "latex":
        caption = (
            rf"  \caption{{"
            rf"Constraints on $\lambda_2$ with $\lambda_1 < {args.lam1_ref}$ "
            rf"under various systematic uncertainties, "
            rf"for $M_{{X_1}} \in \{{1.0,\,1.5,\,2.0,\,2.5\}}$~TeV. "
            rf"The 95\% CL expected upper limits are obtained "
            rf"using the asymptotic CL$_s$ method.}}"
        )
        label = r"  \label{tab:lam2_critical_syst}"

        full_tex = (
            "\\begin{table}[htbp]\n"
            "  \\centering\n"
            + "\n\n  \\vspace{1.2em}\n\n".join(latex_blocks)
            + "\n\n" + caption + "\n" + label + "\n"
            + "\\end{table}\n"
        )

        if args.out:
            with open(args.out, "w") as f:
                f.write(full_tex)
            print(f"[DONE] saved: {args.out}")
        else:
            print(full_tex)


if __name__ == "__main__":
    main()
