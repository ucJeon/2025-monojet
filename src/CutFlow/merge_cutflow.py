#!/usr/bin/env python3
"""
merge_cutflow.py
병렬화된 cutflow CSV를 sample.subindex 단위로 합산

입력: cutflow_{sample}.{subindex}.{jobid}_v{ver}.csv
출력: cutflow_{sample}.{subindex}_v{ver}.csv

Usage:
    python3 merge_cutflow.py --input-dir outputs/ --output-dir merged/
    python3 merge_cutflow.py --dry-run   # 저장 없이 stdout만
"""

import os
import re
import csv
import argparse
from collections import defaultdict
from pathlib import Path


# ──────────────────────────────────────────────
# 1. 파일명 파싱
#    cutflow_wjets.2.6_v2.csv
#    → sample_key = "wjets.2"
#    → jobid      = "6"
#    → version    = "v2"
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# 전역 설정
# ──────────────────────────────────────────────
LUMI_FB = 300.0   # fb⁻¹  (변경 시 여기만 수정)
# N_expected = xsec [pb] × lumi [fb⁻¹] × 1000 [pb/fb] × (n_sel/n_gen)
# weight_per_event = xsec × LUMI × 1000 / N_gen

FILE_PATTERN = re.compile(
    r"^cutflow_"
    r"(?P<sample>[a-zA-Z0-9_]+\.[0-9]+)"   # wjets.2 / ttbar.3
    r"\."
    r"(?P<jobid>[0-9]+)"                    # 6
    r"_"
    r"(?P<version>v[0-9]+)"                 # v2
    r"\.csv$"
)

def parse_filename(fname):
    m = FILE_PATTERN.match(fname)
    if not m:
        return None
    return m.group("sample"), m.group("jobid"), m.group("version")


# ──────────────────────────────────────────────
# 2. CSV 읽기
# ──────────────────────────────────────────────
def read_csv(filepath):
    meta = {}
    with open(filepath, newline="") as f:
        lines = f.readlines()

    # 헤더 파싱
    data_lines = []
    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("#"):
            content = line.lstrip("# ").strip()
            if "," in content:
                k, v = content.split(",", 1)
                meta[k.strip()] = v.strip()
        else:
            data_lines.append(line)

    # 데이터 파싱
    rows = []
    reader = csv.DictReader(data_lines)
    for row in reader:
        rows.append({
            "cut":        row["cut"],
            "n_raw":      int(row["n_raw"]),
            "n_weighted": float(row["n_weighted"]),
            "eff_abs":    float(row["eff_abs"]),
            "eff_rel":    float(row["eff_rel"]),
        })
    return meta, rows


# ──────────────────────────────────────────────
# 3. 그룹 합산
# ──────────────────────────────────────────────
def merge_group(file_list):
    all_meta = []
    all_rows = []

    for fp in file_list:
        meta, rows = read_csv(fp)
        all_meta.append(meta)
        all_rows.append(rows)

    if not all_rows:
        return None, None

    cut_names = [r["cut"] for r in all_rows[0]]

    # n_raw 합산
    n_raw_sum = defaultdict(int)
    for rows in all_rows:
        for r in rows:
            n_raw_sum[r["cut"]] += r["n_raw"]

    # n_generated 합산
    n_gen_total = sum(int(m.get("n_generated", 0)) for m in all_meta)

    # xsec: 첫 번째 파일 기준 (병렬 job은 동일)
    xsec     = float(all_meta[0].get("xsec_pb", -1))
    xsec_unc = float(all_meta[0].get("xsec_unc_pb", -1))
    version  = all_meta[0].get("sel_version", "v2")

    weight = (xsec * LUMI_FB * 1000.0) / n_gen_total if (n_gen_total > 0 and xsec > 0) else 1.0

    # merged rows
    n_gen_raw = n_raw_sum.get("generated", n_gen_total)
    prev_raw  = None
    merged_rows = []

    for cut in cut_names:
        nr       = n_raw_sum[cut]
        nw       = nr * weight
        eff_abs  = nr / n_gen_raw if n_gen_raw > 0 else 0.0
        eff_rel  = nr / prev_raw  if (prev_raw and prev_raw > 0) else 1.0
        merged_rows.append({
            "cut":        cut,
            "n_raw":      nr,
            "n_weighted": nw,
            "eff_abs":    eff_abs,
            "eff_rel":    eff_rel,
        })
        prev_raw = nr

    merged_meta = {
        "xsec_pb":          xsec,
        "xsec_unc_pb":      xsec_unc,
        "n_generated":      n_gen_total,
        "lumi_fb":          LUMI_FB,
        "weight_per_event": weight,
        "sel_version":      version,
        "n_jobs_merged":    len(file_list),
    }

    return merged_meta, merged_rows


