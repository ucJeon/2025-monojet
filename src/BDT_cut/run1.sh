#!/bin/bash
# Usage: bash run1.sh <version> <lumi> <mx1> <ntree> <maxdepth> <cut>
# e.g.   bash run1.sh v2 300 1-0 2000 4 0.1300

if [ $# -ne 6 ]; then
  echo "Usage: $0 <version> <lumi> <mx1> <ntree> <maxdepth> <cut>"
  exit 1
fi

version=$1
lumi=$2
mx1=$3
ntree=$4
maxdepth=$5
cut=$6

python3 yield_after_bdtcut.py \
  --input_dir  /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/${version}/data_eval_MX1${mx1}_nTree${ntree}_maxDepth${maxdepth}_${version} \
  --version    ${version} \
  --lumi       ${lumi} \
  --mx1        ${mx1} \
  --ntree      ${ntree} \
  --maxdepth   ${maxdepth} \
  --cut        ${cut} \
  --output_dir /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_cut/out

