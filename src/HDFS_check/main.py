#!/usr/bin/env python3
"""
HepMC -> MC 변환 정상 여부 확인 스크립트

파일명 매칭 규칙:
  HepMC : zjets.3.70.hepmc.gz   (/hdfs/user/ujeon/monojet/HepMC/v1.1.0)
  MC    : zjets.3.70.root        (/hdfs/user/ujeon/monojet/mc/v1.1.0)
  → .hepmc.gz 제거 후 stem 기준 매칭

판정 기준:
  O : MC 파일이 존재하고 크기 > 0
  X : MC 파일 없거나 크기 = 0

Usage:
  python3 check_hepmc2mc.py
  python3 check_hepmc2mc.py --output my_result.csv
"""

import subprocess
import csv
import argparse
import sys
import re

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
HEPMC_DIR = "/user/ujeon/monojet/HepMC/v1.1.0"
MC_DIR    = "/user/ujeon/monojet/mc/v1.1.0"

# HepMC 파일에서 stem 추출: .hepmc.gz 또는 .hepmc 제거
HEPMC_SUFFIX_PATTERN = re.compile(r"\.hepmc(\.gz)?$")
MC_EXT = ".root"


def hdfs_ls(path: str) -> list:
    """
    hdfs dfs -ls 결과 파싱
    출력 형식: permissions  rep  owner  group  size(bytes)  date  time  filepath
    반환: [{"name": filename, "size": int, "path": full_path}, ...]
    """
    cmd = ["hdfs", "dfs", "-ls", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        print("[ERROR] 'hdfs' 명령어를 찾을 수 없습니다. Hadoop 환경에서 실행하세요.", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"[ERROR] hdfs ls 실패: {path}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    entries = []
    for line in result.stdout.splitlines():
        parts = line.split()
        # 헤더 줄("Found N items") 또는 디렉토리 스킵
        if len(parts) < 8 or parts[0].startswith("d") or parts[0] == "Found":
            continue
        try:
            size  = int(parts[4])          # 바이트 단위 실제 크기
            fpath = parts[7]
            fname = fpath.split("/")[-1]
        except (ValueError, IndexError):
            continue
        entries.append({"name": fname, "size": size, "path": fpath})
    return entries


def human_readable(size_bytes):
    """바이트 -> 사람이 읽기 쉬운 단위"""
    if size_bytes == "" or size_bytes is None:
        return "-"
    b = int(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def get_stem(filename: str) -> str:
    """HepMC 파일명에서 공통 stem 추출 (.hepmc.gz or .hepmc 제거)"""
    return HEPMC_SUFFIX_PATTERN.sub("", filename)


def main():
    parser = argparse.ArgumentParser(description="HepMC->MC 변환 정상 여부 확인")
    parser.add_argument("--output", default="hepmc2mc_check.csv", help="출력 CSV 파일명")
    args = parser.parse_args()

    # ── 1. 파일 목록 수집 ──────────────────────────────────────────────────────
    print(f"[1/3] HepMC 디렉토리 스캔: {HEPMC_DIR}")
    hepmc_entries = hdfs_ls(HEPMC_DIR)
    print(f"      -> {len(hepmc_entries)}개 파일")

    print(f"[2/3] MC 디렉토리 스캔:    {MC_DIR}")
    mc_entries = hdfs_ls(MC_DIR)
    print(f"      -> {len(mc_entries)}개 파일")

    # ── 2. MC 인덱스 구성 (stem -> entry) ─────────────────────────────────────
    mc_index = {}
    for e in mc_entries:
        if e["name"].endswith(MC_EXT):
            stem = e["name"][: -len(MC_EXT)]   # .root 제거
            mc_index[stem] = e

    # ── 3. 매칭 & 판정 ────────────────────────────────────────────────────────
    rows = []
    ok_count = 0

    for hepmc in sorted(hepmc_entries, key=lambda x: x["name"]):
        stem      = get_stem(hepmc["name"])
        mc        = mc_index.get(stem)

        hepmc_size = hepmc["size"]
        mc_size    = mc["size"] if mc else ""
        mc_path    = mc["path"] if mc else ""

        # 판정
        if mc is None:
            result, reason = "X", "MC 파일 없음"
        elif mc["size"] == 0:
            result, reason = "X", "MC 파일 크기=0"
        elif hepmc_size > 0 and mc["size"] / hepmc_size < 1/512:
            result, reason = "X", f"크기 비율 {mc['size']/hepmc_size:.6f} < 1/512"
        else:
            result, reason = "O", ""
            ok_count += 1

        # 비율
        ratio = f"{mc['size'] / hepmc_size:.4f}" if mc and hepmc_size > 0 else ""

        rows.append({
            "stem":            stem,
            "hepmc_file":      hepmc["name"],
            "hepmc_size_B":    hepmc_size,
            "hepmc_size":      human_readable(hepmc_size),
            "mc_file":         mc["name"] if mc else "",
            "mc_size_B":       mc_size,
            "mc_size":         human_readable(mc_size),
            "ratio(mc/hepmc)": ratio,
            "result":          result,
            "reason":          reason,
        })

    # ── 4. CSV 저장 ───────────────────────────────────────────────────────────
    fieldnames = [
        "stem", "hepmc_file", "hepmc_size_B", "hepmc_size",
        "mc_file", "mc_size_B", "mc_size", "ratio(mc/hepmc)",
        "result", "reason",
    ]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # ── 5. 요약 출력 ──────────────────────────────────────────────────────────
    total      = len(rows)
    fail_count = total - ok_count
    print(f"\n[3/3] 결과 요약")
    print(f"      전체    : {total}")
    print(f"      O 정상  : {ok_count}")
    print(f"      X 실패  : {fail_count}")
    print(f"      저장    : {args.output}")

    failed = [r for r in rows if r["result"] == "X"]
    if failed:
        print(f"\n  실패 목록 (최대 20개):")
        print(f"  {'stem':<45}  {'이유'}")
        print(f"  {'-'*45}  {'-'*20}")
        for r in failed[:]:
            print(f"  {r['stem']:<45}  {r['reason']}")

    # 역방향 체크: MC에만 있고 HepMC에 없는 파일
    hepmc_stems = {get_stem(e["name"]) for e in hepmc_entries}
    orphan_mc   = sorted(set(mc_index.keys()) - hepmc_stems)
    if orphan_mc:
        print(f"\n  [WARNING] 대응 HepMC 없는 MC 파일 {len(orphan_mc)}개:")
        for k in orphan_mc[:10]:
            print(f"    {k}{MC_EXT}")


if __name__ == "__main__":
    main()

