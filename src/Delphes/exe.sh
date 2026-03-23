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

for (( process=process_min; process<=process_max; process++ )); do

    input_file="${input_parent}/${version}/${full_target}.${process}.hepmc.gz"
    output_file="${output_parent}/${version}/${full_target}.${process}.root"

    echo ""
    echo "------------------------------------------------------"
    echo "[PROCESS] $process  input=$input_file"

    # ----------------------------------------------------------
    # Case 0: 테스트 → 파일 조회만
    # ----------------------------------------------------------
    if [ "$is_test" = "1" ]; then
        hdfs dfs -test -e "$input_file"  2>/dev/null && echo "  input  : EXISTS" || echo "  input  : NOT FOUND"
        hdfs dfs -test -e "$output_file" 2>/dev/null && echo "  output : EXISTS" || echo "  output : NOT FOUND"
        continue
    fi

    # ----------------------------------------------------------
    # 상태 판별 → CASE, IS_REPLICATION 세팅
    # ----------------------------------------------------------
    source "./toCondor/check_status.sh" "$input_file" "$output_file"
    echo "[CASE] $CASE (is_replication=$IS_REPLICATION)"

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
