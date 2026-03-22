#!/bin/bash
# run_asymptotic.sh
# Usage: bash run_asymptotic.sh <version> <ntree> <maxdepth> <cut>
# e.g.   bash run_asymptotic.sh v2 2000 4 0.1300
#
# BDT model (version/ntree/maxdepth) + cut 을 받아
# 4 mx1 × 2 lumi = 8개 asymptotic limit 을 계산한다.
# 결과: results/{version}_{ntree}_{maxdepth}/limit_summary.csv

if [ $# -ne 4 ]; then
  echo "Usage: $0 <version> <ntree> <maxdepth> <cut>"
  echo "e.g.   $0 v2 2000 4 0.1300"
  exit 1
fi

VERSION=$1
NTREE=$2
MAXDEPTH=$3
CUT=$4

LAM1="0-15"
LAM2="0-15"

MX1_LIST=("1-0" "1-5" "2-0" "2-5")
LUMI_LIST=("300" "3000")

echo "========================================"
echo " run_asymptotic.sh"
echo " version  = ${VERSION}"
echo " ntree    = ${NTREE}"
echo " maxdepth = ${MAXDEPTH}"
echo " cut      = ${CUT}"
echo " lam1     = ${LAM1}, lam2 = ${LAM2}"
echo "========================================"

for lumi in "${LUMI_LIST[@]}"; do
  for mx1 in "${MX1_LIST[@]}"; do
    echo ""
    echo ">>> lumi=${lumi}  mx1=${mx1}"
    python3 main.py ${lumi} ${mx1} ${LAM1} ${LAM2} ${VERSION} ${NTREE} ${MAXDEPTH} \
      --cut ${CUT} \
      --mode asymptotic
  done
done

echo ""
echo "[DONE] asymptotic limit done."
echo "       → results/${VERSION}_${NTREE}_${MAXDEPTH}/limit_summary.csv"
