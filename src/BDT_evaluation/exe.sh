#!/bin/bash
set -e

xml_path="$1"
input_file="$2"
output_dir="$3"
mode="$4"
target_mx1="$5"

echo "=============================="
echo "[INFO] exe.sh start"
echo "xml_path   = ${xml_path}"
echo "input_file = ${input_file}"
echo "output_dir = ${output_dir}"
echo "mode       = ${mode}"
echo "target_mx1 = ${target_mx1}"
echo "pwd        = $(pwd)"
echo "=============================="

mkdir -p "${output_dir}"

# apply_bdt는 파일 1개도 처리 가능
./apply_bdt "${xml_path}" "${input_file}" "${output_dir}" "${mode}" "${target_mx1}"

echo "[INFO] exe.sh done"
