#!/usr/bin/env python3
# ==============================================================
# run_recopy.py
# RF=2 파일을 EC로 재복사 (hdfs get → rm → put)
# 사용: python3 run_recopy.py --hdfs_path <HDFS 경로>
# ==============================================================

import argparse
import os
import subprocess
import sys
import tempfile


# --------------------------------------------------------------
# 유틸
# --------------------------------------------------------------

def hdfs_exists(hdfs_path):
    ret = subprocess.call(
        ["hdfs", "dfs", "-test", "-e", hdfs_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return ret == 0


def check_is_replication(hdfs_path):
    """
    physical/logical >= 1.8 → RF=2 (True)
    그 외 → EC (False)
    """
    proc = subprocess.Popen(
        ["hdfs", "dfs", "-du", hdfs_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = proc.communicate()
    parts = out.decode().split()
    if len(parts) < 2:
        return False
    logical  = int(parts[0])
    physical = int(parts[1])
    if logical == 0:
        return False
    ratio = physical * 10 // logical
    return ratio >= 18


# --------------------------------------------------------------
# 메인
# --------------------------------------------------------------

def run(hdfs_path):
    print(f"[INFO] 대상 파일: {hdfs_path}")

    # 1. 존재 여부 확인
    if not hdfs_exists(hdfs_path):
        print(f"[ERROR] 파일 없음: {hdfs_path}")
        sys.exit(1)

    # 2. 이미 EC인지 확인
    if not check_is_replication(hdfs_path):
        print(f"[INFO] 이미 EC 정책 적용됨 → recopy 불필요")
        return

    print(f"[INFO] RF=2 감지 → recopy 시작")

    # 3. 임시 디렉토리에 get
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, os.path.basename(hdfs_path))

        print(f"\n===== 1. HDFS get =====")
        ret = subprocess.call(["hdfs", "dfs", "-get", hdfs_path, local_path])
        if ret != 0:
            print(f"[ERROR] hdfs get 실패: {hdfs_path}")
            sys.exit(1)

        print(f"\n===== 2. HDFS rm =====")
        ret = subprocess.call(["hdfs", "dfs", "-rm", "-f", hdfs_path])
        if ret != 0:
            print(f"[ERROR] hdfs rm 실패: {hdfs_path}")
            sys.exit(1)

        print(f"\n===== 3. HDFS put =====")
        ret = subprocess.call(["hdfs", "dfs", "-put", local_path, hdfs_path])
        if ret != 0:
            print(f"[ERROR] hdfs put 실패 → 원본 복구 시도")
            # 복구 시도
            subprocess.call(["hdfs", "dfs", "-put", local_path, hdfs_path])
            print(f"[ERROR] recopy 실패: {hdfs_path}")
            sys.exit(1)

    # 4. 완료 후 정책 재확인
    if check_is_replication(hdfs_path):
        print(f"[ERROR] recopy 후에도 RF=2 상태: {hdfs_path}")
        sys.exit(1)

    print(f"\n[DONE] recopy 완료 → EC 적용됨: {hdfs_path}")


# --------------------------------------------------------------
# Entry point
# --------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="RF=2 → EC recopy")
    parser.add_argument(
        "--hdfs_path",
        required=True,
        help="재복사할 HDFS 파일 경로 (예: /user/ujeon/monojet/HepMC/v1.1.0/wjets.1.0.hepmc.gz)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(hdfs_path=args.hdfs_path)
