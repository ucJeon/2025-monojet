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

Usage:
  python3 make_inputs_from_mc.py                   # 전체 처리
  python3 make_inputs_from_mc.py --bkg             # background만
  python3 make_inputs_from_mc.py --mx1 1-0         # Signal MX1=1.0 TeV만
  python3 make_inputs_from_mc.py --mx1 2-5 --test  # MX1=2.5 TeV, 첫 파일만

4개 세션 병렬 예시:
  session 1: python3 make_inputs_from_mc.py --bkg
  session 2: python3 make_inputs_from_mc.py --mx1 1-0
  session 3: python3 make_inputs_from_mc.py --mx1 1-5
  session 4: python3 make_inputs_from_mc.py --mx1 2-0
  session 5: python3 make_inputs_from_mc.py --mx1 2-5
"""

import os
import sys
import subprocess
import argparse
from collections import defaultdict

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
MC_DIR     = "/hdfs/user/ujeon/monojet/mc/v1.1.0"
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
                        help="Signal MX1 필터 (e.g. --mx1 1-0). 해당 MX1 Signal만 처리.")
    parser.add_argument("--bkg",     action="store_true",
                        help="Background만 처리 (Signal 제외). --mx1 과 동시 사용 불가.")
    args = parser.parse_args()

    # 옵션 충돌 체크
    if args.mx1 and args.bkg:
        print("❌ --mx1 과 --bkg 는 동시에 사용할 수 없습니다.")
        sys.exit(1)

    print("###################################################################")
    print("#        GenHisto Input 파일 생성 (MC + replica node)               #")
    print("###################################################################\n")
    print(f"MC 디렉토리 : {args.mc_dir}")
    print(f"출력 디렉토리: {args.out_dir}")
    if args.bkg:
        print(f"모드        : Background only")
    elif args.mx1:
        print(f"모드        : Signal MX1={args.mx1} only")
    else:
        print(f"모드        : 전체 (Background + Signal 모두)")
    print()

    # ── 1. MC 파일 목록 수집 ───────────────────────────────────────────────────
    print("[1/3] MC 파일 목록 수집 중...")
    entries = hdfs_ls(args.mc_dir)
    print(f"      → {len(entries)}개 .root 파일 발견\n")

    # ── 2. 필터링 & (sample, sub_idx) 기준 분류 ──────────────────────────────
    group_map = defaultdict(list)   # (sample, sub_idx) -> [(parallel, fname, fpath), ...]

    for e in entries:
        name_parts = e["name"].split(".")
        if len(name_parts) < 4:
            print(f"  ⚠️  파일명 형식 오류, 건너뜀: {e['name']}")
            continue

        sample  = name_parts[0]   # wjets  or  Signal_1-0_0-03_0-04
        sub_idx = name_parts[1]   # 3      or  0
        try:
            parallel = int(name_parts[2])
        except ValueError:
            print(f"  ⚠️  parallel idx 파싱 실패, 건너뜀: {e['name']}")
            continue

        is_signal = sample.startswith("Signal_")

        if args.bkg:
            # background만: Signal 제외
            if is_signal:
                continue
        elif args.mx1:
            # 특정 MX1 Signal만: background 제외, 다른 MX1 제외
            if not is_signal:
                continue
            # Signal_1-0_... → MX1 = "1-0"
            mx1_in_name = sample.split("_")[1]   # e.g. "1-0"
            if mx1_in_name != args.mx1:
                continue
        # else: 필터 없음 → 전체 처리

        # Signal lam1/lam2 필터: 둘 중 하나라도 2-0이면 스킵
        # sample 형식: Signal_{MX1}_{lam1}_{lam2}  e.g. Signal_1-0_2-0_0-04
        if is_signal:
            parts_sig = sample.split("_")   # ["Signal", "1-0", "lam1", "lam2"]
            if len(parts_sig) >= 4:
                lam1, lam2 = parts_sig[2], parts_sig[3]
                if lam1 == "2-0" or lam2 == "2-0":
                    continue

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

        # 기존 파일이 있으면 내용 읽어서 이미 처리된 fname 목록 파악
        existing_fnames = set()
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_fnames.add(line.split(",")[0])  # fname (첫 번째 컬럼)

        # 이미 처리된 것 제외
        todo_list = [(parallel, fname, fpath)
                     for (parallel, fname, fpath) in file_list
                     if fname not in existing_fnames]

        if not todo_list:
            print(f"  [{g_idx+1}/{total_groups}] {sample}.{sub_idx}  ⏭️  전체 완료, skip")
            continue

        skip_count = len(file_list) - len(todo_list)
        print(f"  [{g_idx+1}/{total_groups}] {sample}.{sub_idx}  ({len(todo_list)}개 처리 / {skip_count}개 skip)")

        rows = []
        for i, (parallel, fname, fpath) in enumerate(todo_list):
            print(f"    {i+1}/{len(todo_list)}  {fname}", end="  ", flush=True)
            nodes = get_replica_nodes(fpath)
            row   = ",".join([fname] + nodes)
            rows.append(row)
            print(f"→ {nodes}")

        # 기존 row + 신규 row 합쳐서 parallel 기준 재정렬 후 저장
        existing_rows = {}
        if existing_fnames:
            with open(output_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        fname_key = line.split(",")[0]
                        existing_rows[fname_key] = line

        for row in rows:
            fname_key = row.split(",")[0]
            existing_rows[fname_key] = row

        # parallel idx 기준 정렬: fname의 세 번째 "." 구분자 숫자
        def sort_key(row):
            try:
                return int(row.split(",")[0].split(".")[2])
            except (IndexError, ValueError):
                return 0

        sorted_rows = sorted(existing_rows.values(), key=sort_key)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted_rows) + "\n")

        print(f"  ✅ 저장: {output_file}  (총 {len(sorted_rows)}행)\n")

    print(f"[3/3] 완료. 총 {total_groups}개 그룹 처리.")


if __name__ == "__main__":
    main()


