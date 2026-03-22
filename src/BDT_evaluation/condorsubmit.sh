#!/bin/bash
set -e

if [ $# -lt 5 ]; then
  echo "Usage: $0 <bdt_output_dir> <input_data_dir> <output_dir> <mode> <version>"
  exit 1
fi

bdt_output_dir="$1"
input_data_dir="$2"
output_dir="$3"
mode="$4"
version="$5"

mkdir -p logs/out logs/err logs/log subs

# bdt_output_dir 이름에서 target_mx1 추출
# 예: MX11-0_nTree2500_maxDepth4_uc_v2 -> 1-0
target_mx1=$(basename "$bdt_output_dir" | sed -E 's/^MX1([^_]+).*$/\1/')

xml_path="${bdt_output_dir}/dataset/weights/TMVAClassification_BDT.weights.xml"

if [ ! -f "$xml_path" ]; then
  echo "[ERROR] XML not found: $xml_path"
  exit 1
fi

input_list="./subs/input_${mode}_${target_mx1}_${version}.txt"

python3 make_input_list.py \
  --input_dir "$input_data_dir" \
  --mode "$mode" \
  --target_mx1 "$target_mx1" \
  --version "$version" \
  --output_list "$input_list"

nfiles=$(wc -l < "$input_list")
echo "[INFO] target_mx1 = $target_mx1"
echo "[INFO] xml_path   = $xml_path"
echo "[INFO] nfiles     = $nfiles"

if [ "$nfiles" -eq 0 ]; then
  echo "[ERROR] No input files selected."
  exit 1
fi

cat > ./subs/submission.sub <<EOL
universe = vanilla
getenv = True

executable = exe.sh
transfer_input_files = exe.sh,apply_bdt

should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_output_files   = ""

output = logs/out/\$(ClusterId).\$(ProcId).out
error  = logs/err/\$(ClusterId).\$(ProcId).err
log    = logs/log/\$(ClusterId).\$(ProcId).log

request_cpus   = 1
request_memory = 3G
request_disk   = 1G

+JobBatchName = "monojet_apply_bdt_${mode}_${target_mx1}"

arguments = ${xml_path} \$(input_file) ${output_dir} ${mode} ${target_mx1}

Requirements = (OpSysAndVer == "AlmaLinux9")

queue input_file from ${input_list}
EOL

condor_submit ./subs/submission.sub

