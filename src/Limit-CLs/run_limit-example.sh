# lam1plot만
python3 run_limit.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --lam1plot
# --lam1plot은 --cut 과 무관하게 limit_summary.csv 전체를 스캔해서 모든 cut 포인트를 한 번에 그립니다.

# 전부 (planes + limits + lam1plot)
python3 run_limit.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300 --all

# 기본 (planes + limits, lam1plot 제외)
python3 run_limit.py --version v2 --ntree 2000 --maxdepth 4 --cut 0.1300
