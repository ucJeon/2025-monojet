#!/bin/bash
# ==============================================================
# exe.sh
# Delphes Step - HTCondor Executable
# ==============================================================

echo "============================================================"
echo "[INFO] job_name     : $job_name"
echo "[INFO] full_target  : $full_target"
echo "[INFO] version      : $version"
echo "[INFO] process_min  : $process_min"
echo "[INFO] process_max  : $process_max"
echo "[INFO] is_test      : $is_test"
echo "============================================================"

# 로그만인 케이스
LOG_CASES="2 4 5 6 7 8 12 14 15 16 17 18"

# summary 로그 경로
SUMMARY_LOG="${main_path}/logs/summary_${job_name}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "${main_path}/logs"

for (( process=process_min; process<=process_max; process++ )); do

    input_file="${input_parent}/${version}/${full_target}.${process}.hepmc.gz"
    output_file="${output_parent}/${version}/${full_target}.${process}.root"

    echo ""
    echo "------------------------------------------------------"
    echo "[PROCESS] $process  input=$input_file"

    # ----------------------------------------------------------
    # 상태 판별 → CASE, IS_REPLICATION 세팅
    # ----------------------------------------------------------
    source "./toCondor/check_status.sh" "$input_file" "$output_file"
    echo "[CASE] $CASE (is_replication=$IS_REPLICATION)"

    # ----------------------------------------------------------
    # test mode: CASE 및 실행될 커맨드 echo 후 종료
    # ----------------------------------------------------------
    if [ "$is_test" = "1" ]; then
        if echo "$LOG_CASES" | grep -qw "$CASE"; then
            echo "[CMD]  python3 ./toCondor/run_status_log.py --case $CASE --input_file $input_file --output_file $output_file --process $process --full_target $full_target"
        else
            echo "[CMD]  python3 ./toCondor/run_status${CASE}.py --input_file $input_file --output_file $output_file --process $process --full_target $full_target --main_path ./toCondor"
        fi
        echo "$full_target.$process CASE=$CASE [TEST]" >> "$SUMMARY_LOG"
        continue
    fi

    # ----------------------------------------------------------
    # summary 기록
    # ----------------------------------------------------------
    echo "$full_target.$process CASE=$CASE" >> "$SUMMARY_LOG"

    # ----------------------------------------------------------
    # 로그 케이스
    # ----------------------------------------------------------
    if echo "$LOG_CASES" | grep -qw "$CASE"; then
        python3 "./toCondor/run_status_log.py" \
            --case        "$CASE"        \
            --input_file  "$input_file"  \
            --output_file "$output_file" \
            --process     "$process"     \
            --full_target "$full_target"
        continue
    fi

    # ----------------------------------------------------------
    # 작업 케이스 (1, 3, 11, 13)
    # ----------------------------------------------------------
    python3 "./toCondor/run_status${CASE}.py" \
        --input_file  "$input_file"  \
        --output_file "$output_file" \
        --process     "$process"     \
        --full_target "$full_target" \
        --main_path   "./toCondor"

done

echo ""
echo "[INFO] 완료: $job_name"
echo "[INFO] summary: $SUMMARY_LOG"
