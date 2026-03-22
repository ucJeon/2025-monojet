import pandas as pd

# CSV 파일 읽기 (첫 줄은 설명이므로 skip)
# df = pd.read_csv("cross_sections.csv", skiprows=1)
df = pd.read_csv("cross_sections.csv", skiprows=0)
df.columns = ["sample", "xsec_pb", "xsec_err_pb"]

# 1. sample 이름 기준으로 오름차순 정렬
df_sorted = df.sort_values(by="sample")

# 2. 총 샘플 개수 출력
print(f"총 샘플 개수: {len(df_sorted)}\n")

# 3. C++ 코드 출력
print("std::vector<SampleInfo> GetSignalSamples() {")
print("    return {")

for _, row in df_sorted.iterrows():
    name = row["sample"]
    xsec = row["xsec_pb"]
    err = row["xsec_err_pb"]
    print(f'        {{ "{name}", {xsec:.8e}, {err:.8e} }},')

print("    };")
print("}")

import pandas as pd
import numpy as np
import re
from itertools import product

# CSV 파일 로딩
df = pd.read_csv("cross_sections.csv")
df.columns = ["sample", "xsec_pb", "xsec_err_pb"]

# sample 이름에서 MX1, lam1, lam2 파싱
def parse_sample_name(name):
    match = re.match(r"Signal_(\d+-\d+)_(\d+-\d+)_(\d+-\d+)", name)
    if match:
        mx1 = float(match.group(1).replace("-", "."))
        lam1 = float(match.group(2).replace("-", "."))
        lam2 = float(match.group(3).replace("-", "."))
        return mx1, lam1, lam2
    return None

# 실제로 존재하는 (MX1, lam1, lam2) 조합
existing = set()
for name in df["sample"]:
    parsed = parse_sample_name(name)
    if parsed:
        existing.add(parsed)

# 정의된 전체 그리드
mx1_list = [1.0, 1.5, 2.0, 2.5]
lam1_list = [0.03,0.05,0.07,0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
lam2_list = [0.04,0.06,0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

full_grid = set(product(mx1_list, lam1_list, lam2_list))

# 누락된 조합 찾기
missing = sorted(full_grid - existing)

# 결과 출력
print(f"✅ 누락된 그리드 포인트 개수: {len(missing)}")
print("MX1     lam1    lam2")
for mx1, lam1, lam2 in missing:
    print(f"{mx1:<7} {lam1:<7} {lam2:<7}")
