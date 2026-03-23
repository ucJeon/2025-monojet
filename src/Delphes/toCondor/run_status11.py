#!/usr/bin/env python3
# ==============================================================
# run_status11.py
# Case 11: 입력 RF=2, 출력 없음 → recopy 후 Delphes 작업 수행
# ==============================================================

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_recopy
import run_status1


def parse_args():
    parser = argparse.ArgumentParser(description="Case 11: recopy 후 Delphes 작업 수행")
    parser.add_argument("--input_file",  required=True)
    parser.add_argument("--output_file", required=True)
    parser.add_argument("--process",     required=True, type=int)
    parser.add_argument("--full_target", required=True)
    parser.add_argument("--main_path",   required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 1. recopy
    hdfs_input = args.input_file.replace("/hdfs/", "/")
    run_recopy.run(hdfs_path=hdfs_input)

    # 2. Delphes 작업 수행 (run_status1 재활용)
    run_status1.run(
        input_file  = args.input_file,
        output_file = args.output_file,
        process     = args.process,
        full_target = args.full_target,
        main_path   = args.main_path,
    )
