import pandas as pd

base_path = "cross_sections.csv"
add_path  = "cross_sections_with_added_new_sample_250807.csv"
out_path  = "cross_sections_updated.csv"  # 결과 파일 (원하면 cross_sections.csv로 바꿔서 덮어쓰기 가능)

# 읽기
base = pd.read_csv(base_path)
add  = pd.read_csv(add_path)

# 컬럼 이름 표준화(공백 제거)
base.columns = [c.strip() for c in base.columns]
add.columns  = [c.strip() for c in add.columns]

key = "sample"
if key not in base.columns or key not in add.columns:
    raise ValueError(f"'{key}' 컬럼이 없어요. base={base.columns.tolist()}, add={add.columns.tolist()}")

# sample 값 표준화(앞뒤 공백 제거)
base[key] = base[key].astype(str).str.strip()
add[key]  = add[key].astype(str).str.strip()

# add에서 base에 없는 sample만 추출
missing = add[~add[key].isin(set(base[key]))].copy()

# (선택) base에 있는 컬럼만 맞춰서 추가
# add에만 있는 컬럼은 버리고 싶으면 아래 라인 사용
missing = missing.reindex(columns=base.columns)

# 합치기 + sample 중복 방지(혹시 모르니 마지막에 한번 더)
merged = pd.concat([base, missing], ignore_index=True)
merged = merged.drop_duplicates(subset=[key], keep="first")

# 저장
merged.to_csv(out_path, index=False)

print(f"base rows: {len(base)}")
print(f"added missing rows: {len(missing)}")
print(f"merged rows: {len(merged)}")
print(f"saved -> {out_path}")
