#!/usr/bin/env python3
# ==============================================================
# condorsubmit.py
# Delphes Step - HTCondor Job Submitter
# /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Delphes
# ==============================================================

import argparse
import os
import subprocess
import sys
import yaml


# --------------------------------------------------------------
# Config loader
# --------------------------------------------------------------

def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def expand_samples(config: dict) -> list[dict]:
    """
    config의 samples를 펼쳐서 job 단위 리스트로 반환.
    각 항목: {sample_name, version, index, process_min, process_max}

    signal의 경우 mx1 x lam1 x lam2 조합을 sample_name으로 변환.
    """
    jobs = []
    for sample_name, entries in config["samples"].items():
        for entry in entries:
            version     = entry["version"]
            process_min = entry["process"]["min"]
            process_max = entry["process"]["max"]

            # Signal: mx1 x lam1 x lam2 조합 전개
            if sample_name == "Signal":
                for mx1 in entry["mx1"]:
                    for lam1 in entry["lam1"]:
                        for lam2 in entry["lam2"]:
                            full_name = f"Signal_{mx1}_{lam1}_{lam2}"
                            jobs.append({
                                "sample_name": full_name,
                                "version":     version,
                                "index":       entry.get("index", 0),
                                "process_min": process_min,
                                "process_max": process_max,
                            })
            # Background: indices 전개
            else:
                for idx in entry["indices"]:
                    jobs.append({
                        "sample_name": sample_name,
                        "version":     version,
                        "index":       idx,
                        "process_min": process_min,
                        "process_max": process_max,
                    })
    return jobs


# --------------------------------------------------------------
# Condor JDL writer
# --------------------------------------------------------------

def write_jdl(
    job_name_base: str,
    work_dir:      str,
    input_parent:  str,
    output_parent: str,
    jobs:          list[dict],
    log_dir:       str,
    is_test:       bool = False,
) -> str:
    """
    단일 JDL 파일 생성.
    job 1개 = sample.index 단위.
    process 범위(min~max)는 exe.sh에서 루프 처리.
    파라미터는 environment 환경변수로 exe.sh에 전달.
    is_test=True 이면 exe.sh에서 파일 조회만 수행 (case=0).
    """
    os.makedirs(log_dir, exist_ok=True)
    jdl_path = os.path.join(work_dir, f"{job_name_base}.jdl")

    lines = []
    lines.append(f"executable            = {work_dir}/exe.sh")
    lines.append(f"getenv                = True")
    lines.append(f"should_transfer_files = YES")                          # NO → YES
    lines.append(f"when_to_transfer_output = ON_EXIT")                    # 추가
    lines.append(f"transfer_input_files  = {work_dir}/toCondor")          # 추가
    lines.append(f"")


    test_flag = "1" if is_test else "0"

    for job in jobs:
        sample_name = job["sample_name"]
        version     = job["version"]
        index       = job["index"]
        process_min = job["process_min"]
        process_max = job["process_max"]
        full_target = f"{sample_name}.{index}"
        job_name    = f"{job_name_base}.{full_target}"

        lines.append(f"# --- {full_target} ---")
        lines.append(
            f'environment = "'
            f'job_name={job_name} '
            f'sample_name={sample_name} '
            f'version={version} '
            f'full_target={full_target} '
            f'input_parent={input_parent} '
            f'output_parent={output_parent} '
            f'main_path={work_dir} '
            f'process_min={process_min} '
            f'process_max={process_max} '
            f'is_test={test_flag}'
            f'"'
        )
        lines.append(f"log    = {log_dir}/{job_name}.log")
        lines.append(f"output = {log_dir}/{job_name}.out")
        lines.append(f"error  = {log_dir}/{job_name}.err")
        lines.append(f"Queue 1")
        lines.append(f"")

    with open(jdl_path, "w") as f:
        f.write("\n".join(lines))

    return jdl_path


# --------------------------------------------------------------
# Main
# --------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Delphes Step HTCondor submitter"
    )
    parser.add_argument(
        "-c", "--config",
        required=True,
        help="config yaml 경로 (예: bkg_config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="JDL 생성만 하고 실제 submit은 하지 않음"
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="log/out/err 저장 디렉토리 (default: {work_dir}/logs)"
    )
    parser.add_argument(
        "--sample",
        default=None,
        help="특정 샘플만 제출 (예: wjets). 미지정시 전체 제출"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 → exe.sh에서 파일 조회만 하고 실제 작업 수행 안 함"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 1. config 로드
    config     = load_config(args.config)
    job_base   = config["job"]["name_base"]
    work_dir   = config["job"]["work_dir"]
    input_par  = config["paths"]["input_parent"]
    output_par = config["paths"]["output_parent"]
    log_dir    = args.log_dir or os.path.join(work_dir, "logs")

    # 2. job 목록 생성
    jobs = expand_samples(config)

    # 특정 샘플 필터
    if args.sample:
        jobs = [j for j in jobs if j["sample_name"] == args.sample]
        if not jobs:
            print(f"[ERROR] sample '{args.sample}' 이 config에 없음")
            sys.exit(1)

    # ↓ 여기 추가
    if args.test:
        for j in jobs:
            j["process_min"] = 0
            j["process_max"] = 0

    print(f"[INFO] config     : {args.config}")
    print(f"[INFO] work_dir   : {work_dir}")
    print(f"[INFO] total jobs : {len(jobs)}")
    print(f"[INFO] dry-run    : {args.dry_run}")
    print(f"[INFO] test       : {args.test}")
    print()

    for j in jobs:
        print(f"  {j['sample_name']}.{j['index']}  "
              f"(version={j['version']}, "
              f"process={j['process_min']}~{j['process_max']})")
    print()

    # 3. JDL 작성
    jdl_path = write_jdl(
        job_name_base = job_base,
        work_dir      = work_dir,
        input_parent  = input_par,
        output_parent = output_par,
        jobs          = jobs,
        log_dir       = log_dir,
        is_test       = args.test,
    )
    print(f"[INFO] JDL written : {jdl_path}")

    # 4. 제출
    if args.dry_run:
        print("[INFO] dry-run 모드 → submit 생략")
        return

    ret = subprocess.call(["condor_submit", jdl_path])
    if ret != 0:
        print(f"[ERROR] condor_submit 실패 (return code={ret})")
        sys.exit(ret)

    print("[INFO] condor_submit 완료")


if __name__ == "__main__":
    main()
