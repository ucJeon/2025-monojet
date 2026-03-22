#!/bin/sh
export exe_name=$0
export cluster=$1
export process=$2
export target_input=$3
export target_node=$4
export input_parent=$5
export main_path=$6 # If analyzer generate tsome output files, then you need this variable.
export job_name=$7 # also
export host_name=$HOSTNAME
echo "=======================INFO======================="
echo "Starting time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "EXE script: ${exe_name}"
echo "file, node: ${target_input}, ${target_node}"
echo "Cluster ID: $cluster"
echo "Process ID: $process"
echo "input_parent: $input_parent"
echo "host_name: ${host_name} < tempprary..."
echo "=================================================="


# source /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc12-opt/setup.sh
# Outputs 디렉토리 생성
mkdir -p $PWD/outputs

# Python 스크립트 실행
python3 $PWD/main.py
