mx1_list=(
  1-0
  1-5
  2-0
  2-5
)

ntree_list=(
  # 1500
  # 2000
  # 2500
  4000
)

maxd_list=(
  6
)

version_list=(
  v2
  #v21
)
for version in "${version_list[@]}"; do
  for ntree in "${ntree_list[@]}"; do
    for maxd in "${maxd_list[@]}"; do
      for mx1 in "${mx1_list[@]}"; do
        bash condorsubmit.sh \
          /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_training/results/MX1${mx1}_nTree${ntree}_maxDepth${maxd}_uc_${version} \
          /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/${version}/data \
          /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/${version}/data_eval_MX1${mx1}_nTree${ntree}_maxDepth${maxd}_${version} \
          all \
          ${version}
      done
    done
  done
done

