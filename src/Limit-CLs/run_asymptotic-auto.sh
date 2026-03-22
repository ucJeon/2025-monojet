#!/bin/bash
# run_asymptotic_all.sh
# Usage: bash run_asymptotic_all.sh <version> <ntree> <maxdepth>
# e.g.   bash run_asymptotic_all.sh v2 2000 4
#
# BDT_cut/run2.sh 와 동일한 cut list 를 순회하며
# 각 cut에 대해 8개 (4 mx1 × 2 lumi) asymptotic limit 계산.
# 결과: results/{version}_{ntree}_{maxdepth}/limit_summary.csv

if [ $# -ne 3 ]; then
  echo "Usage: $0 <version> <ntree> <maxdepth>"
  echo "e.g.   $0 v2 2000 4"
  exit 1
fi

VERSION=$1
NTREE=$2
MAXDEPTH=$3

LAM1="0-15"
LAM2="0-15"

MX1_LIST=("1-0" "1-5" "2-0" "2-5")
LUMI_LIST=("300" "3000")

# BDT_cut/run2.sh 와 동일한 cut list
# -1.0 (no-cut baseline) + -0.30 ~ +0.30 (step 0.05)
CUT_LIST=(-1.0)
for i in $(seq -30 1 30); do
    cut=$(echo "scale=2; $i / 100" | bc)
    CUT_LIST+=($cut)
done

N_CUTS=${#CUT_LIST[@]}
N_TOTAL=$(( N_CUTS * ${#MX1_LIST[@]} * ${#LUMI_LIST[@]} ))

echo "========================================"
echo " run_asymptotic_all.sh"
echo " version  = ${VERSION}"
echo " ntree    = ${NTREE}"
echo " maxdepth = ${MAXDEPTH}"
echo " lam1     = ${LAM1}, lam2 = ${LAM2}"
echo " cuts     = ${N_CUTS}  (${CUT_LIST[0]} ... ${CUT_LIST[-1]})"
echo " total    = ${N_TOTAL} jobs"
echo "========================================"

RESULT_CSV="results/${VERSION}_${NTREE}_${MAXDEPTH}/limit_summary.csv"

job=0
for cut in "${CUT_LIST[@]}"; do
  for lumi in "${LUMI_LIST[@]}"; do
    for mx1 in "${MX1_LIST[@]}"; do
      job=$((job + 1))
      echo ""
      echo ">>> [${job}/${N_TOTAL}] cut=${cut}  lumi=${lumi}  mx1=${mx1}"
      python3 main.py ${lumi} ${mx1} ${LAM1} ${LAM2} ${VERSION} ${NTREE} ${MAXDEPTH} \
        --cut  ${cut} \
        --mode asymptotic
    done
  done
done

echo ""
echo "[DONE] all ${N_TOTAL} jobs finished."
echo "       → ${RESULT_CSV}"