# ──────────────────────────────────────────────
# 4. CSV 저장
# ──────────────────────────────────────────────
def write_csv(out_path, sample_key, meta, rows):
    with open(out_path, "w", newline="") as f:
        f.write(f"# sample_name,{sample_key}\n")
        f.write(f"# sel_version,{meta['sel_version']}\n")
        f.write(f"# xsec_pb,{meta['xsec_pb']:.8e}\n")
        f.write(f"# xsec_unc_pb,{meta['xsec_unc_pb']:.8e}\n")
        f.write(f"# lumi_fb,{meta['lumi_fb']:.1f}\n")
        f.write(f"# n_generated,{meta['n_generated']}\n")
        f.write(f"# weight_per_event,{meta['weight_per_event']:.8e}\n")
        f.write(f"# n_jobs_merged,{meta['n_jobs_merged']}\n")
        f.write("#\n")
        f.write("cut,n_raw,n_weighted,eff_abs,eff_rel\n")
        for r in rows:
            f.write(
                f"{r['cut']},"
                f"{r['n_raw']},"
                f"{r['n_weighted']:.4f},"
                f"{r['eff_abs']:.6f},"
                f"{r['eff_rel']:.6f}\n"
            )
    print(f"[SAVED] {out_path}")


# ──────────────────────────────────────────────
# 5. stdout 요약
# ──────────────────────────────────────────────
def print_summary(sample_key, meta, rows):
    print(f"\n{'='*62}")
    print(f" Sample  : {sample_key}")
    print(f" Version : {meta['sel_version']}")
    print(f" XS [pb] : {meta['xsec_pb']:.4e} +- {meta['xsec_unc_pb']:.4e}")
    print(f" N_gen   : {meta['n_generated']}  ({meta['n_jobs_merged']} jobs merged)")
    print(f"{'='*62}")
    print(f"{'cut':<14} {'n_raw':>10} {'n_weighted':>14} {'eff_abs':>10} {'eff_rel':>10}")
    print("-"*62)
    for r in rows:
        print(f"{r['cut']:<14} {r['n_raw']:>10} "
              f"{r['n_weighted']:>14.2f} "
              f"{r['eff_abs']:>10.4f} "
              f"{r['eff_rel']:>10.4f}")


# ──────────────────────────────────────────────
# 6. Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Merge cutflow CSVs by sample.subindex"
    )
    parser.add_argument("--input-dir",  "-i", default=".",      help="입력 디렉토리 (default: .)")
    parser.add_argument("--output-dir", "-o", default="merged", help="출력 디렉토리 (default: merged/)")
    parser.add_argument("--dry-run", action="store_true",       help="파일 저장 없이 stdout만")
    args = parser.parse_args()

    in_dir  = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # 파일 수집 및 그룹핑
    # key: (sample_key, version) → [Path, ...]
    groups = defaultdict(list)
    for fp in sorted(in_dir.glob("cutflow_*.csv")):
        parsed = parse_filename(fp.name)
        if parsed is None:
            print(f"[SKIP] {fp.name}")
            continue
        sample_key, jobid, version = parsed
        groups[(sample_key, version)].append(fp)

    if not groups:
        print("[ERROR] 매칭되는 파일 없음")
        return

    print(f"[INFO] {len(groups)} group(s) in '{in_dir}'")

    for (sample_key, version), file_list in sorted(groups.items()):
        print(f"\n[GROUP] {sample_key}_{version}  ({len(file_list)} files)")
        for fp in file_list:
            print(f"        {fp.name}")

        meta, rows = merge_group(file_list)
        if rows is None:
            print("  → merge 실패, skip")
            continue

        print_summary(sample_key, meta, rows)

        if not args.dry_run:
            out_fname = f"cutflow_{sample_key}_{version}.csv"
            write_csv(out_dir / out_fname, sample_key, meta, rows)



