import ROOT
import argparse
import subprocess
import sys
import os
sys.path.append("/users/ujeon/2025-monojet")
from main_monojet import *
# import matplotlib.pyplot as plt
# import seaborn as sns
# import numpy as np
# import argparse
# import subprocess
# import shutil
# import uproot
# import time
import sys
# import os


##### Variable Setting #####
current_dir  = os.getenv("PWD")
cluster      = os.getenv("cluster") # same to ClsuterID
process      = os.getenv("process") # same to ProcID
target_input = os.getenv("target_input") # file 
target_node  = os.getenv("target_node") # node
input_parent = os.getenv("input_parent") 
main_path    = os.getenv("main_path")
job_name     = os.getenv("job_name") # monotop.wz_lvbb.EventGenerat

input_file_path  = f"{input_parent}/{target_input}" # ex) /hdfs/.../ww/0.root
output_file_path = f"{main_path}/outputs/{job_name}.{cluster}"
output_file_name = f"{output_file_path}/histo_{target_input}"

def main():
    target_input_dummy = target_input.removesuffix(".root")

    # ── 출력 파일 존재 여부 체크 ───────────────────────────────────────────────
    out_v2  = f"/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/root/v2/sel_{target_input_dummy}_v2.root"
    out_v21 = f"/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/root/v21/sel_{target_input_dummy}_v21.root"

    if os.path.exists(out_v2) and os.path.exists(out_v21):
        print(f"⏭️  Skip: output already exists → {target_input_dummy}")
        sys.exit(0)

    # 가져오기
    print("Step1: Getting")
    subprocess.call(["hdfs", "dfs", "-get", input_file_path.replace("/hdfs/","/"), "."])
    
    # Selection
    print("Step2: Main v2")
    subprocess.call([f"./main_v2 {target_input}"], shell=True)
    subprocess.call([f"cp cutflow_{target_input_dummy}_v2.csv /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/cutflowcsv/v2/cutflow_{target_input_dummy}_v2.csv"],shell=True)
    subprocess.call([f"cp sel_{target_input_dummy}_v2.root    /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/root/v2/sel_{target_input_dummy}_v2.root"],shell=True)
    
    # Selection
    print("Step2: Main v21")
    subprocess.call([f"./main_v21 {target_input}"], shell=True)
    subprocess.call([f"cp cutflow_{target_input_dummy}_v21.csv /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/cutflowcsv/v21/cutflow_{target_input_dummy}_v2.csv"],shell=True)
    subprocess.call([f"cp sel_{target_input_dummy}_v21.root    /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/root/v21/sel_{target_input_dummy}_v21.root"],shell=True)

if __name__ == "__main__":
    main()
