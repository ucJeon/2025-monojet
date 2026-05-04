#!/bin/bash
# run_asymptotic_syst.sh
# Incremental systematic uncertainty study
# mode: none / stats / sys1 / sys2 / sys3 / sys4

c10="0p1050"
c15="0p1350"
c20="0p1440"
c25="0p1520"

Lumi_list="300 3000"
Mode_list="none stats sys1 sys2 sys3"

for lumi in $Lumi_list; do
  for mode in $Mode_list; do

    echo ""
    echo "============================================================"
    echo " lumi=${lumi}  mode=${mode}"
    echo "============================================================"

    # 1.0 TeV
    DC="./datacards/datacard_lumi${lumi}_mx11-0_cut${c10}_${mode}.txt"
    echo "[RUN] ${DC}"
    combine -M AsymptoticLimits $DC \
        -n .Lumi${lumi}.MX10.${mode} \
        -m 1000 \
        --run blind \
        | grep -E "Expected|Observed"

    # 1.5 TeV
    DC="./datacards/datacard_lumi${lumi}_mx11-5_cut${c15}_${mode}.txt"
    echo "[RUN] ${DC}"
    combine -M AsymptoticLimits $DC \
        -n .Lumi${lumi}.MX15.${mode} \
        -m 1500 \
        --run blind 2>/dev/null \
        | grep -E "Expected|Observed"

    # 2.0 TeV
    DC="./datacards/datacard_lumi${lumi}_mx12-0_cut${c20}_${mode}.txt"
    echo "[RUN] ${DC}"
    combine -M AsymptoticLimits $DC \
        -n .Lumi${lumi}.MX20.${mode} \
        -m 2000 \
        --run blind 2>/dev/null \
        | grep -E "Expected|Observed"

    # 2.5 TeV
    DC="./datacards/datacard_lumi${lumi}_mx12-5_cut${c25}_${mode}.txt"
    echo "[RUN] ${DC}"
    combine -M AsymptoticLimits $DC \
        -n .Lumi${lumi}.MX25.${mode} \
        -m 2500 \
        --run blind 2>/dev/null \
        | grep -E "Expected|Observed"

  done
done

echo ""
echo "[ALL DONE]"
