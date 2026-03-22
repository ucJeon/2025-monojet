#!/bin/bash
# condorsubmit.sh
# Usage: bash condorsubmit.sh <version> <ntree> <maxdepth> <cut>
# e.g.   bash condorsubmit.sh v2 2000 4 0.1300
#
# 4 mx1 × 2 lumi = 8개 full CLs job을 HTCondor에 제출한다.
# 각 job: python3 main.py ... --mode full --ntoys 10000 --nscan 300

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
NTOYS=10000
NSCAN=300

MX1_LIST=("1-0" "1-5" "2-0" "2-5")
LUMI_LIST=("300" "3000")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBS_DIR="${SCRIPT_DIR}/subs/logs"
LOG_DIR="${SCRIPT_DIR}/logs"

mkdir -p "${SUBS_DIR}/log" "${SUBS_DIR}/out" "${SUBS_DIR}/err"
mkdir -p "${LOG_DIR}/log"  "${LOG_DIR}/out"  "${LOG_DIR}/err"

MODEL_TAG="${VERSION}_${NTREE}_${MAXDEPTH}"
JDL="${SCRIPT_DIR}/subs/condor_full_${MODEL_TAG}.jdl"

# ---- JDL 생성 ----
cat > "${JDL}" <<EOF
Universe   = vanilla
Executable = ${SCRIPT_DIR}/subs/run_one.sh
Log        = ${SUBS_DIR}/log/\$(ClusterId).\$(ProcId).log
Output     = ${SUBS_DIR}/out/\$(ClusterId).\$(ProcId).out
Error      = ${SUBS_DIR}/err/\$(ClusterId).\$(ProcId).err
getenv     = True
request_cpus = 1

EOF

for lumi in "${LUMI_LIST[@]}"; do
  for mx1 in "${MX1_LIST[@]}"; do
    cat >> "${JDL}" <<EOF
Arguments  = ${lumi} ${mx1} ${LAM1} ${LAM2} ${VERSION} ${NTREE} ${MAXDEPTH} ${CUT} ${NTOYS} ${NSCAN}
Queue

EOF
  done
done

echo "[INFO] JDL written: ${JDL}"

# ---- wrapper 스크립트 ----
WRAPPER="${SCRIPT_DIR}/subs/run_one.sh"
cat > "${WRAPPER}" <<'WRAPPER_EOF'
#!/bin/bash
# run_one.sh <lumi> <mx1> <lam1> <lam2> <version> <ntree> <maxdepth> <cut> <ntoys> <nscan>
LUMI=$1; MX1=$2; LAM1=$3; LAM2=$4
VERSION=$5; NTREE=$6; MAXDEPTH=$7; CUT=$8
NTOYS=$9; NSCAN=${10}

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[START] lumi=${LUMI} mx1=${MX1} version=${VERSION} ntree=${NTREE} maxdepth=${MAXDEPTH} cut=${CUT}"

python3 ${SCRIPT_DIR}/main.py \
  ${LUMI} ${MX1} ${LAM1} ${LAM2} ${VERSION} ${NTREE} ${MAXDEPTH} \
  --cut     ${CUT} \
  --mode    full \
  --ntoys   ${NTOYS} \
  --nscan   ${NSCAN}

echo "[DONE] lumi=${LUMI} mx1=${MX1}"
WRAPPER_EOF

chmod +x "${WRAPPER}"
echo "[INFO] wrapper written: ${WRAPPER}"

# ---- 제출 ----
echo "[INFO] submitting..."
condor_submit "${JDL}"

echo ""
echo "[DONE] condor jobs submitted."
echo "       model  = ${MODEL_TAG}"
echo "       ntoys  = ${NTOYS},  nscan = ${NSCAN}"
echo "       result → results/${MODEL_TAG}/limit_summary.csv"
