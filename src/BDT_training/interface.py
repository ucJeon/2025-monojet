#!/usr/bin/env python3
import os
import subprocess
import sys

def main():
    if len(sys.argv) < 6:
        print(
            f"Usage: {sys.argv[0]} "
            "<which_mx1> <version> <nTree> <Depth> <flag> [storeDir]"
        )
        sys.exit(1)

    which_mx1 = sys.argv[1]
    version   = sys.argv[2]
    nTree     = sys.argv[3]
    Depth     = sys.argv[4]
    flag      = sys.argv[5]
    storeDir  = sys.argv[6] if len(sys.argv) > 6 else "./"

    data_dir = f"/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/{version}/BDTdata"

    if not os.path.isdir(data_dir):
        print(f"[ERROR] BDTdata directory not found: {data_dir}")
        sys.exit(1)

    lam1_labels = ["0-1", "0-3", "0-5"]
    lam2_labels = ["0-1.0", "0-3.0", "0-5.0"]

    missing = []

    print("=" * 60)
    print("[INFO] BDT interface")
    print(f"  which_mx1 : {which_mx1}")
    print(f"  version   : {version}")
    print(f"  nTree     : {nTree}")
    print(f"  Depth     : {Depth}")
    print(f"  flag      : {flag}")
    print(f"  storeDir  : {storeDir}")
    print(f"  data_dir  : {data_dir}")
    print("[INFO] signal grid check:")
    print("=" * 60)

    for lam1 in lam1_labels:
        for lam2 in lam2_labels:
            signal_path = os.path.join(
                data_dir,
                f"sel_Signal_{which_mx1}_{lam1}_{lam2}_{version}.root"
            )
            exists = os.path.isfile(signal_path)
            print(f"  [{'OK' if exists else 'NO'}] {signal_path}")
            if not exists:
                missing.append(signal_path)

    if missing:
        print("[ERROR] Missing signal files:")
        for x in missing:
            print(" ", x)
        sys.exit(1)

    cmd = [
        "./main",
        which_mx1,
        version,
        nTree,
        Depth,
        flag,
        storeDir,
    ]

    print("[INFO] Run command:")
    print(" ", " ".join(cmd))

    ret = subprocess.call(cmd)
    sys.exit(ret)

if __name__ == "__main__":
    main()