# ══════════════════════════════════════════════════════════════
# [STAGE 2] sub-index 단위 → sample 단위 합산
#   입력: cutflow_{sample}.{subindex}_v{ver}.csv  (stage1 출력)
#   출력: cutflow_{sample}_v{ver}.csv
#
#   - n_raw     : 합산 (참고용)
#   - xs        : 해당 sub-index의 xsec [pb] (컬럼으로 추가)
#   - n_weighted: sub-index별 독립 계산 후 합산 (핵심)
#   - eff_abs/rel: 합산된 n_weighted 기준으로 재계산
# ══════════════════════════════════════════════════════════════

STAGE2_PATTERN = re.compile(
    r"^cutflow_"
    r"(?P<sample>[a-zA-Z0-9_]+)"   # ttbar / wjets / zjets
    r"\."
    r"(?P<subindex>[0-9]+)"         # 1 / 2 / 3
    r"_"
    r"(?P<version>v[0-9]+)"         # v2
    r"\.csv$"
)

def parse_filename_stage2(fname):
    m = STAGE2_PATTERN.match(fname)
    if not m:
        return None
    return m.group("sample"), m.group("subindex"), m.group("version")


def merge_group_stage2(file_list):
    """
    같은 sample + version에 속하는 sub-index CSV 합산
    각 파일은 이미 stage1 merge된 상태 (n_weighted 신뢰 가능)
    """
    all_meta = []
    all_rows = []

    for fp in file_list:
        meta, rows = read_csv(fp)
        # xs 컬럼이 없으면 meta에서 가져와서 rows에 추가
        xsec = float(meta.get("xsec_pb", -1))
        for r in rows:
            r["xs"] = xsec
        all_meta.append(meta)
        all_rows.append((meta, rows))

    if not all_rows:
        return None, None

    cut_names = [r["cut"] for r in all_rows[0][1]]

    # cut별로 sub-index마다 독립 계산 후 합산
    # n_weighted_total[cut] = Σ_i  n_raw_i[cut] * xsec_i / n_gen_i
    n_raw_total      = defaultdict(int)
    n_weighted_total = defaultdict(float)

    for meta, rows in all_rows:
        xsec  = float(meta.get("xsec_pb", -1))
        n_gen = int(meta.get("n_generated", 0))
        w     = (xsec * LUMI_FB * 1000.0) / n_gen if (n_gen > 0 and xsec > 0) else 1.0
        for r in rows:
            n_raw_total[r["cut"]]      += r["n_raw"]
            n_weighted_total[r["cut"]] += r["n_raw"] * w

    # eff 재계산 (n_weighted 기준)
    nw_gen   = n_weighted_total.get("generated", 1.0)
    prev_nw  = None
    merged_rows = []

    for cut in cut_names:
        nr  = n_raw_total[cut]
        nw  = n_weighted_total[cut]
        eff_abs = nw / nw_gen if nw_gen > 0 else 0.0
        eff_rel = nw / prev_nw if (prev_nw and prev_nw > 0) else 1.0
        merged_rows.append({
            "cut":        cut,
            "n_raw":      nr,
            "n_weighted": nw,
            "eff_abs":    eff_abs,
            "eff_rel":    eff_rel,
        })
        prev_nw = nw

    # xs 목록 (sub-index별 xsec 나열)
    xs_list    = [float(m.get("xsec_pb", -1)) for m, _ in all_rows]
    xs_str     = ";".join(f"{x:.6e}" for x in xs_list)
    n_gen_list = [int(m.get("n_generated", 0)) for m, _ in all_rows]

    merged_meta = {
        "sel_version":       all_meta[0].get("sel_version", "v2"),
        "lumi_fb":           LUMI_FB,
        "n_subindex_merged": len(file_list),
        "xs_per_subindex":   xs_str,
        "n_gen_per_subindex": ";".join(str(n) for n in n_gen_list),
        "n_weighted_total":  n_weighted_total.get("generated", 0.0),
    }

    return merged_meta, merged_rows


