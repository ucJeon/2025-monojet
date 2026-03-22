#!/usr/bin/env python3
"""
run_plot.py
-----------
Usage:
  python3 run_plot.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300
  python3 run_plot.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --planes
  python3 run_plot.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --limits
  python3 run_plot.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --lam1plot
  python3 run_plot.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --show
  python3 run_plot.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --all
"""

import os
import sys
import argparse

# ============================================================
# USER CONFIG  ← BDT_cut base 경로만 여기서 수정
# ============================================================

BDT_CUT_BASE = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_cut/out"
LIMIT_BASE   = os.path.dirname(os.path.abspath(__file__))

LUMI_LIST = [300, 3000]
MX1_LIST  = ["1-0", "1-5", "2-0", "2-5"]

# ============================================================


def cut_to_tag(cut: float) -> str:
    if cut < 0:
        return "m" + f"{abs(cut):.4f}".replace(".", "p")
    return f"{cut:.4f}".replace(".", "p")


def build_plot_points(version: str, ntree: int, maxdepth: int, cut: float) -> list:
    """
    (lumi, mx1, csv_path) 리스트 생성.
    BDT_cut/out/{version}_{ntree}_{maxdepth}_{cut_tag}/sig_lumi{lumi}_mx1{mx1}.csv
    """
    model_tag = f"{version}_{ntree}_{maxdepth}_{cut_to_tag(cut)}"
    bdt_dir   = os.path.join(BDT_CUT_BASE, model_tag)

    points = []
    for lumi in LUMI_LIST:
        for mx1 in MX1_LIST:
            csv_path = os.path.join(bdt_dir, f"sig_lumi{lumi}_mx1{mx1}.csv")
            if not os.path.isfile(csv_path):
                print(f"[WARN] not found: {csv_path}")
                continue
            points.append((lumi, mx1, csv_path))

    return points


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version",  required=True)
    parser.add_argument("--ntree",    required=True, type=int)
    parser.add_argument("--maxdepth", required=True, type=int)
    parser.add_argument("--cut",      required=True, type=float,
                        help="BDT cut value (e.g. 0.1300)")
    parser.add_argument("--planes",   action="store_true",
                        help="plane heatmap (8개)")
    parser.add_argument("--limits",   action="store_true",
                        help="combined limit figure (4개)")
    parser.add_argument("--lam1plot", action="store_true",
                        help="lam1_critical vs BDT cut figure (2개)")
    parser.add_argument("--all",      action="store_true",
                        help="planes + limits + lam1plot 전부")
    parser.add_argument("--show",     action="store_true")
    args = parser.parse_args()

    # summary CSV 경로
    model_tag   = f"{args.version}_{args.ntree}_{args.maxdepth}"
    summary_csv = os.path.join(LIMIT_BASE, "results", model_tag, "limit_summary.csv")

    if not os.path.isfile(summary_csv):
        print(f"[WARN] summary CSV not found: {summary_csv}")
        print("       run run_asymptotic_all.sh first.")

    sys.path.insert(0, LIMIT_BASE)
    from plot import plot_all_planes, plot_all_limits
    from plot.lam1_vs_bdtcut import plot_all as plot_lam1_all

    # --all 이면 전부, 아무것도 안 주면 기본값 planes+limits
    if args.all:
        do_planes   = True
        do_limits   = True
        do_lam1plot = True
    elif not any([args.planes, args.limits, args.lam1plot]):
        do_planes   = True
        do_limits   = True
        do_lam1plot = False
    else:
        do_planes   = args.planes
        do_limits   = args.limits
        do_lam1plot = args.lam1plot

    print(f"[INFO] model     = {model_tag}")
    print(f"[INFO] cut       = {args.cut}")
    print(f"[INFO] summary   = {summary_csv}")
    print(f"[INFO] planes    = {do_planes}")
    print(f"[INFO] limits    = {do_limits}")
    print(f"[INFO] lam1plot  = {do_lam1plot}")

    # ---- planes ----
    if do_planes:
        plot_points = build_plot_points(args.version, args.ntree, args.maxdepth, args.cut)
        if not plot_points:
            print("[WARN] no sig CSV found for planes. skipping.")
        else:
            print("\n[PLANE] plotting planes ...")
            plot_all_planes(plot_points, summary_csv=summary_csv, show=args.show)

    # ---- limits ----
    if do_limits:
        plot_points = build_plot_points(args.version, args.ntree, args.maxdepth, args.cut)
        if not plot_points:
            print("[WARN] no sig CSV found for limits. skipping.")
        else:
            print("\n[LIMIT] plotting limits ...")
            plot_all_limits(plot_points, summary_csv=summary_csv, show=args.show)

    # ---- lam1 vs bdtcut ----
    if do_lam1plot:
        print("\n[LAM1] plotting lam1_critical vs BDT cut ...")
        plot_lam1_all(args.version, args.ntree, args.maxdepth, show=args.show)

    print("\n[DONE]")


if __name__ == "__main__":
    main()

