# Test Run
# 파이썬에서 생성한 파일명 규칙에 맞춰 'p'로 변경한 변수를 정의합니다.
c10="0p1050"
c15="0p1350"
c20="0p1440"
c25="0p1520"

Lumi_list="300 3000"
# Lumi_list="3000"

for lumi in $Lumi_list; do
  # 1.0 TeV
  DC1p0="./datacards/datacard_lumi${lumi}_mx11-0_cut${c10}_stats.txt"
  combine -M AsymptoticLimits $DC1p0 -n .Lumi${lumi}.MX10 -m 1000

  # 1.5 TeV
  DC1p5="./datacards/datacard_lumi${lumi}_mx11-5_cut${c15}_stats.txt"
  combine -M AsymptoticLimits $DC1p5 -n .Lumi${lumi}.MX15 -m 1500

  # 2.0 TeV
  DC2p0="./datacards/datacard_lumi${lumi}_mx12-0_cut${c20}_stats.txt"
  combine -M AsymptoticLimits $DC2p0 -n .Lumi${lumi}.MX20 -m 2000

  # 2.5 TeV
  DC2p5="./datacards/datacard_lumi${lumi}_mx12-5_cut${c25}_stats.txt"
  combine -M AsymptoticLimits $DC2p5 -n .Lumi${lumi}.MX25 -m 2500
done
