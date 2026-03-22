#!/usr/bin/env python3
import os
import re
import glob
import argparse
import numpy as np
import matplotlib.pyplot as plt
import uproot


def parse_signal_filename(path: str):
    """
    sel_Signal_1-0_0-03_0-04_v2.root
      -> ("1-0", "0-03", "0-04", "v2")
    """
    base = os.path.basename(path)
    m = re.match(r"^sel_Signal_([^_]+)_([^_]+)_([^_]+)_([^\.]+)\.root$", base)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


def calc_asimov(S, B):
    S = np.asarray(S, dtype=float)
    B = np.asarray(B, dtype=float)
    out = np.zeros_like(S, dtype=float)
    valid = (S > 0) & (B > 0)
    s = S[valid]
    b = B[valid]
    out[valid] = np.sqrt(2.0 * ((s + b) * np.log(1.0 + s / b) - s))
    return out


def calc_punzi(S, B, a=1.64):
    S = np.asarray(S, dtype=float)
    B = np.asarray(B, dtype=float)
    S0 = S[0] if len(S) > 0 and S[0] > 0 else 1.0
    eps = S / S0
    return eps / (a / 2.0 + np.sqrt(np.maximum(B, 0.0)))


def compute_metric(S, B, sig_def):
    if sig_def == "Significance":
        denom = np.sqrt(np.maximum(S + B, 1e-12))
        return S / denom
    elif sig_def == "asimov":
        return calc_asimov(S, B)
    elif sig_def == "punzi":
        return calc_punzi(S, B, a=1.64)
    elif sig_def == "punzi5":
        return calc_punzi(S, B, a=5.0)
    else:
        raise ValueError(f"Unknown sig_def: {sig_def}")


def read_arrays_from_root(root_file):
    """
    필요한 branch만 읽는다.
    """
    with uproot.open(root_file) as f:
        tree = f["events"]
        arr = tree.arrays(
            ["bdt_response", "XS", "Ngen"],
            library="np"
        )

    bdt = arr["bdt_response"].astype(np.float64)
    xs = arr["XS"].astype(np.float64)
    ngen = arr["Ngen"].astype(np.float64)

    return bdt, xs, ngen


def build_weight(xs, ngen, lumi_fb):
    return lumi_fb * 1000.0 * xs / ngen


def collect_signal_and_bkg(input_dir, mx1, lam1, lam2):
    all_root = sorted(glob.glob(os.path.join(input_dir, "*.root")))

    sig_files = []
    bkg_files = []

    for f in all_root:
        base = os.path.basename(f)
        if base.startswith("sel_Signal_"):
            info = parse_signal_filename(f)
            if info is None:
                continue
            f_mx1, f_lam1, f_lam2, _ver = info
            if f_mx1 == mx1 and f_lam1 == lam1 and f_lam2 == lam2:
                sig_files.append(f)
        else:
            bkg_files.append(f)

    return sig_files, bkg_files


def load_weighted_arrays(file_list, lumi_fb):
    if not file_list:
        return np.array([], dtype=float), np.array([], dtype=float)

    all_bdt = []
    all_wgt = []

    for f in file_list:
        bdt, xs, ngen = read_arrays_from_root(f)
        wgt = build_weight(xs, ngen, lumi_fb)

        all_bdt.append(bdt)
        all_wgt.append(wgt)

    return np.concatenate(all_bdt), np.concatenate(all_wgt)


def scan_significance(sig_bdt, sig_w, bkg_bdt, bkg_w, cut_min, cut_max, cut_step, sig_def):
    cuts = np.arange(cut_min, cut_max + 0.5 * cut_step, cut_step)

    S_vals = np.zeros_like(cuts, dtype=float)
    B_vals = np.zeros_like(cuts, dtype=float)

    for i, cut in enumerate(cuts):
        S_vals[i] = sig_w[sig_bdt > cut].sum()
        B_vals[i] = bkg_w[bkg_bdt > cut].sum()

    Z_vals = compute_metric(S_vals, B_vals, sig_def)
    return cuts, S_vals, B_vals, Z_vals


def save_csv(csv_path, cuts, S_vals, B_vals, Z_vals):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w") as f:
        f.write("BDT Response,Signal Yield (Log),Background Yield (Log),Metric\n")
        for c, s, b, z in zip(cuts, S_vals, B_vals, Z_vals):
            f.write(f"{c:.6f},{s:.12g},{b:.12g},{z:.12g}\n")


def plot_significance(out_png, cuts, S_vals, B_vals, Z_vals, sig_def, title):
    os.makedirs(os.path.dirname(out_png), exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    ax3.spines["right"].set_position(("axes", 1.15))

    S_plot = np.maximum(S_vals, 1e-12)
    B_plot = np.maximum(B_vals, 1e-12)

    ax2.set_yscale("log")
    ax3.set_yscale("log")

    ax1.plot(cuts, Z_vals, color="green", label=sig_def)
    ax2.plot(cuts, S_plot, color="blue", label="Signal Yield (Log)")
    ax3.plot(cuts, B_plot, color="red", label="Background Yield (Log)")

    idx_best = int(np.argmax(Z_vals))
    best_cut = cuts[idx_best]
    best_Z = Z_vals[idx_best]
    best_S = S_vals[idx_best]
    best_B = B_vals[idx_best]

    ax1.axvline(best_cut, color="green", linestyle="--", alpha=0.7)

    ax1.set_xlabel("BDT Response")
    ax1.set_ylabel(sig_def, color="green")
    ax2.set_ylabel("Signal Yield (Log)", color="blue")
    ax3.set_ylabel("Background Yield (Log)", color="red")

    ax1.tick_params(axis="y", colors="green")
    ax2.tick_params(axis="y", colors="blue")
    ax3.tick_params(axis="y", colors="red")

    text = (
        f"Best cut = {best_cut:.4f}\n"
        f"{sig_def} = {best_Z:.4f}\n"
        f"S = {best_S:.4f}\n"
        f"B = {best_B:.4f}"
    )

    ax1.text(
        0.03, 0.92, text,
        transform=ax1.transAxes,
        va="top",
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            alpha=0.85,
            edgecolor="black",   # 또는 "none"
            linewidth=1.0
        )
    )

    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
