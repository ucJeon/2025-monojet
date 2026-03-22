#!/bin/sh
# exe_make_inputs.sh
# condor job 실행 스크립트
# arguments: $1=sample  $2=sub_idx  $3=mc_dir  $4=out_dir

export sample=$1
export sub_idx=$2
export mc_dir=$3
export out_dir=$4

echo "=================================================="
echo "Starting time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Host: $HOSTNAME"
echo "sample: ${sample}, sub_idx: ${sub_idx}"
echo "mc_dir: ${mc_dir}"
echo "out_dir: ${out_dir}"
echo "=================================================="

python3 /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/setting/condor/worker_make_inputs.py \
    --sample  ${sample}  \
    --sub-idx ${sub_idx} \
    --mc-dir  ${mc_dir}  \
    --out-dir ${out_dir}

echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
