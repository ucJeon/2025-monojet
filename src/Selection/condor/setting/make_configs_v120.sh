#!/bin/bash

# 리스트 파일 경로
# list_file="/users/ujeon/2025-monojet/condor/2.GenSamples/setting/sample_list.txt"
# sample_list를 파일에서 읽어 배열로 저장
# mapfile -t sample_list < "$list_file"

sample_list=(
    wwlv2q.8
    wwlv2q.9
    
    wz2l2q.8
    wz2l2q.9

    wzlv2q.8
    wzlv2q.9

)

# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
input_parent="/hdfs/user/ujeon/monojet/mc/v1.2.0"
main_path="/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor"
# 배열 정의

# 배열을 순회하면서 스크립트 파일 생성
for item in "${sample_list[@]}"; do
    cat << EOF > "${main_path}/configs/${item}.yaml"
input_parent: ${input_parent}
job_name: monojetSelectionDiet.${item}
main_path: ${main_path}
EOF
done
