#!/bin/bash
# run2.sh
# cut list: -1.0 (no-cut baseline) + -0.30 to +0.30 (step 0.05)
# total 14 cut values × 4 mx1 × 2 lumi = 112 jobs

VERSION="v2"
NTREE=2000
MAXDEPTH=4
MX1_LIST=("1-0" "1-5" "2-0" "2-5")
LUMI_LIST=("300" "3000")

# cut list 생성: -1.0 고정 + seq -0.30 to 0.30 step 0.05
CUT_LIST=(-1.0)
# for i in $(seq -30 5 30); do
for i in $(seq -30 1 30); do # more fine
    # 정수 → 소수 변환: -30 → -0.30
    cut=$(echo "scale=2; $i / 100" | bc)
    CUT_LIST+=($cut)
done

echo "[INFO] cut list: ${CUT_LIST[@]}"
echo "[INFO] total cuts: ${#CUT_LIST[@]}"
echo ""

for mx1 in "${MX1_LIST[@]}"; do
    for lumi in "${LUMI_LIST[@]}"; do
        for cut in "${CUT_LIST[@]}"; do
            echo ">>> version=${VERSION} lumi=${lumi} mx1=${mx1} ntree=${NTREE} maxdepth=${MAXDEPTH} cut=${cut}"
            bash run1.sh ${VERSION} ${lumi} ${mx1} ${NTREE} ${MAXDEPTH} ${cut}
        done
    done
done

echo ""
echo "[DONE] all jobs finished."

