#!/usr/bin/env python3
"""
SampleByCheck_entryOnly.py
--------------------------
현재 작업 환경(PrepareBDTdatas/postprocessing/root/<version>)에서
각 .root 파일의 entry 수만 확인하여 CSV로 저장한다.

Usage:
  python3 SampleByCheck_entryOnly.py --ver v2 --step 1
  python3 SampleByCheck_entryOnly.py --ver v2 --step 2
  python3 SampleByCheck_entryOnly.py --ver v2 --step 2 --lam-values 0.03,0.05,0.07
"""

import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict

# ── argparse ─────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Check entry counts of .root files in postprocessing/root/<version>"
)
parser.add_argument(
    "--ver", required=True,
    help="version directory under ../postprocessing/root/ (e.g. v2)"
)
parser.add_argument(
    "--data", required=True,
    help="version directory under ../postprocessing/root/ (e.g. v2)"
)
parser.add_argument(
    "--step", required=True, choices=["1", "2"],
    help="1: count entries and save CSV, 2: summarize selected signal grid"
)
parser.add_argument(
    "--lam-values", default="0.1,0.3,0.5",
    help="comma-separated lam1/lam2 values to keep in step2 (default: 0.03,0.05,0.07)"
)
args = parser.parse_args()

# ── 경로 설정 ─────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
IN_DIR = (SCRIPT_DIR / "../postprocessing/root" / args.ver / args.data).resolve()
#IN_DIR = (SCRIPT_DIR / "../postprocessing/root-800M-0p5" / args.ver / args.data).resolve()
OUT_CSV = IN_DIR / f"SampleByCheck_entryOnly_{args.ver}.csv"

# ── ROOT import ───────────────────────────────────────────────
def import_root():
    try:
        import ROOT
        ROOT.gROOT.SetBatch(True)
        ROOT.gErrorIgnoreLevel = ROOT.kError
        return ROOT
    except ImportError:
        print("[ERROR] ROOT (PyROOT) not available.")
        sys.exit(1)

# ── 유틸 ──────────────────────────────────────────────────────
TREE_CANDIDATES = [
    "Events", "events", "tree", "Tree", "nominal", "ntuple",
    "Delphes", "MyAnalysis", "AnalysisTree"
]
def norm_token(tok: str) -> str:
    """
    filename token normalize
    예:
      '0-04.0' -> '0.04'
      '0-06.0' -> '0.06'
      '1-0'    -> '1'
      '1-0.0'  -> '1'
      '0-03'   -> '0.03'
    """
    tok = tok.replace(".root", "")

    # 마지막 '.0' 제거
    if tok.endswith(".0"):
        tok = tok[:-2]

    # '-'를 decimal point처럼 사용
    tok = tok.replace("-", ".")

    try:
        val = float(tok)
        return f"{val:g}"
    except ValueError:
        return tok
def get_entry_count(ROOT, filepath: Path):
    """
    ROOT 파일을 열어 TTree entry 수만 반환.
    - 성공: (entry, tree_name)
    - 실패: (-1, reason)
    """
    try:
        rfile = ROOT.TFile.Open(str(filepath), "READ")
        if not rfile or rfile.IsZombie():
            return -1, "ZOMBIE"

        # 1) 후보 이름 우선 검색
        for tname in TREE_CANDIDATES:
            tree = rfile.Get(tname)
            if tree and hasattr(tree, "GetEntries"):
                n = int(tree.GetEntries())
                rfile.Close()
                return n, tname

        # 2) top-level key에서 첫 TTree 탐색
        keys = rfile.GetListOfKeys()
        if keys:
            for key in keys:
                obj = key.ReadObj()
                if obj and obj.InheritsFrom("TTree"):
                    n = int(obj.GetEntries())
                    tname = key.GetName()
                    rfile.Close()
                    return n, tname

        rfile.Close()
        return -1, "NO_TREE"

    except Exception as e:
        return -1, f"ERROR:{e}"

