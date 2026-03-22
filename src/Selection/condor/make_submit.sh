#!/bin/sh
analyzer_tag=${1:-none}
store_tag=${2:-none}
if [ "$store_tag" != "none" ]; then
    mkdir -p "$store_tag"
fi
# config 파일 목록 배열 정의
configs=($(ls configs/*.yaml))  # configs 폴더 내의 모든 .yaml 파일을 배열에 저장

# 반복문을 사용하여 각 config 파일에 대해 명령 실행
for config in "${configs[@]}"; do
    python3 /users/ujeon/bin/condorSubmit/condorSubmit.py --config "$config" --request_disk 6 --submit_scr_arg "[\"$analyzer_tag\", \"$store_tag\"]" 
    #python3 /users/ujeon/bin/condorSubmit/condorSubmit.py --config "$config" --request_disk 10 --only_one true
done
