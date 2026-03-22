#!/usr/bin/env python3
"""
make_summary_table.py
---------------------
--version v2 --ntree 2000 --maxdepth 4 를 받아,
out/{version}_{ntree}_{maxdepth}_*/ 폴더를 스캔하고
각 mx1에 대해 cut별 테이블을 생성한다.

테이블 컬럼:
  cut | bkg_N | bkg_Sigma_N | bkg_Sigma_N/N | sig_N | sig_Sigma_N | sig_Sigma_N/N

- lumi  = 300 고정
- sig   = lam1=REF_LAM1, lam2=REF_LAM2 (default: 0.15, 0.15) 단일 benchmark point
- mx1별로 별도 CSV + 터미널 출력

Usage:
  python3 make_summary_table.py --version v2 --ntree 2000 --maxdepth 4
  python3 make_summary_table.py --version v2 --ntree 2000 --maxdepth 4 --mx1 1-0
  python3 make_summary_table.py --version v2 --ntree 2000 --maxdepth 4 --lam1 0.2 --lam2 0.2
"""

import os
import glob
import argparse
import numpy as np
import pandas as pd

# ============================================================
# config
# ============================================================

BASE_OUT_DIR = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_cut/out"
LUMI         = 300
MX1_LIST     = ["1-0", "1-5", "2-0", "2-5"]
REF_LAM1     = "0-15"   # 기준 lam1 (0.15)
REF_LAM2     = "0-15"   # 기준 lam2 (0.15)

# ============================================================


def cut_tag_to_float(tag: str) -> float:
    """
    "0p1300"  →  0.1300
    "m1p0000" → -1.0
    """
    if tag.startswith("m"):
        return -float(tag[1:].replace("p", "."))
    return float(tag.replace("p", "."))


def scan_folders(base_dir: str, version: str, ntree: int, maxdepth: int) -> list:
    """
    out/{version}_{ntree}_{maxdepth}_*/ 패턴으로 폴더 스캔.
    반환: [(cut_float, folder_path), ...]  cut 오름차순 정렬
    """
    prefix  = f"{version}_{ntree}_{maxdepth}_"
    pattern = os.path.join(base_dir, prefix + "*")
    folders = sorted(glob.glob(pattern))

    result = []
    for folder in folders:
        tag = os.path.basename(folder)[len(prefix):]
        try:
            cut = cut_tag_to_float(tag)
            result.append((cut, folder))
        except ValueError:
            print(f"[WARN] cannot parse cut from folder: {folder}")

    result.sort(key=lambda x: x[0])
    return result


def load_bkg_total(folder: str, lumi: int, mx1: str) -> dict | None:
    """
    bkg_lumi{lumi}_mx1{mx1}.csv 에서 TOTAL 행 읽기.
    """
    csv_path = os.path.join(folder, f"bkg_lumi{lumi}_mx1{mx1}.csv")
    if not os.path.isfile(csv_path):
        return None

    df    = pd.read_csv(csv_path)
    total = df[df["sample"] == "TOTAL"]
    if total.empty:
        return None

    b0      = float(total.iloc[0]["b0"])
    sigma_b = float(total.iloc[0]["sigmab0"])
    ratio   = sigma_b / b0 if b0 > 0 else float("nan")

    return {"N": b0, "Sigma_N": sigma_b, "Sigma_N/N": ratio}


def load_sig_at_benchmark(folder: str, lumi: int, mx1: str,
                          ref_lam1: str = REF_LAM1,
                          ref_lam2: str = REF_LAM2) -> dict | None:
    """
    sig_lumi{lumi}_mx1{mx1}.csv 에서
    lam1 == ref_lam1 AND lam2 == ref_lam2 인 단일 행을 읽는다.

    signal 컬럼 형식: Signal_{mx1}_{lam1}_{lam2}.0
    ref_lam1/2 포맷:  "0-15" (하이픈)
    """
    csv_path = os.path.join(folder, f"sig_lumi{lumi}_mx1{mx1}.csv")
    if not os.path.isfile(csv_path):
        return None

    df = pd.read_csv(csv_path)
    if df.empty:
        return None

    # lam1, lam2 파싱: Signal_1-0_0-15_0-15.0
    def extract_lams(sig_name: str):
        parts = str(sig_name).strip().split("_")
        if len(parts) != 4:
            return "", ""
        lam1_tag = parts[2]                   # "0-15"
        lam2_tag = parts[3].replace(".0", "") # "0-15"
        return lam1_tag, lam2_tag

    lams = df["signal"].apply(extract_lams).tolist()
    df["lam1_tag"] = [x[0] for x in lams]
    df["lam2_tag"] = [x[1] for x in lams]

    df_ref = df[(df["lam1_tag"] == ref_lam1) & (df["lam2_tag"] == ref_lam2)]

    if df_ref.empty:
        print(f"[WARN] lam1={ref_lam1}, lam2={ref_lam2} not found in {csv_path}")
        return None

    row   = df_ref.iloc[0]
    sg    = float(row["sg after"])
    err   = float(row["sg after err"])
    ratio = err / sg if sg > 0 else float("nan")

    return {"N": sg, "Sigma_N": err, "Sigma_N/N": ratio}