def write_csv_stage2(out_path, sample_key, meta, rows):
    with open(out_path, "w", newline="") as f:
        f.write(f"# sample_name,{sample_key}\n")
        f.write(f"# sel_version,{meta['sel_version']}\n")
        f.write(f"# lumi_fb,{meta['lumi_fb']:.1f}\n")
        f.write(f"# n_subindex_merged,{meta['n_subindex_merged']}\n")
        f.write(f"# xs_per_subindex,{meta['xs_per_subindex']}\n")
        f.write(f"# n_gen_per_subindex,{meta['n_gen_per_subindex']}\n")
        f.write(f"# n_weighted_generated,{meta['n_weighted_total']:.4f}\n")
        f.write("#\n")
        f.write("cut,n_raw,n_weighted,eff_abs,eff_rel\n")
        for r in rows:
            f.write(
                f"{r['cut']},"
                f"{r['n_raw']},"
                f"{r['n_weighted']:.4f},"
                f"{r['eff_abs']:.6f},"
                f"{r['eff_rel']:.6f}\n"
            )
    print(f"[SAVED] {out_path}")


def print_summary_stage2(sample_key, meta, rows):
    print(f"\n{'='*70}")
    print(f" Sample   : {sample_key}")
    print(f" Version  : {meta['sel_version']}")
    print(f" Lumi     : {meta['lumi_fb']:.1f} fb⁻¹")
    print(f" N_sub    : {meta['n_subindex_merged']} sub-indices merged")
    print(f" XS list  : {meta['xs_per_subindex']}")
    print(f" N_w(gen) : {meta['n_weighted_total']:.2f}")
    print(f"{'='*70}")
    print(f"{'cut':<14} {'n_raw':>12} {'n_weighted':>14} {'eff_abs':>10} {'eff_rel':>10}")
    print("-"*70)
    for r in rows:
        print(f"{r['cut']:<14} {r['n_raw']:>12} "
              f"{r['n_weighted']:>14.2f} "
              f"{r['eff_abs']:>10.4f} "
              f"{r['eff_rel']:>10.4f}")


def main_stage2():
    parser = argparse.ArgumentParser(
        description="[Stage2] Merge cutflow CSVs by sample (sub-index → sample)"
    )
    parser.add_argument("--input-dir",  "-i", default="merged",   help="stage1 출력 디렉토리")
    parser.add_argument("--output-dir", "-o", default="process",  help="stage2 출력 디렉토리")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    in_dir  = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    groups = defaultdict(list)
    for fp in sorted(in_dir.glob("cutflow_*.csv")):
        parsed = parse_filename_stage2(fp.name)
        if parsed is None:
            print(f"[SKIP] {fp.name}")
            continue
        sample, subindex, version = parsed
        groups[(sample, version)].append(fp)

    if not groups:
        print("[ERROR] 매칭되는 파일 없음")
        return

    print(f"[INFO] {len(groups)} sample group(s) in '{in_dir}'")

    for (sample, version), file_list in sorted(groups.items()):
        print(f"\n[GROUP] {sample}_{version}  ({len(file_list)} sub-indices)")
        for fp in file_list:
            print(f"        {fp.name}")

        meta, rows = merge_group_stage2(file_list)
        if rows is None:
            print("  → merge 실패, skip")
            continue

        print_summary_stage2(sample, meta, rows)

        if not args.dry_run:
            out_fname = f"cutflow_{sample}_{version}.csv"
            write_csv_stage2(out_dir / out_fname, sample, meta, rows)


# ══════════════════════════════════════════════════════════════
# [STAGE 3] sample 단위 → 물리 그룹 (TT / WJ / DY / VV)
#   입력: cutflow_{sample}_v{ver}.csv  (stage2 출력)
#   출력: cutflow_{group}_v{ver}.csv
#
#   그룹 정의:
#     TT : ttbar
#     WJ : wjets
#     DY : zjets
#     VV : ww2l2v, ww3l1v(=wz3l1v), wwlv2q, wz2l2q, wzlv2q, zz4l
#
#   - n_weighted: stage2 파일의 n_weighted 직접 합산
#                 (이미 xsec×lumi/N_gen 적용된 값)
#   - eff_abs/rel: 합산된 n_weighted 기준 재계산
# ══════════════════════════════════════════════════════════════

