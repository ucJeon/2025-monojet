#!/usr/bin/env python3
import os
import re
import sys
import glob
import argparse

def is_signal_file(path):
    return os.path.basename(path).startswith("sel_Signal_")

def has_version(path, version):
    base = os.path.basename(path)
    return base.endswith(f"_{version}.root")

def extract_signal_mx1(path):
    base = os.path.basename(path)
    m = re.match(r"^sel_Signal_([^_]+)_", base)
    return m.group(1) if m else ""

def pass_mode(path, mode, target_mx1, version):
    base = os.path.basename(path)

    # version 필터
    if version and not has_version(path, version):
        return False

    sig = is_signal_file(path)

    if mode == "signal":
        return sig and (target_mx1 == "" or extract_signal_mx1(path) == target_mx1)

    if mode == "bkg":
        return not sig

    if mode == "all":
        if not sig:
            return True
        return target_mx1 == "" or extract_signal_mx1(path) == target_mx1

    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", required=True)
    ap.add_argument("--mode", required=True, choices=["signal", "bkg", "all"])
    ap.add_argument("--target_mx1", default="")
    ap.add_argument("--version", default="",
                    help='file version filter, e.g. "v2", "v21"')
    ap.add_argument("--output_list", required=True)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, "*.root")))
    selected = [f for f in files if pass_mode(f, args.mode, args.target_mx1, args.version)]

    with open(args.output_list, "w") as f:
        for x in selected:
            f.write(x + "\n")

    print(f"[INFO] input_dir   = {args.input_dir}")
    print(f"[INFO] mode       = {args.mode}")
    print(f"[INFO] target_mx1 = {args.target_mx1}")
    print(f"[INFO] version    = {args.version}")
    print(f"[INFO] selected   = {len(selected)}")
    print(f"[INFO] wrote list to {args.output_list}")

if __name__ == "__main__":
    main()

