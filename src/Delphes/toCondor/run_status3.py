#!/usr/bin/env python3
# ==============================================================
# run_status3.py
# Case 3: 입력 정상, 출력 이상 → 출력 삭제 후 재작업
# ==============================================================

import argparse
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_status1


def parse_args():
    parser = argparse.ArgumentParser(description="Case 3: 출력 삭제 후 재작업")
    parser.add_argument("--input_file",  required=True)
    parser.add_argument("--output_file", required=True)
    parser.add_argument("--process",     required=True, type=int)
    parser.add_argument("--full_target", required=True)
    parser.add_argument("--main_path",   required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 1. 깨진 출력 파일 삭제
    # hdfs_output = args.output_file.replace("/hdfs/", "/")
    hdfs_output = args.output_file
    print(f"[INFO] 출력 파일 삭제: {hdfs_output}")
    ret = subprocess.call(["hdfs", "dfs", "-rm", "-f", hdfs_output])
    if ret != 0:
        print(f"[ERROR] hdfs rm 실패: {hdfs_output}")
        sys.exit(1)

    # 2. 재작업
    run_status1.run(
        input_file  = args.input_file,
        output_file = args.output_file,
        process     = args.process,
        full_target = args.full_target,
        main_path   = args.main_path,
    )
