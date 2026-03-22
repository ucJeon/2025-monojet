#!/bin/bash

export exe_name=$0
export cluster=$1
export process=$2
export target_input=$3

source /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc12-opt/setup.sh

# basename만 추출
input_basename=$(basename $target_input)

# hdfs 경로로부터 local로 가져오기
prefix="/hdfs/user/ujeon/monojet/mc/v1.0.0"
target_input_=$prefix/$target_input
hdfs dfs -get ${target_input_//\/hdfs\//\/} $current_dir

current_dir=$PWD
echo $current_dir

echo " =========================================== "
echo " ================= step: 1 ================= "

# main.py에 인자 전달
bash _compile.sh
./monojetMX1massDitribution $input_basename
 
mkdir -p /users/ujeon/2025-monojet/condor/21.DistributionMX1/outputs/${cluster}
cp ${current_dir}/output.root /users/ujeon/2025-monojet/condor/21.DistributionMX1/outputs/${cluster}/$input_basename

echo " ================== DONE =================== "
