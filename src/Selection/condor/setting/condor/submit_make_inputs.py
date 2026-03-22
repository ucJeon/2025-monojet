#!/usr/bin/env python3
"""
submit_make_inputs.py
MC 디렉토리를 스캔하여 (sample, sub_idx) 별로 condor job 제출

각 job:  exe_make_inputs.sh {sample} {sub_idx} {mc_dir} {out_dir}
로그:    logs/out|err|log/make_inputs/{sample}.{sub_idx}/...

Usage:
  python3 submit_make_inputs.py
  python3 submit_make_inputs.py --mc-dir /hdfs/.../mc/v1.2.0
  python3 submit_make_inputs.py --dry-run   # .sub 파일만 생성, 제출 안 함
"""

import os
import sys
import subprocess
import argparse
from collections import defaultdict

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
MC_DIR     = "/hdfs/user/ujeon/monojet/mc/v1.1.0"
OUTPUT_DIR = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/inputs"
MAIN_PATH  = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor"
EXE_PATH   = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/setting/condor/exe_make_inputs.sh"
JOB_NAME   = "make_inputs"


def hdfs_ls(path: str) -> list:
    cmd = ["hdfs", "dfs", "-ls", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        print("❌ hdfs 명령어를 찾을 수 없습니다.")
        sys.exit(1)
    if result.returncode != 0:
        print(f"❌ hdfs ls 실패:\n{result.stderr}")
        sys.exit(1)

    entries = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 8 or parts[0].startswith("d") or parts[0] == "Found":
            continue
        try:
            fname = parts[7].split("/")[-1]
        except IndexError:
            continue
        if fname.endswith(".root"):
            entries.append(fname)
    return entries


def get_groups(entries: list) -> list:
    """파일명 목록에서 고유한 (sample, sub_idx) 조합 추출"""
    groups = set()
    for fname in entries:
        parts = fname.split(".")
        if len(parts) < 4:
            continue
        try:
            int(parts[2])   # parallel index 검증
        except ValueError:
            continue
        groups.add((parts[0], parts[1]))   # (sample, sub_idx)
    return sorted(groups)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc-dir",   default=MC_DIR)
    parser.add_argument("--out-dir",  default=OUTPUT_DIR)
    parser.add_argument("--dry-run",  action="store_true", help=".sub 파일만 생성, condor_submit 안 함")
    parser.add_argument("--memory",   type=int, default=2,  help="request_memory (GB)")
    parser.add_argument("--disk",     type=int, default=2,  help="request_disk (GB)")
    args = parser.parse_args()

    # ── 1. 그룹 목록 수집 ─────────────────────────────────────────────────────
    print(f"[1/3] MC 디렉토리 스캔: {args.mc_dir}")
    entries = hdfs_ls(args.mc_dir)
    groups  = get_groups(entries)
    print(f"      → {len(groups)}개 그룹 (sample.sub_idx) 발견\n")

    if not groups:
        print("❌ 제출할 그룹이 없습니다.")
        sys.exit(1)

    # ── 2. 로그 디렉토리 생성 ─────────────────────────────────────────────────
    for sub in ["out", "err", "log"]:
        os.makedirs(f"{MAIN_PATH}/logs/{sub}/{JOB_NAME}", exist_ok=True)

    # ── 3. .sub 파일 생성 ─────────────────────────────────────────────────────
    sub_content = f"""\
universe   = vanilla
getenv     = True
executable = {EXE_PATH}

output = {MAIN_PATH}/logs/out/{JOB_NAME}/$(ClusterId).$(ProcId)
error  = {MAIN_PATH}/logs/err/{JOB_NAME}/$(ClusterId).$(ProcId)
log    = {MAIN_PATH}/logs/log/{JOB_NAME}/$(ClusterId).$(ProcId)

should_transfer_files   = NO

request_cpus   = 1
request_memory = {args.memory}G
request_disk   = {args.disk}G

+JobBatchName = "{JOB_NAME}"

"""
    for sample, sub_idx in groups:
        sub_content += (
            f"arguments = {sample} {sub_idx} {args.mc_dir} {args.out_dir}\n"
            f"Requirements = (OpSysAndVer == \"AlmaLinux9\")\n"
            f"queue 1\n\n"
        )

    os.makedirs(f"{MAIN_PATH}/subs", exist_ok=True)
    sub_file = f"{MAIN_PATH}/subs/{JOB_NAME}.sub"
    with open(sub_file, "w") as f:
        f.write(sub_content)
    print(f"[2/3] .sub 파일 생성: {sub_file}  ({len(groups)}개 job)\n")

    # 그룹 미리보기
    for sample, sub_idx in groups[:10]:
        print(f"  {sample}.{sub_idx}")
    if len(groups) > 10:
        print(f"  ... 외 {len(groups)-10}개")

    # ── 4. condor_submit ──────────────────────────────────────────────────────
    print()
    if args.dry_run:
        print(f"[3/3] dry-run 모드: condor_submit 생략")
        print(f"      제출하려면: condor_submit {sub_file}")
    else:
        print(f"[3/3] condor_submit 실행 중...")
        subprocess.run(["condor_submit", sub_file])


if __name__ == "__main__":
    main()