def make_table(version: str, ntree: int, maxdepth: int,
               mx1: str,
               ref_lam1: str = REF_LAM1,
               ref_lam2: str = REF_LAM2,
               base_dir: str = BASE_OUT_DIR) -> pd.DataFrame:
    """한 mx1에 대한 cut별 summary table 생성."""
    folders = scan_folders(base_dir, version, ntree, maxdepth)

    if not folders:
        print(f"[WARN] no folders found for {version}_{ntree}_{maxdepth}_*")
        return pd.DataFrame()

    rows = []
    for cut, folder in folders:
        bkg = load_bkg_total(folder, LUMI, mx1)
        sig = load_sig_at_benchmark(folder, LUMI, mx1,
                                    ref_lam1=ref_lam1, ref_lam2=ref_lam2)

        row = {"cut": cut}

        if bkg:
            row["bkg_N"]         = bkg["N"]
            row["bkg_Sigma_N"]   = bkg["Sigma_N"]
            row["bkg_Sigma_N/N"] = bkg["Sigma_N/N"]
        else:
            row["bkg_N"] = row["bkg_Sigma_N"] = row["bkg_Sigma_N/N"] = float("nan")

        if sig:
            row["sig_N"]         = sig["N"]
            row["sig_Sigma_N"]   = sig["Sigma_N"]
            row["sig_Sigma_N/N"] = sig["Sigma_N/N"]
        else:
            row["sig_N"] = row["sig_Sigma_N"] = row["sig_Sigma_N/N"] = float("nan")

        rows.append(row)

    df = pd.DataFrame(rows, columns=[
        "cut",
        "bkg_N", "bkg_Sigma_N", "bkg_Sigma_N/N",
        "sig_N", "sig_Sigma_N", "sig_Sigma_N/N",
    ])
    return df


def print_table(df: pd.DataFrame, mx1: str, ref_lam1: str, ref_lam2: str):
    l1 = ref_lam1.replace("-", ".")
    l2 = ref_lam2.replace("-", ".")
    print(f"\n{'='*72}")
    print(f"  mx1={mx1}  lumi={LUMI} fb^-1  sig: lam1={l1}, lam2={l2}")
    print(f"{'='*72}")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version",  required=True, help="e.g. v2")
    parser.add_argument("--ntree",    required=True, type=int)
    parser.add_argument("--maxdepth", required=True, type=int)
    parser.add_argument("--mx1",      default=None,
                        choices=["1-0", "1-5", "2-0", "2-5"],
                        help="특정 mx1만. 없으면 전체 4개 각각 출력/저장.")
    parser.add_argument("--lam1",     default=None, type=float,
                        help="기준 lam1 float값 (default: 0.15)")
    parser.add_argument("--lam2",     default=None, type=float,
                        help="기준 lam2 float값 (default: 0.15)")
    parser.add_argument("--base_dir", default=BASE_OUT_DIR)
    parser.add_argument("--save",     action="store_true",
                        help="mx1별로 CSV 각각 저장")
    parser.add_argument("--save_dir", default=".",
                        help="저장 경로 (default: 현재 디렉토리)")
    args = parser.parse_args()

    # lam1, lam2 결정: float → "0-15" 형식
    ref_lam1 = f"{args.lam1:.2f}".replace(".", "-") if args.lam1 else REF_LAM1
    ref_lam2 = f"{args.lam2:.2f}".replace(".", "-") if args.lam2 else REF_LAM2

    targets = [args.mx1] if args.mx1 else MX1_LIST

    for mx1 in targets:
        df = make_table(args.version, args.ntree, args.maxdepth,
                        mx1=mx1, ref_lam1=ref_lam1, ref_lam2=ref_lam2,
                        base_dir=args.base_dir)

        if df.empty:
            print(f"[SKIP] mx1={mx1}: no data")
            continue

        print_table(df, mx1, ref_lam1, ref_lam2)

        if args.save:
            os.makedirs(args.save_dir, exist_ok=True)
            l1 = ref_lam1.replace("-", "p")
            l2 = ref_lam2.replace("-", "p")
            fname = os.path.join(
                args.save_dir,
                f"summary_{args.version}_{args.ntree}_{args.maxdepth}"
                f"_mx1{mx1}_lam1{l1}_lam2{l2}_lumi{LUMI}.csv"
            )
            df.to_csv(fname, index=False)
            print(f"[SAVED] {fname}")


if __name__ == "__main__":
    main()