def parse_signal_filename(fname: str):
    """
    sel_Signal_1-5_0-05_0-04.0_v2.root
      -> mass='1.5', lam1='0.05', lam2='0.04'

    형식이 아니면 None 반환
    """
    if not fname.startswith("sel_Signal_") or not fname.endswith(".root"):
        return None

    base = fname[:-5]  # remove .root
    parts = base.split("_")

    # 기대 형식:
    # ['sel', 'Signal', mass, lam1, lam2, ver]
    if len(parts) != 6:
        return None
    if parts[0] != "sel" or parts[1] != "Signal":
        return None

    mass = norm_token(parts[2])
    lam1 = norm_token(parts[3])
    lam2 = norm_token(parts[4])
    ver  = parts[5]

    return mass, lam1, lam2, ver

# ── step1 ─────────────────────────────────────────────────────
def step1():
    print(f"\n{'='*70}")
    print(" SampleByCheck (entry-only) - current workspace version")
    print(f" Input Dir : {IN_DIR}")
    print(f" Output CSV: {OUT_CSV}")
    print(f"{'='*70}\n")

    if not IN_DIR.is_dir():
        print(f"[ERROR] Directory not found: {IN_DIR}")
        sys.exit(1)

    ROOT = import_root()

    root_files = sorted([
        p for p in IN_DIR.iterdir()
        if p.is_file() and p.suffix == ".root"
    ])

    if not root_files:
        print(f"[WARN] No .root files found in {IN_DIR}")
        sys.exit(0)

    print(f"Found {len(root_files)} .root files\n")

    fmt = "{:<55} {:>12}  {}"
    print(fmt.format("FileName", "entry", "TreeName/Status"))
    print("-" * 95)

    rows = []
    for fpath in root_files:
        entry, tree_name = get_entry_count(ROOT, fpath)

        rows.append({
            "FileName": fpath.name,
            "entry": entry,
            "tree": tree_name,
        })

        print(fmt.format(fpath.name, entry, tree_name))

    with open(OUT_CSV, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["FileName", "entry", "TreeNameOrStatus"])
        for r in rows:
            writer.writerow([r["FileName"], r["entry"], r["tree"]])

    print(f"\nCSV saved: {OUT_CSV}")

# ── step2 ─────────────────────────────────────────────────────
def step2():
    print("=" * 20, " Step2: Signal grid summary ", "=" * 20)

    if not OUT_CSV.is_file():
        print(f"[ERROR] CSV not found. Run step1 first: {OUT_CSV}")
        sys.exit(1)

    lam_keep = {norm_token(x.strip()) for x in args.lam_values.split(",") if x.strip()}
    if not lam_keep:
        print("[ERROR] Empty --lam-values")
        sys.exit(1)

    grid = defaultdict(lambda: defaultdict(int))

    with open(OUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = row["FileName"]

            parsed = parse_signal_filename(fname)
            if parsed is None:
                continue

            try:
                entry = int(row["entry"])
            except Exception:
                continue

            if entry < 0:
                continue

            mass, lam1, lam2, ver = parsed

            if lam1 not in lam_keep or lam2 not in lam_keep:
                continue

            grid[mass][(lam1, lam2)] += entry

    if not grid:
        print("[WARN] No matching signal files found for requested lam-values.")
        print(f"       lam-values = {sorted(lam_keep, key=float)}")
        return

    lam_list = sorted(lam_keep, key=float)

    print(f"\n[INFO] keeping lam values: {', '.join(lam_list)}")

    for mass in sorted(grid.keys(), key=float):
        print(f"\n[mass = {mass}]")
        print(" " * 12 + "  ".join([f"lam2={l2:>8}" for l2 in lam_list]))
        print("-" * (16 + 14 * len(lam_list)))

        for l1 in lam_list:
            row = [f"lam1={l1:>8}"]
            for l2 in lam_list:
                row.append(f"{grid[mass].get((l1, l2), 0):>12}")
            print("  ".join(row))

# ── main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    if args.step == "1":
        step1()
    elif args.step == "2":
        step2()


