#!/usr/bin/env python3
import os
import sys
import subprocess
import re

def main():
    if len(sys.argv) < 5:
        print(
            f"Usage: {sys.argv[0]} "
            "<bdt_output_dir> <input_data_path> <output_dir> <mode>\n"
            "  mode = signal | bkg | all\n"
            "\n"
            "Example:\n"
            "  python3 interface.py "
            "/path/to/BDT_Result/MX11-0_lam10-03_lam20-04_nTree850_maxDepth3_test_v2 "
            "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/v2/data "
            "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/v2/data_eval "
            "all"
        )
        sys.exit(1)

    bdt_output_dir = sys.argv[1]
    input_data_path = sys.argv[2]
    output_dir = sys.argv[3]
    mode = sys.argv[4]

    if mode not in ("signal", "bkg", "all"):
        print(f"[ERROR] invalid mode: {mode}")
        sys.exit(1)

    # bdt_output_dir 이름에서 target_mx1 추출
    # 예: MX11-0_lam10-03_lam20-04_nTree850_maxDepth3_test_v2 -> 1-0
    m = re.search(r"MX1([^_]+)", os.path.basename(bdt_output_dir))
    if not m:
        print("[ERROR] cannot extract target_mx1 from bdt_output_dir")
        sys.exit(1)

    target_mx1 = m.group(1)

    xml_path = os.path.join(
        bdt_output_dir,
        "dataset",
        "weights",
        "TMVAClassification_BDT.weights.xml"
    )

    if not os.path.isfile(xml_path):
        print(f"[ERROR] XML file not found: {xml_path}")
        sys.exit(1)

    if not os.path.exists(input_data_path):
        print(f"[ERROR] input_data_path not found: {input_data_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "./apply_bdt",
        xml_path,
        input_data_path,
        output_dir,
        mode,
        target_mx1
    ]

    print("=" * 70)
    print("[INFO] Apply BDT")
    print(f"  bdt_output_dir : {bdt_output_dir}")
    print(f"  xml_path       : {xml_path}")
    print(f"  input_data     : {input_data_path}")
    print(f"  output_dir     : {output_dir}")
    print(f"  mode           : {mode}")
    print(f"  target_mx1     : {target_mx1}")
    print("[INFO] Run command:")
    print("  " + " ".join(cmd))
    print("=" * 70)

    ret = subprocess.call(cmd)
    sys.exit(ret)

if __name__ == "__main__":
    main()