'''
def plot_significance(out_png, cuts, S_vals, B_vals, Z_vals, sig_def, title):
    os.makedirs(os.path.dirname(out_png), exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    ax2.set_yscale("log")
    ax3.set_yscale("log")

    ax3.spines["right"].set_position(("axes", 1.15))

    ax1.plot(cuts, Z_vals, color="green", label=sig_def)
    ax2.plot(cuts, S_vals, color="blue", label="Signal Yield (Log)")
    ax3.plot(cuts, B_vals, color="red", label="Background Yield (Log)")

    idx_best = int(np.argmax(Z_vals))
    best_cut = cuts[idx_best]
    best_Z = Z_vals[idx_best]
    best_S = S_vals[idx_best]
    best_B = B_vals[idx_best]

    ax1.axvline(best_cut, color="green", linestyle="--", alpha=0.7)

    ax1.set_xlabel("BDT Response")
    ax1.set_ylabel(sig_def, color="green")
    ax2.set_ylabel("Signal Yield (Log)", color="blue")
    ax3.set_ylabel("Background Yield (Log)", color="red")

    ax1.tick_params(axis="y", colors="green")
    ax2.tick_params(axis="y", colors="blue")
    ax3.tick_params(axis="y", colors="red")

    text = (
        f"Best cut = {best_cut:.4f}\n"
        f"{sig_def} = {best_Z:.4f}\n"
        f"S = {best_S:.4f}\n"
        f"B = {best_B:.4f}"
    )

    ax1.text(
        0.03, 0.92, text,
        transform=ax1.transAxes,
        va="top",
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            alpha=0.85,
            edgecolor="white",
            linewidth=1.0
        )
    )

    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
'''

def main():
    parser = argparse.ArgumentParser(description="Significance scan from data_eval ROOT files")
    parser.add_argument("--input_dir", required=True,
                        help="Directory containing evaluated ROOT files with bdt_response")
    parser.add_argument("--mx1", required=True, help="Signal mx1, e.g. 1-0")
    parser.add_argument("--lam1", required=True, help="Signal lam1, e.g. 0-03")
    parser.add_argument("--lam2", required=True, help="Signal lam2, e.g. 0-04")
    parser.add_argument("--lumi", type=float, required=True,
                        help="Luminosity in fb^-1")
    parser.add_argument("--output", required=True,
                        help="Output prefix or directory")
    parser.add_argument("--cut-min", type=float, default=-1.0)
    parser.add_argument("--cut-max", type=float, default=1.0)
    parser.add_argument("--cut-step", type=float, default=0.001)
    parser.add_argument("--sig-def", type=str, default="Significance",
                        choices=["Significance", "asimov", "punzi", "punzi5"])
    args = parser.parse_args()

    sig_files, bkg_files = collect_signal_and_bkg(
        args.input_dir, args.mx1, args.lam1, args.lam2
    )

    print(f"[INFO] signal files = {len(sig_files)}")
    for f in sig_files:
        print(f"  [SIG] {os.path.basename(f)}")

    print(f"[INFO] background files = {len(bkg_files)}")

    if len(sig_files) == 0:
        raise RuntimeError("No matching signal files found.")
    if len(bkg_files) == 0:
        raise RuntimeError("No background files found.")

    sig_bdt, sig_w = load_weighted_arrays(sig_files, args.lumi)
    bkg_bdt, bkg_w = load_weighted_arrays(bkg_files, args.lumi)

    print(f"[INFO] signal events loaded = {len(sig_bdt)}")
    print(f"[INFO] bkg events loaded    = {len(bkg_bdt)}")

    cuts, S_vals, B_vals, Z_vals = scan_significance(
        sig_bdt, sig_w,
        bkg_bdt, bkg_w,
        args.cut_min, args.cut_max, args.cut_step,
        args.sig_def
    )

    idx_best = int(np.argmax(Z_vals))
    print("[INFO] Best point")
    print(f"  cut = {cuts[idx_best]:.6f}")
    print(f"  S   = {S_vals[idx_best]:.6f}")
    print(f"  B   = {B_vals[idx_best]:.6f}")
    print(f"  {args.sig_def} = {Z_vals[idx_best]:.6f}")

    os.makedirs(args.output, exist_ok=True)

    tag = f"MX1{args.mx1}_lam1{args.lam1}_lam2{args.lam2}_{args.sig_def}"
    out_csv = os.path.join(args.output, f"significance_scan_{tag}.csv")
    out_png = os.path.join(args.output, f"significance_scan_{tag}.png")

    save_csv(out_csv, cuts, S_vals, B_vals, Z_vals)

    title = (
        f"MX1={args.mx1}, lam1={args.lam1}, lam2={args.lam2}, "
        f"L={args.lumi} fb^-1"
    )
    plot_significance(out_png, cuts, S_vals, B_vals, Z_vals, args.sig_def, title)

    print(f"[SAVED] {out_csv}")
    print(f"[SAVED] {out_png}")


if __name__ == "__main__":
    main()

