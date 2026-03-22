#!/bin/bash

set -euo pipefail

if [ $# -lt 5 ]; then
    echo "Usage: $0 <mx1> <version> <nTree> <Depth> <flag>"
    echo "Example: bash run_one.sh 1-0 v2 2500 4 uc"
    exit 1
fi

mx1="$1"
version="$2"
nTree="$3"
Depth="$4"
flag="$5"

base_dir="/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_training"
log_dir="${base_dir}/manual_logs"

mkdir -p "${log_dir}"

if [ "${flag}" = "none" ]; then
    tag="MX1${mx1}_nTree${nTree}_maxDepth${Depth}_${version}"
else
    tag="MX1${mx1}_nTree${nTree}_maxDepth${Depth}_${flag}_${version}"
fi

stdout_log="${log_dir}/${tag}.out"
stderr_log="${log_dir}/${tag}.err"

cd "${base_dir}"

echo "[INFO] Run: exe.sh local 0 ${mx1} ${version} ${nTree} ${Depth} ${flag}"
echo "[INFO] stdout -> ${stdout_log}"
echo "[INFO] stderr -> ${stderr_log}"

bash exe.sh local 0 "${mx1}" "${version}" "${nTree}" "${Depth}" "${flag}" \
    > "${stdout_log}" 2> "${stderr_log}"

echo "[INFO] Done."
