#!/bin/bash

# 리스트 파일 경로
# list_file="/users/ujeon/2025-monojet/condor/2.GenSamples/setting/sample_list.txt"
# sample_list를 파일에서 읽어 배열로 저장
# mapfile -t sample_list < "$list_file"

sample_list=(

    ttbar.1
    ttbar.2
    ttbar.3
    ttbar.4
    ttbar.5
    ttbar.6
    ttbar.7
    ttbar.8
    ttbar.9

    wjets.1
    wjets.2
    wjets.3
    wjets.4
    wjets.5
    wjets.6
    wjets.7
    wjets.8

    zjets.1
    zjets.2
    zjets.3
    zjets.4
    zjets.5
    zjets.6
    zjets.7
    zjets.8
    
    zz4l.0
    ww2l2v.0
    wz3l1v.0 
    wwlv2q.1
    wwlv2q.2
    wwlv2q.3
    wwlv2q.4
    wwlv2q.5
    wwlv2q.6
    wwlv2q.7
    
    wz2l2q.1
    wz2l2q.2
    wz2l2q.3
    wz2l2q.4
    wz2l2q.5
    wz2l2q.6
    wz2l2q.7

    wzlv2q.1
    wzlv2q.2
    wzlv2q.3
    wzlv2q.4
    wzlv2q.5
    wzlv2q.6
    wzlv2q.7

)

# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
# input_parent 변수를 정의합니다.
input_parent="/hdfs/user/ujeon/monojet/mc/v1.1.0"
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
