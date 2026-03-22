#!/usr/bin/env python3
"""
MC 폴더를 스캔하여 GenHisto용 input 파일 생성 (replica node 정보 포함)

출력 형식 : {filename},{replica1_hostname},{replica2_hostname}
출력 파일 : inputs.monojetSelectionDiet.{sample}.{sub_idx}.txt

파일명 구조:
  Background : {sample}.{sub_idx}.{parallel}.root
               e.g. wjets.3.7.root
  Signal     : Signal_{MX1}_{lam1}_{lam2}.{sub_idx}.{parallel}.root
               e.g. Signal_1-0_0-03_0-04.0.7.root

실행 위치 : checkDataNode.py 가 있는 디렉토리
           또는 CHECKDATANODE_DIR 경로 지정

Usage:
  python3 make_inputs_from_mc.py                        # 전체 처리
  python3 make_inputs_from_mc.py --mx1 1-0              # Signal MX1=1.0 TeV만
  python3 make_inputs_from_mc.py --mx1 2-5 --test       # MX1=2.5 TeV, 첫 파일만
  python3 make_inputs_from_mc.py --mc-dir /hdfs/user/ujeon/monojet/mc/v1.1.0
"""

import os
import sys
import subprocess
import argparse
from collections import defaultdict

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
MC_DIR     = "/user/ujeon/monojet/mc/v1.0.0"
OUTPUT_DIR = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/inputs"

CHECKDATANODE_DIR = "/users/ujeon/bin/condorSubmit"

# ── checkDataNode import ───────────────────────────────────────────────────────
sys.path.insert(0, CHECKDATANODE_DIR)
try:
    from checkDataNode import getDataNodes, getHostnameFromIP
except ImportError:
    print(f"❌ checkDataNode.py 를 찾을 수 없습니다: {CHECKDATANODE_DIR}")
    sys.exit(1)


def hdfs_ls(path: str) -> list:
    """hdfs dfs -ls 결과 파싱 → [{"name", "path"}, ...]"""
    cmd = ["hdfs", "dfs", "-ls", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        print("❌ 'hdfs' 명령어를 찾을 수 없습니다.")
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
            fpath = parts[7]
            fname = fpath.split("/")[-1]
        except IndexError:
            continue
        if fname.endswith(".root"):
            entries.append({"name": fname, "path": fpath})
    return entries


def get_replica_nodes(hdfs_path: str) -> list:
    """HDFS replica datanode hostname 목록 반환"""
    internal_path = hdfs_path.replace("/hdfs/", "/")
    try:
        ips = getDataNodes(internal_path)
        hostnames = [getHostnameFromIP(ip) for ip in ips]
        return hostnames
    except Exception as e:
        print(f"  ⚠️  replica 조회 실패 ({hdfs_path}): {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="MC → input 파일 생성 (replica node 포함)")
    parser.add_argument("--mc-dir",  default=MC_DIR,     help="MC HDFS 디렉토리")
    parser.add_argument("--out-dir", default=OUTPUT_DIR, help="output 파일 저장 디렉토리")
    parser.add_argument("--test",    action="store_true", help="각 그룹 첫 번째 파일만 처리")
    parser.add_argument("--mx1",     default=None,
                        help="Signal MX1 필터 (e.g. --mx1 1-0). 지정 시 해당 MX1 Signal만 처리. "
                             "미지정 시 전체(background + 모든 Signal) 처리")
    args = parser.parse_args()

    print("###################################################################")
    print("#        GenHisto Input 파일 생성 (MC + replica node)               #")
    print("###################################################################\n")
    print(f"MC 디렉토리 : {args.mc_dir}")
    print(f"출력 디렉토리: {args.out_dir}")
    if args.mx1:
        print(f"MX1 필터    : {args.mx1}  (Signal_MX1-* 만 처리)")
    print()

    # ── 1. MC 파일 목록 수집 ───────────────────────────────────────────────────
    print("[1/3] MC 파일 목록 수집 중...")
    entries = hdfs_ls(args.mc_dir)
    print(f"      → {len(entries)}개 .root 파일 발견\n")

    # ── 2. 필터링 & (sample, sub_idx) 기준 분류 ──────────────────────────────
    # 파일명 구조: {sample}.{sub_idx}.{parallel}.root
    group_map = defaultdict(list)   # (sample, sub_idx) -> [(parallel, fname, fpath), ...]

    for e in entries:
        name_parts = e["name"].split(".")
        if len(name_parts) < 4:
            print(f"  ⚠️  파일명 형식 오류, 건너뜀: {e['name']}")
            continue

        sample  = name_parts[0]   # e.g. wjets  /  Signal_1-0_0-03_0-04
        sub_idx = name_parts[1]   # e.g. 3      /  0
        try:
            parallel = int(name_parts[2])
        except ValueError:
            print(f"  ⚠️  parallel idx 파싱 실패, 건너뜀: {e['name']}")
            continue

        # --mx1 필터 적용
        if args.mx1:
            # Signal_MX1-MX2_... 형식에서 MX1 추출
            if sample.startswith("Signal_"):
                mx1_in_name = sample.split("_")[1].split("-")[0] + "-" + sample.split("_")[1].split("-")[1]
                # e.g. Signal_1-0_... → "1-0"
                if mx1_in_name != args.mx1:
                    continue   # 다른 MX1이면 스킵
            else:
                continue       # background는 스킵 (--mx1 지정 시)

        group_map[(sample, sub_idx)].append((parallel, e["name"], e["path"]))

    if not group_map:
        print("❌ 조건에 맞는 파일이 없습니다.")
        sys.exit(1)

    # ── 3. replica 조회 & 파일 저장 ───────────────────────────────────────────
    os.makedirs(args.out_dir, exist_ok=True)
    print("[2/3] replica node 조회 및 파일 저장 중...\n")

    total_groups = len(group_map)
    for g_idx, (sample, sub_idx) in enumerate(sorted(group_map.keys())):
        file_list = sorted(group_map[(sample, sub_idx)], key=lambda x: x[0])
        if args.test:
            file_list = file_list[:1]

        output_file = os.path.join(args.out_dir, f"inputs.monojetSelectionDiet.{sample}.{sub_idx}.txt")
        rows = []

        print(f"  [{g_idx+1}/{total_groups}] {sample}.{sub_idx}  ({len(file_list)}개 파일)")
        for i, (parallel, fname, fpath) in enumerate(file_list):
            print(f"    {i+1}/{len(file_list)}  {fname}", end="  ", flush=True)
            nodes = get_replica_nodes(fpath)
            row   = ",".join([fname] + nodes)
            rows.append(row)
            print(f"→ {nodes}")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")

        print(f"  ✅ 저장: {output_file}\n")

    print(f"[3/3] 완료. 총 {total_groups}개 그룹 처리.")


if __name__ == "__main__":
    main()
