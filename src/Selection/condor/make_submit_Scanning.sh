#!/bin/bash

mode=$1  # 첫 번째 인자를 mode로 받음

configs_dir="configs"
outputs_dir="outputs"

# 모든 config 파일 리스트 수집
configs=($(ls ${configs_dir}/*.yaml))

# mode 1일 경우: config는 있지만 output이 없는 항목을 추림
if [ "$mode" == "1" ]; then
    missing_configs=()

    echo "🔍 configs vs outputs 비교 결과:"
    for config in "${configs[@]}"; do
        # config 파일명 추출
        filename=$(basename "$config")
        base=${filename%.yaml}
        expected_output="${outputs_dir}/monojetGetHisto.${base}"

        if [ -f "$expected_output" ]; then
            echo " + ${config}"  # 존재하는 output
        else
            echo " - ${config}"  # 없는 output
            missing_configs+=("$config")
        fi
    done

    echo
    read -p "❓ 위 missing config들에 대해 Condor job을 제출하려면 1을 입력하세요: " confirm
    if [ "$confirm" == "1" ]; then
        for config in "${missing_configs[@]}"; do
            echo "🚀 Submitting job for $config"
            python3 /users/ujeon/bin/condorSubmit/condorSubmit.py --config "$config" --request_disk 10
        done
    else
        echo "⛔ 제출 취소됨."
    fi

# 기본 모드: 모든 config에 대해 제출
else
    for config in "${configs[@]}"; do
        echo "🚀 Submitting job for $config"
        python3 /users/ujeon/bin/condorSubmit/condorSubmit.py --config "$config" --request_disk 10
    done
fi
