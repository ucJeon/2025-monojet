
#!/usr/bin/env python3
import os
import re
import glob
import math
import argparse
import numpy as np
import pandas as pd
import uproot


# ============================================================
# helpers
# ============================================================

def cut_to_tag(cut: float) -> str:
    """
    0.1300 → "0p1300"
    -1.0   → "m1p0000"
    """
    if cut < 0:
        return "m" + f"{abs(cut):.4f}".replace(".", "p")
    return f"{cut:.4f}".replace(".", "p")


def make_output_dir(base_dir: str, version: str, ntree: int, maxdepth: int, cut: float) -> str:
    """
    out/{version}_{ntree}_{maxdepth}_{cut_tag}/
    e.g. out/v2_2000_4_0p1300/
    """
    tag = f"{version}_{ntree}_{maxdepth}_{cut_to_tag(cut)}"
    path = os.path.join(base_dir, tag)
    os.makedirs(path, exist_ok=True)
    return path


def parse_signal_filename(path):
    base = os.path.basename(path)
    m = re.match(r"^sel_Signal_([^_]+)_([^_]+)_([^_]+)_([^\.]+)\.root$", base)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


def is_signal(path):
    return os.path.basename(path).startswith("sel_Signal_")


def event_weight(xs, ngen, lumi_fb):
    return lumi_fb * 1000.0 * xs / ngen


def compute_yield_and_err(root_file, lumi_fb, cut=None):
    with uproot.open(root_file) as f:
        tree = f["events"]
        arr  = tree.arrays(["bdt_response", "XS", "Ngen"], library="np")

    bdt  = arr["bdt_response"].astype(np.float64)
    xs   = arr["XS"].astype(np.float64)
    ngen = arr["Ngen"].astype(np.float64)
    w    = event_weight(xs, ngen, lumi_fb)

    mask = np.ones_like(bdt, dtype=bool) if cut is None else (bdt > cut)

    count = int(np.count_nonzero(mask))
    w_sel = w[mask]
    yld   = float(np.sum(w_sel))
    err   = float(np.sqrt(np.sum(w_sel ** 2)))

    return count, yld, err


# ============================================================
# background
# ============================================================

def process_background(input_dir, lumi_fb, cut, output_csv):
    files     = sorted(glob.glob(os.path.join(input_dir, "*.root")))
    bkg_files = [f for f in files if not is_signal(f)]

    rows          = []
    total_count   = 0
    total_yield   = 0.0
    total_err2    = 0.0

    for f in bkg_files:
        count, yld, err = compute_yield_and_err(f, lumi_fb, cut=cut)
        rows.append({
            "sample":  os.path.basename(f),
            "bdtcut":  cut,
            "count":   count,
            "b0":      yld,
            "sigmab0": err,
        })
        total_count += count
        total_yield += yld
        total_err2  += err ** 2

    rows.append({
        "sample":  "TOTAL",
        "bdtcut":  "",
        "count":   total_count,
        "b0":      total_yield,
        "sigmab0": math.sqrt(total_err2),
    })

    pd.DataFrame(rows).to_csv(output_csv, index=False)
    print(f"[SAVED] {output_csv}")


# ============================================================
# signal
# ============================================================

def process_signal(input_dir, lumi_fb, mx1, cut, output_csv):
    files     = sorted(glob.glob(os.path.join(input_dir, "*.root")))
    sig_files = [f for f in files if is_signal(f)]

    rows = []

    for f in sig_files:
        info = parse_signal_filename(f)
        if info is None:
            continue
        f_mx1, lam1, lam2, version = info
        if f_mx1 != mx1:
            continue

        count_before, y_before, err_before = compute_yield_and_err(f, lumi_fb, cut=None)
        count_after,  y_after,  err_after  = compute_yield_and_err(f, lumi_fb, cut=cut)
        acc = (y_after / y_before) if y_before > 0 else 0.0

        rows.append({
            "signal":        f"Signal_{f_mx1}_{lam1}_{lam2}",
            "BDT cut":       cut,
            "count before":  count_before,
            "sg before":     y_before,
            "sg before err": err_before,
            "count after":   count_after,
            "sg after":      y_after,
            "sg after err":  err_after,
            "sg acceptance": acc,
        })

    pd.DataFrame(rows).to_csv(output_csv, index=False)
    print(f"[SAVED] {output_csv}")


# ============================================================
# main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Compute yields after BDT cut")
    parser.add_argument("--input_dir",  required=True)
    parser.add_argument("--version",    required=True, help="e.g. v2, v21")
    parser.add_argument("--lumi",       type=float, required=True)
    parser.add_argument("--mx1",        required=True, choices=["1-0", "1-5", "2-0", "2-5"])
    parser.add_argument("--ntree",      required=True, type=int)
    parser.add_argument("--maxdepth",   required=True, type=int)
    parser.add_argument("--cut",        type=float, required=True,
                        help="BDT cut value (e.g. 0.13 or -1.0 for no cut)")
    parser.add_argument("--output_dir", required=True,
                        help="Base output dir (e.g. /path/to/BDT_cut/out)")
    args = parser.parse_args()

    # out/{version}_{ntree}_{maxdepth}_{cut_tag}/
    out_dir = make_output_dir(args.output_dir, args.version,
                              args.ntree, args.maxdepth, args.cut)

    lumi_tag = str(int(args.lumi))

    bkg_csv = os.path.join(out_dir, f"bkg_lumi{lumi_tag}_mx1{args.mx1}.csv")
    sig_csv = os.path.join(out_dir, f"sig_lumi{lumi_tag}_mx1{args.mx1}.csv")

    print("[INFO] configuration")
    print(f"  input_dir  = {args.input_dir}")
    print(f"  version    = {args.version}")
    print(f"  lumi       = {args.lumi}")
    print(f"  mx1        = {args.mx1}")
    print(f"  ntree      = {args.ntree}")
    print(f"  maxdepth   = {args.maxdepth}")
    print(f"  cut        = {args.cut:.4f}")
    print(f"  output_dir = {out_dir}")

    process_background(args.input_dir, args.lumi, args.cut, bkg_csv)
    process_signal(args.input_dir, args.lumi, args.mx1, args.cut, sig_csv)


if __name__ == "__main__":
    main()


