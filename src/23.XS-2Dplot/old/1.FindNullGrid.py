import csv
from itertools import product

# 기준 조합 정의
mx1_values = ['1-0', '1-5', '2-0','2-5']
lam1_values = ['0-03','0-05','0-07','0-08', '0-1', '0-15', '0-2', '0-3', '0-4', '0-5', '0-6', '0-7', '0-8', '0-9', '1-0','2-0']
lam2_values = ['0-04','0-06','0-08', '0-1', '0-15', '0-2', '0-3', '0-4', '0-5', '0-6', '0-7', '0-8', '0-9', '1-0','2-0']

# 전체 가능한 조합 생성
expected_samples = set(
    f"Signal_{mx1}_{lam1}_{lam2}"
    for mx1, lam1, lam2 in product(mx1_values, lam1_values, lam2_values)
)

# CSV 파일에서 실제 존재하는 sample 목록 읽기
existing_samples = set()
with open("cross_sections.csv", newline='') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # skip header
    for row in reader:
        sample = row[0].strip()
        if "." in sample:
            sample = sample.split(".")[0]  # Signal_1-0_0-3_0-4.0 -> Signal_1-0_0-3_0-4
        existing_samples.add(sample)

# 누락된 조합 계산
missing_samples = expected_samples - existing_samples

# 출력
print("❌ 누락된 조합:")
for sample in sorted(missing_samples):
    print(sample)

# 선택사항: 결과 저장
with open("missing_samples.txt", "w") as f:
    for sample in sorted(missing_samples):
        f.write(f"{sample}\n")
