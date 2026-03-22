#!/bin/bash

if [ $# -lt 2 ]; then
  echo "Usage: $0 <ntree> <maxdepth>"
  exit 1
fi

ntree=$1
md=$2

mx1_list=(
  1-0
  1-5
  2-0
  2-5
)

lam_list=(
  #0-08
  0-1
  #0-2
  #0-3
  #0-4
  #0-5
)

for lam in "${lam_list[@]}"; do
  for mx1 in "${mx1_list[@]}"; do
    echo "[RUN] mx1=${mx1} lam=${lam} ntree=${ntree} maxdepth=${md}"
    bash run.sh ${mx1} ${ntree} ${md} ${lam}
  done
done

