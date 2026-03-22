mx1=$1
nt=$2
md=$3
lam=$4
python3 significance_scan.py \
  --input_dir /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/v2/data_eval_MX1${mx1}_nTree${nt}_maxDepth${md}_v2/ \
  --mx1 $mx1 \
  --lam1 $lam \
  --lam2 $lam.0 \
  --lumi 300 \
  --output ./sig_scan_out \
  --cut-min -0.4 \
  --cut-max 0.3 \
  --cut-step 0.002 \
  --sig-def Significance

