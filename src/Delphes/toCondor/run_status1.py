#!/usr/bin/env python3
# ==============================================================
# run_status1.py
# Case 1: 입력 정상, 출력 없음 → Delphes 작업 수행
# ==============================================================

import argparse
import os
import re
import socket
import subprocess
import sys


# --------------------------------------------------------------
# 유틸
# --------------------------------------------------------------

def run_cmd(args_list):
    proc = subprocess.Popen(args_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s_output, s_err = proc.communicate()
    return proc.returncode, s_output, s_err


def get_datanodes(hdfs_path):
    ret, out, err = run_cmd(['hdfs', 'fsck', hdfs_path, '-files', '-locations', '-blocks'])
    lines = out.decode('utf8').split('\n')
    comp = re.compile(r'DatanodeInfoWithStorage\[(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):9004')
    ips = []
    for line in lines:
        for part in line.split(","):
            result = comp.search(part)
            if result:
                ips.append(result.groupdict()['ip'])
    return ips


def get_hostname_from_ip(ip):
    return socket.gethostbyaddr(ip)[0]





# --------------------------------------------------------------
# 메인 작업
# --------------------------------------------------------------

def run(input_file, output_file, process, full_target, main_path):
    current_dir = os.getcwd()

    # full_target = sample_name.index (예: wjets.1)
    parts      = full_target.split(".")
    target     = parts[0]   # wjets
    sub_index  = parts[1]   # 1

    print(f"[INFO] target     : {target}")
    print(f"[INFO] sub_index  : {sub_index}")
    print(f"[INFO] process    : {process}")
    print(f"[INFO] input_file : {input_file}")
    print(f"[INFO] output_file: {output_file}")

    # ----------------------------------------------------------
    # 1. 출력 파일 혹시 있으면 삭제 (안전장치)
    # ----------------------------------------------------------
    print("\n===== 1. 출력 파일 사전 삭제 =====")
    hdfs_output = output_file.replace("/hdfs/", "/")
    subprocess.call(["hdfs", "dfs", "-rm", "-f", hdfs_output])

    # ----------------------------------------------------------
    # 2. 입력 HepMC 파일 가져오기
    # ----------------------------------------------------------
    print("\n===== 2. HepMC get =====")
    hdfs_input = input_file.replace("/hdfs/", "/")
    ret = subprocess.call(["hdfs", "dfs", "-get", hdfs_input, "."])
    if ret != 0:
        print(f"[ERROR] hdfs get 실패: {hdfs_input}")
        sys.exit(1)

    # ----------------------------------------------------------
    # 3. gunzip
    # ----------------------------------------------------------
    print("\n===== 3. gunzip =====")
    gz_file  = f"{current_dir}/{target}.{sub_index}.{process}.hepmc.gz"
    hepmc_file = f"{current_dir}/{target}.{sub_index}.{process}.hepmc"
    ret = subprocess.call(f"gunzip {gz_file}", shell=True)
    if ret != 0:
        print(f"[ERROR] gunzip 실패: {gz_file}")
        sys.exit(1)

    # ----------------------------------------------------------
    # 4. Delphes 실행
    # ----------------------------------------------------------
    print("\n===== 4. Delphes =====")
    delphes_card = f"{main_path}/delphes_card_CMS_monojet.dat"
    delphes_bin  = f"{main_path}/delphes_tauHadFinderModi/DelphesHepMC2"
    ret = subprocess.call(
        f"{delphes_bin} {delphes_card} output.root {hepmc_file}",
        shell=True
    )
    if ret != 0:
        print(f"[ERROR] Delphes 실패")
        sys.exit(1)

    # ----------------------------------------------------------
    # 5. 출력 파일 HDFS put
    # ----------------------------------------------------------
    print("\n===== 5. HDFS put =====")
    ret = subprocess.call(["hdfs", "dfs", "-put", "-f", f"{current_dir}/output.root", hdfs_output])
    if ret != 0:
        print(f"[ERROR] hdfs put 실패: {hdfs_output}")
        sys.exit(1)

    # ----------------------------------------------------------
    # 6. DataNode 정보 저장
    # ----------------------------------------------------------
    print("\n===== 6. DataNode 저장 =====")
    output_base = os.path.basename(hdfs_output)
    node_file   = f"{main_path}/outputs/{full_target}.GetHisto_{process}.txt"
    os.makedirs(os.path.dirname(node_file), exist_ok=True)

    datanodes = [get_hostname_from_ip(ip) for ip in get_datanodes(hdfs_output)]
    line = ",".join([output_base] + datanodes)
    with open(node_file, 'a') as f:
        f.write(line + '\n')
    print(f"[INFO] DataNode 저장 완료: {node_file}")

    # ----------------------------------------------------------
    # 7. 임시 파일 정리
    # ----------------------------------------------------------
    print("\n===== 7. 정리 =====")
    for f in [gz_file, hepmc_file, f"{current_dir}/output.root"]:
        if os.path.exists(f):
            os.remove(f)
            print(f"[INFO] 삭제: {f}")

    print("\n[DONE] run_status1 완료")


# --------------------------------------------------------------
# Entry point
# --------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Case 1: Delphes 작업 수행")
    parser.add_argument("--input_file",  required=True)
    parser.add_argument("--output_file", required=True)
    parser.add_argument("--process",     required=True, type=int)
    parser.add_argument("--full_target", required=True)
    parser.add_argument("--main_path",   required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        input_file  = args.input_file,
        output_file = args.output_file,
        process     = args.process,
        full_target = args.full_target,
        main_path   = args.main_path,
    )