# 파일명 → 물리 그룹 매핑
# ww3l1v는 파일명이지만 실제로는 wz3l1v (xs mapping 불일치 처리)
SAMPLE_TO_GROUP = {
    "ttbar":   "TT",
    "wjets":   "WJ",
    "zjets":   "DY",
    "ww2l2v":  "VV",
    "ww3l1v":  "VV",   # 파일명 ww3l1v = 실제 wz3l1v
    "wwlv2q":  "VV",
    "wz2l2q":  "VV",
    "wzlv2q":  "VV",
    "zz4l":    "VV",
}

# ww3l1v → wz3l1v XS lookup alias
SAMPLE_NAME_ALIAS = {
    "ww3l1v": "wz3l1v",
}

STAGE3_PATTERN = re.compile(
    r"^cutflow_"
    r"(?P<sample>[a-zA-Z0-9_]+)"   # ttbar / wjets / zjets / ww2l2v / ...
    r"_"
    r"(?P<version>v[0-9]+)"         # v2
    r"\.csv$"
)

def parse_filename_stage3(fname):
    m = STAGE3_PATTERN.match(fname)
    if not m:
        return None
    sample  = m.group("sample")
    version = m.group("version")
    group   = SAMPLE_TO_GROUP.get(sample)
    if group is None:
        return None
    return sample, group, version


def merge_group_stage3(file_list):
    """
    같은 물리 그룹에 속하는 sample CSV 합산
    stage2 출력의 n_weighted를 직접 합산
    """
    all_meta = []
    all_rows = []

    for fp in file_list:
        meta, rows = read_csv(fp)
        all_meta.append((fp.stem, meta))   # (filename_stem, meta)
        all_rows.append((meta, rows))

    if not all_rows:
        return None, None

    cut_names = [r["cut"] for r in all_rows[0][1]]

    # n_raw, n_weighted 합산
    # n_weighted는 이미 xsec×lumi/N_gen 적용된 값 → 직접 합산
    n_raw_total      = defaultdict(int)
    n_weighted_total = defaultdict(float)

    for meta, rows in all_rows:
        for r in rows:
            n_raw_total[r["cut"]]      += r["n_raw"]
            n_weighted_total[r["cut"]] += r["n_weighted"]

    # eff 재계산 (n_weighted 기준)
    nw_gen  = n_weighted_total.get("generated", 1.0)
    prev_nw = None
    merged_rows = []

    for cut in cut_names:
        nr      = n_raw_total[cut]
        nw      = n_weighted_total[cut]
        eff_abs = nw / nw_gen if nw_gen > 0 else 0.0
        eff_rel = nw / prev_nw if (prev_nw and prev_nw > 0) else 1.0
        merged_rows.append({
            "cut":        cut,
            "n_raw":      nr,
            "n_weighted": nw,
            "eff_abs":    eff_abs,
            "eff_rel":    eff_rel,
        })
        prev_nw = nw

    # 샘플별 xs 및 n_weighted(generated) 목록
    sample_names = [parse_filename_stage3(fp.name)[0] for fp in file_list]
    xs_list      = [float(m.get("xsec_pb", -1)) if "xsec_pb" in m
                    else -1.0
                    for _, m in all_meta]
    nw_gen_list  = []
    for _, rows in all_rows:
        gen_row = next((r for r in rows if r["cut"] == "generated"), None)
        nw_gen_list.append(gen_row["n_weighted"] if gen_row else 0.0)

    merged_meta = {
        "sel_version":      all_meta[0][1].get("sel_version", "v2"),
        "lumi_fb":          LUMI_FB,
        "n_samples_merged": len(file_list),
        "samples":          ";".join(sample_names),
        "xs_per_sample":    ";".join(f"{x:.6e}" for x in xs_list),
        "nw_gen_per_sample":";".join(f"{n:.2f}" for n in nw_gen_list),
        "n_weighted_total": n_weighted_total.get("generated", 0.0),
    }

    return merged_meta, merged_rows


