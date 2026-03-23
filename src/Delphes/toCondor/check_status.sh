#!/bin/bash
# ==============================================================
# check_status.sh
# 파일 상태 판별 → CASE, IS_REPLICATION 세팅
# 사용: source check_status.sh <input_file> <output_file>
# ==============================================================

INPUT_FILE=$1
OUTPUT_FILE=$2

MIN_SIZE=$(( 10 * 1024 * 1024 ))  # 10MB in bytes

# --------------------------------------------------------------
# 존재 여부
# --------------------------------------------------------------
hdfs dfs -test -e "$INPUT_FILE"  2>/dev/null; INPUT_EXISTS=$?
hdfs dfs -test -e "$OUTPUT_FILE" 2>/dev/null; OUTPUT_EXISTS=$?

# --------------------------------------------------------------
# 이상치 확인
# 이상치 = _COPYING_ suffix 존재 OR 크기 < 10MB
# --------------------------------------------------------------
INPUT_OK=0
OUTPUT_OK=0

if [ "$INPUT_EXISTS" -eq 0 ]; then
    # _COPYING_ 체크
    hdfs dfs -test -e "${INPUT_FILE}_COPYING_" 2>/dev/null
    INPUT_COPYING=$?  # 0=존재(이상), 1=없음(정상)

    # 크기 체크
    INPUT_SIZE=$(hdfs dfs -du "$INPUT_FILE" 2>/dev/null | awk '{print $1}')
    INPUT_SIZE=${INPUT_SIZE:-0}

    if [ "$INPUT_COPYING" -eq 0 ] || [ "$INPUT_SIZE" -lt "$MIN_SIZE" ]; then
        INPUT_OK=1  # 이상
    fi
fi

if [ "$OUTPUT_EXISTS" -eq 0 ]; then
    # 크기 체크 (출력은 _COPYING_ 해당 없음)
    OUTPUT_SIZE=$(hdfs dfs -du "$OUTPUT_FILE" 2>/dev/null | awk '{print $1}')
    OUTPUT_SIZE=${OUTPUT_SIZE:-0}

    if [ "$OUTPUT_SIZE" -lt "$MIN_SIZE" ]; then
        OUTPUT_OK=1  # 이상
    fi
fi

# --------------------------------------------------------------
# HDFS 정책 (EC=0번대, RF=2=10번대)
# physical/logical >= 1.8 → RF=2
# --------------------------------------------------------------
IS_REPLICATION=0
if [ "$INPUT_EXISTS" -eq 0 ]; then
    read LOGICAL PHYSICAL _ <<< $(hdfs dfs -du "$INPUT_FILE" 2>/dev/null)
    if [ -n "$LOGICAL" ] && [ "$LOGICAL" -gt 0 ]; then
        RATIO=$(( PHYSICAL * 10 / LOGICAL ))
        [ "$RATIO" -ge 18 ] && IS_REPLICATION=1
    fi
fi

# --------------------------------------------------------------
# CASE 판별
# EC(0번대) / RF=2(10번대) 자동 분기
# --------------------------------------------------------------
OFFSET=0
[ "$IS_REPLICATION" -eq 1 ] && OFFSET=10

if   [ "$INPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_EXISTS" -ne 0 ] && [ "$INPUT_OK"  -eq 0 ]; then CASE=$(( 1 + OFFSET ))
elif [ "$INPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_EXISTS" -eq 0 ] && [ "$INPUT_OK"  -eq 0 ] && [ "$OUTPUT_OK" -eq 0 ]; then CASE=$(( 2 + OFFSET ))
elif [ "$INPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_EXISTS" -eq 0 ] && [ "$INPUT_OK"  -eq 0 ] && [ "$OUTPUT_OK" -ne 0 ]; then CASE=$(( 3 + OFFSET ))
elif [ "$INPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_EXISTS" -ne 0 ] && [ "$INPUT_OK"  -ne 0 ]; then CASE=$(( 4 + OFFSET ))
elif [ "$INPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_EXISTS" -eq 0 ] && [ "$INPUT_OK"  -ne 0 ]; then CASE=$(( 5 + OFFSET ))
elif [ "$INPUT_EXISTS" -ne 0 ] && [ "$OUTPUT_EXISTS" -ne 0 ]; then CASE=$(( 6 + OFFSET ))
elif [ "$INPUT_EXISTS" -ne 0 ] && [ "$OUTPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_OK" -eq 0 ]; then CASE=$(( 7 + OFFSET ))
elif [ "$INPUT_EXISTS" -ne 0 ] && [ "$OUTPUT_EXISTS" -eq 0 ] && [ "$OUTPUT_OK" -ne 0 ]; then CASE=$(( 8 + OFFSET ))
else CASE=99
fi

