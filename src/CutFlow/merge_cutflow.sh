base=/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/cutflowcsv
version=$1 # v1 v2 v21
# Stage 1: job → sub-index
python3 merge_cutflow.py --stage 1 -i ${base}/${version}/      -o 1_merged/

# Stage 2: sub-index → sample  (xsec×lumi/N_gen 적용)
python3 merge_cutflow.py --stage 2 -i 1_merged/        -o 2_merged_sample/

# Stage 3: sample → TT/WJ/DY/VV  (n_weighted 직접 합산)
python3 merge_cutflow.py --stage 3 -i 2_merged_sample/ -o 3_final/