def write_csv_stage3(out_path, group_key, meta, rows):
    with open(out_path, "w", newline="") as f:
        f.write(f"# group_name,{group_key}\n")
        f.write(f"# sel_version,{meta['sel_version']}\n")
        f.write(f"# lumi_fb,{meta['lumi_fb']:.1f}\n")
        f.write(f"# n_samples_merged,{meta['n_samples_merged']}\n")
        f.write(f"# samples,{meta['samples']}\n")
        f.write(f"# xs_per_sample,{meta['xs_per_sample']}\n")
        f.write(f"# nw_gen_per_sample,{meta['nw_gen_per_sample']}\n")
        f.write(f"# n_weighted_generated,{meta['n_weighted_total']:.4f}\n")
        f.write("#\n")
        f.write("cut,n_raw,n_weighted,eff_abs,eff_rel\n")
        for r in rows:
            f.write(
                f"{r['cut']},"
                f"{r['n_raw']},"
                f"{r['n_weighted']:.4f},"
                f"{r['eff_abs']:.6f},"
                f"{r['eff_rel']:.6f}\n"
            )
    print(f"[SAVED] {out_path}")


def print_summary_stage3(group_key, meta, rows):
    print(f"\n{'='*70}")
    print(f" Group    : {group_key}")
    print(f" Version  : {meta['sel_version']}")
    print(f" Lumi     : {meta['lumi_fb']:.1f} fb⁻¹")
    print(f" Samples  : {meta['samples']}")
    print(f" N_w(gen) : {meta['n_weighted_total']:.2f}")
    print(f"{'='*70}")
    print(f"{'cut':<14} {'n_raw':>12} {'n_weighted':>16} {'eff_abs':>10} {'eff_rel':>10}")
    print("-"*70)
    for r in rows:
        print(f"{r['cut']:<14} {r['n_raw']:>12} "
              f"{r['n_weighted']:>16.2f} "
              f"{r['eff_abs']:>10.4f} "
              f"{r['eff_rel']:>10.4f}")


def main_stage3():
    parser = argparse.ArgumentParser(
        description="[Stage3] Merge sample CSVs into physics groups (TT/WJ/DY/VV)"
    )
    parser.add_argument("--input-dir",  "-i", default="merged_sample", help="stage2 출력 디렉토리")
    parser.add_argument("--output-dir", "-o", default="final",         help="stage3 출력 디렉토리")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    in_dir  = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # 파일 수집 및 그룹핑
    # key: (group, version) → [Path, ...]
    groups = defaultdict(list)
    skipped = []
    for fp in sorted(in_dir.glob("cutflow_*.csv")):
        parsed = parse_filename_stage3(fp.name)
        if parsed is None:
            skipped.append(fp.name)
            continue
        sample, group, version = parsed
        groups[(group, version)].append(fp)

    if skipped:
        print(f"[SKIP] 매핑 없는 파일 {len(skipped)}개:")
        for s in skipped:
            print(f"       {s}")

    if not groups:
        print("[ERROR] 매칭되는 파일 없음")
        return

    print(f"[INFO] {len(groups)} group(s) in '{in_dir}'")

    for (group, version), file_list in sorted(groups.items()):
        print(f"\n[GROUP] {group}_{version}  ({len(file_list)} samples)")
        for fp in file_list:
            sample = parse_filename_stage3(fp.name)[0]
            alias  = SAMPLE_NAME_ALIAS.get(sample, "")
            alias_str = f"  (XS alias → {alias})" if alias else ""
            print(f"        {fp.name}{alias_str}")

        meta, rows = merge_group_stage3(file_list)
        if rows is None:
            print("  → merge 실패, skip")
            continue

        print_summary_stage3(group, meta, rows)

        if not args.dry_run:
            out_fname = f"cutflow_{group}_{version}.csv"
            write_csv_stage3(out_dir / out_fname, group, meta, rows)


# ──────────────────────────────────────────────
# 진입점: --stage 1 / 2 / 3
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if "--stage" in sys.argv:
        idx = sys.argv.index("--stage")
        stage = int(sys.argv[idx+1])
        sys.argv.pop(idx); sys.argv.pop(idx)
    else:
        stage = 1  # default

    if stage == 1:
        main()
    elif stage == 2:
        main_stage2()
    elif stage == 3:
        main_stage3()
    else:
        print(f"[ERROR] Unknown stage: {stage}")

