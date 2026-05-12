#!/usr/bin/env python3
from __future__ import annotations

import os
import argparse

# ============================================================
# CONFIG
# ============================================================

LUMI_LIST = [300, 3000]

MASS_POINTS = [
    # (MX_tag,  mx_dash, mass,  cut_tag)
    ("MX10", "1-0", 1000, "0p1050"),
    ("MX15", "1-5", 1500, "0p1350"),
    ("MX20", "2-0", 2000, "0p1440"),
    ("MX25", "2-5", 2500, "0p1520"),
]

# 모드 순서 및 설명
MODES = {
    "none":  "No uncertainty",
    "stats": "BKG stat only",
    "sys1":  "stats + xsec_sig (10%)",
    "sys2":  "stats + xsec_sig + JES (5%)",
    "sys3":  "stats + xsec_sig + JES + MET (4%)",
}

# ============================================================


def get_expected_limit(root_path: str, quantile: float = 0.5) -> float | None:
    """AsymptoticLimits ROOT 파일에서 expected upper limit 추출."""
    import ROOT
    ROOT.gROOT.SetBatch(True)

    f = ROOT.TFile.Open(root_path)
    if not f or f.IsZombie():
        return None

    tree = f.Get("limit")
    if not tree:
        f.Close()
        return None

    result = None
    for entry in tree:
        if abs(entry.quantileExpected - quantile) < 1e-4:
            result = float(entry.limit)
            break

    f.Close()
    return result


