#!/usr/bin/env python3
"""
worker_make_inputs.py
단일 (sample, sub_idx) 그룹의 replica node 정보를 조회하여 input 파일 생성

Usage:
  python3 worker_make_inputs.py --sample wjets --sub-idx 3
  python3 worker_make_inputs.py --sample wjets --sub-idx 3 --mc-dir /hdfs/.../mc/v1.2.0
"""

import os
import sys
import subprocess
import argparse

MC_DIR     = "/user/ujeon/monojet/mc/v1.1.0"
OUTPUT_DIR = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/inputs"
CHECKDATANODE_DIR = "/users/ujeon/bin/condorSubmit"

sys.path.insert(0, CHECKDATANODE_DIR)
try:
    from checkDataNode import getDataNodes, getHostnameFromIP
except ImportError:
    print(f"❌ checkDataNode.py 를 찾을 수 없습니다: {CHECKDATANODE_DIR}")
    sys.exit(1)


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
            fpath = parts[7]
            fname = fpath.split("/")[-1]
        except IndexError:
            continue
        if fname.endswith(".root"):
            entries.append({"name": fname, "path": fpath})
    return entries


def get_replica_nodes(hdfs_path: str) -> list:
    internal_path = hdfs_path.replace("/hdfs/", "/")
    try:
        ips = getDataNodes(internal_path)
        return [getHostnameFromIP(ip) for ip in ips]
    except Exception as e:
        print(f"  ⚠️  replica 조회 실패 ({hdfs_path}): {e}")
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample",  required=True, help="sample 이름 (e.g. wjets)")
    parser.add_argument("--sub-idx", required=True, help="sub index  (e.g. 3)")
    parser.add_argument("--mc-dir",  default=MC_DIR)
    parser.add_argument("--out-dir", default=OUTPUT_DIR)
    args = parser.parse_args()

    prefix = f"{args.sample}.{args.sub_idx}"
    print(f"[worker] 시작: {prefix}  (MC: {args.mc_dir})")

    # 해당 그룹 파일만 필터링
    all_entries = hdfs_ls(args.mc_dir)
    entries = []
    for e in all_entries:
        parts = e["name"].split(".")
        if len(parts) < 4:
            continue
        if parts[0] == args.sample and parts[1] == args.sub_idx:
            try:
                parallel = int(parts[2])
            except ValueError:
                continue
            entries.append((parallel, e["name"], e["path"]))

    if not entries:
        print(f"❌ {prefix} 에 해당하는 파일 없음")
        sys.exit(1)

    entries.sort(key=lambda x: x[0])
    print(f"[worker] {len(entries)}개 파일 발견, replica 조회 시작...")

    rows = []
    for i, (parallel, fname, fpath) in enumerate(entries):
        print(f"  {i+1}/{len(entries)}  {fname}", end="  ", flush=True)
        nodes = get_replica_nodes(fpath)
        rows.append(",".join([fname] + nodes))
        print(f"→ {nodes}")

    os.makedirs(args.out_dir, exist_ok=True)
    output_file = os.path.join(args.out_dir, f"inputs.monojetSelectionDiet.{prefix}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")

    print(f"[worker] ✅ 저장 완료: {output_file}")


if __name__ == "__main__":
    main()