def get_s0_from_datacard(card_path: str) -> float | None:
    """datacard txt에서 signal rate (s0) 추출."""
    try:
        with open(card_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("rate"):
                    parts = line.split()
                    return float(parts[1])
    except Exception:
        pass
    return None


def get_root_path(base_dir: str, lumi: int, mx_tag: str, mass: int, mode: str) -> str:
    """ROOT 파일 경로 반환."""
    root_name = (f"higgsCombine.Lumi{lumi}.{mx_tag}.{mode}"
                 f".xsfit.AsymptoticLimits.mH{mass}.root")
    return os.path.join(base_dir, root_name)


def get_card_path(base_dir: str, lumi: int, mx_dash: str,
                  cut_tag: str, mode: str) -> str:
    """datacard 경로 반환."""
    card_name = f"datacard_lumi{lumi}_mx1{mx_dash}_cut{cut_tag}_{mode}.txt"
    return os.path.join(base_dir, "datacards", card_name)


# ============================================================
# 테이블 빌더
# ============================================================

def build_markdown_table(lumi: int, mode: str, base_dir: str) -> str:
    """단일 (lumi, mode) 마크다운 테이블."""
    lines = []
    lines.append(f"### lumi={lumi} fb⁻¹ | {mode}: {MODES[mode]}")
    lines.append("| $M_{X_1}$ [TeV] | 95% CL (median) | $s_0$ |")
    lines.append("|:---:|:---:|:---:|")

    for mx_tag, mx_dash, mass, cut_tag in MASS_POINTS:
        mx_str    = mx_dash.replace("-", ".")
        root_path = get_root_path(base_dir, lumi, mx_tag, mass, mode)
        card_path = get_card_path(base_dir, lumi, mx_dash, cut_tag, mode)

        r_exp = get_expected_limit(root_path)
        r_str = f"r < {r_exp:.4f}" if r_exp is not None else "N/A"

        s0    = get_s0_from_datacard(card_path)
        s0_str = f"{s0:.4f}" if s0 is not None else "N/A"

        lines.append(f"| {mx_str} | {r_str} | {s0_str} |")

    return "\n".join(lines)


def build_summary_markdown(lumi: int, modes: list, base_dir: str) -> str:
    """
    lumi 하나에 대해 모든 mode를 열로 나열하는 요약 테이블.
    행: MX1, 열: mode별 median r
    """
    lines = []
    lines.append(f"## Summary: lumi={lumi} fb⁻¹ (Expected median r)")

    # 헤더
    header = "| $M_{X_1}$ [TeV] |" + "".join(f" {m} |" for m in modes)
    sep    = "|:---:|" + "".join(":---:|" for _ in modes)
    lines.append(header)
    lines.append(sep)

    for mx_tag, mx_dash, mass, cut_tag in MASS_POINTS:
        mx_str = mx_dash.replace("-", ".")
        row = f"| {mx_str} |"
        for mode in modes:
            root_path = get_root_path(base_dir, lumi, mx_tag, mass, mode)
            r_exp = get_expected_limit(root_path)
            r_str = f"{r_exp:.4f}" if r_exp is not None else "N/A"
            row += f" {r_str} |"
        lines.append(row)

    return "\n".join(lines)


def build_latex_table(lumi: int, modes: list, base_dir: str) -> str:
    """LaTeX booktabs 형식 요약 테이블."""
    col_spec = "c" * (1 + len(modes))
    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"  \centering")
    lines.append(
        f"  \\caption{{Expected 95\\% CL upper limits on signal strength "
        f"($\\mathcal{{L}} = {lumi}$~fb$^{{-1}}$)}}"
    )
    lines.append(f"  \\label{{tab:limit_syst_{lumi}}}")
    lines.append(f"  \\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"    \hline\hline")

    # 헤더
    header = "    $M_{X_1}$ [TeV]"
    for m in modes:
        header += f" & {m}"
    header += r" \\"
    lines.append(header)
    lines.append(r"    \hline")

    for mx_tag, mx_dash, mass, cut_tag in MASS_POINTS:
        mx_str = mx_dash.replace("-", ".")
        row = f"    ${mx_str}$"
        for mode in modes:
            root_path = get_root_path(base_dir, lumi, mx_tag, mass, mode)
            r_exp = get_expected_limit(root_path)
            r_str = f"${r_exp:.4f}$" if r_exp is not None else "---"
            row += f" & {r_str}"
        row += r" \\"
        lines.append(row)

    lines.append(r"    \hline\hline")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ============================================================
# z_asymp_result_{mode}.txt 저장
# ============================================================

def build_result_txt_block(lumi: int, mode: str, base_dir: str) -> list:
    """
    단일 lumi 블록을 z_asymp_result 포맷 라인 목록으로 반환.
    형식:
      {lumi} fb-1
      |95% CL (exp. median)|s0|
      |---|---|
      |r < {r}|{s0}|
      ...
    """
    lines = [
        f"{lumi} fb-1",
        "|95% CL (exp. median)|s0|",
        "|---|---|",
    ]
    for mx_tag, mx_dash, mass, cut_tag in MASS_POINTS:
        root_path = get_root_path(base_dir, lumi, mx_tag, mass, mode)
        card_path = get_card_path(base_dir, lumi, mx_dash, cut_tag, mode)

        r_exp  = get_expected_limit(root_path)
        s0     = get_s0_from_datacard(card_path)

        r_str  = f"{r_exp:.4f}"  if r_exp is not None else "N/A"
        s0_str = f"{s0:.4f}"    if s0    is not None else "N/A"
        lines.append(f"|r < {r_str}|{s0_str}|")

    return lines


def save_result_txt(modes: list, base_dir: str):
    """
    각 mode에 대해 z_asymp_result_{mode}.txt 를 base_dir 에 저장.
    result/ 디렉터리의 make_table_criticalValTable*.py 가 기대하는 포맷.
    """
    for mode in modes:
        all_lines = []
        for lumi in LUMI_LIST:
            all_lines += build_result_txt_block(lumi, mode, base_dir)
            all_lines.append("")   # 블록 사이 빈 줄

        out_path = os.path.join(base_dir, "result", f"z_asymp_result_{mode}.txt")
        with open(out_path, "w") as f:
            f.write("\n".join(all_lines))
        print(f"[DONE] saved: {out_path}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sys", default=None,
        choices=list(MODES.keys()),
        help="특정 모드만 출력 (default: 전체)"
    )
    parser.add_argument(
        "--lumi", type=int, default=None,
        choices=[300, 3000],
        help="특정 lumi만 출력 (default: 전체)"
    )
    parser.add_argument(
        "--fmt", default="markdown",
        choices=["markdown", "latex"],
        help="출력 형식 (default: markdown)"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="모드별 요약 테이블 출력 (전체 모드 비교)"
    )
    parser.add_argument(
        "--out", default=None,
        help="출력 파일 경로 (없으면 stdout)"
    )
    parser.add_argument(
        "--save-result", action="store_true",
        help=(
            "z_asymp_result_{mode}.txt 파일을 저장 "
            "(result/ 디렉터리의 make_table_criticalValTable*.py 입력용). "
            "--sys 로 모드를 지정하면 해당 모드만, 없으면 전체 모드 저장."
        )
    )
    args = parser.parse_args()

    # base_dir   = os.path.dirname(os.path.abspath(__file__))
    # base_dir   = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/CombineTool/"
    base_dir   = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/CombineTool/outputs-xsfit/"
    lumi_list  = [args.lumi] if args.lumi else LUMI_LIST
    mode_list  = [args.sys]  if args.sys  else list(MODES.keys())

    # --save-result: z_asymp_result_{mode}.txt 저장 후 종료
    if args.save_result:
        save_result_txt(mode_list, base_dir)
        return

    sections = []

    for lumi in lumi_list:
        if args.summary or args.sys is None:
            # 전체 모드 요약 테이블
            if args.fmt == "latex":
                sections.append(build_latex_table(lumi, mode_list, base_dir))
            else:
                sections.append(build_summary_markdown(lumi, mode_list, base_dir))
        else:
            # 특정 모드 단일 테이블
            sections.append(build_markdown_table(lumi, args.sys, base_dir))

    output = "\n\n".join(sections) + "\n"

    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"[DONE] 저장: {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
