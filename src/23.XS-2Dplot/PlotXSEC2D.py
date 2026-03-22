import ROOT
import csv
from collections import defaultdict

# 파일명
input_file = "cross_sections.csv"

# MX1별 데이터 분류
data_by_mx1 = defaultdict(list)
lam_values_set = set()

# 입력 파일 읽기
with open(input_file, "r") as f:
    reader = csv.reader(f)
    next(reader)  # 헤더 스킵
    for row in reader:
        sample_name, xsec, xsec_err = row
        xsec = float(xsec)
        # 샘플 이름에서 MX1, lam1, lam2 파싱
        try:
            parts = sample_name.split("_")
            mx1 = float(parts[1].replace("-", "."))
            lam1 = float(parts[2].replace("-", "."))
            # lam2 = float(parts[3].replace("-", "."))
            lam2 = float(parts[3].replace("-", ".").rstrip(".0"))
        except Exception as e:
            print(f"[ERROR] Failed to parse sample name '{sample_name}': {e}")
            continue

        data_by_mx1[mx1].append((lam1, lam2, xsec))
        lam_values_set.update([lam1, lam2])


# lam 리스트 및 매핑 자동 생성
#labels = sorted(round(l, 2) for l in lam_values_set)
#lam_mapping = {val: idx + 1 for idx, val in enumerate(labels)}

# lam1, lam2 명시적 정의
lam1_list = [0.03, 0.05, 0.07, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 2.0]
lam2_list = [0.04, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 2.0]

# 각 라벨에 대한 매핑 (bin 번호 = 1-based)
lam1_mapping = {round(val, 2): idx + 1 for idx, val in enumerate(lam1_list)}
lam2_mapping = {round(val, 2): idx + 1 for idx, val in enumerate(lam2_list)}


# ROOT 스타일
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetPalette(ROOT.kRainBow)

# MX1별 그림 그리기
for mx1, entries in data_by_mx1.items():
    nbins_x = len(lam1_list)
    nbins_y = len(lam2_list)

    hist = ROOT.TH2F(
        f"hlego2_mx1_{mx1}",
        f"Cross Section [pb] (MX1 = {mx1:.1f} TeV);#lambda1;#lambda2",
        nbins_x, 0.5, nbins_x + 0.5,
        nbins_y, 0.5, nbins_y + 0.5
    )
    # 축 라벨 설정
    for i, val in enumerate(lam1_list):
        hist.GetXaxis().SetBinLabel(i + 1, str(val))
    for j, val in enumerate(lam2_list):
        hist.GetYaxis().SetBinLabel(j + 1, str(val))

    # 히스토그램 채우기
    for lam1, lam2, xsec in entries:
        lam1_rounded = round(lam1, 2)
        lam2_rounded = round(lam2, 2)

        if lam1_rounded not in lam1_mapping or lam2_rounded not in lam2_mapping:
            print(f"[SKIP] (λ1, λ2)=({lam1_rounded}, {lam2_rounded}) not in predefined list.")
            continue

        binX = lam1_mapping[lam1_rounded]
        binY = lam2_mapping[lam2_rounded]
        hist.SetBinContent(binX, binY, xsec)
        print(f"[FILL] MX1={mx1:.1f}, binX={binX}, binY={binY}, xsec={xsec}")

    # 캔버스 생성 및 저장
    canvas = ROOT.TCanvas(f"clego2_mx1_{mx1}", f"MX1 = {mx1:.1f}", 600, 400)
    canvas.SetLogz()
    hist.Draw("LEGO2Z")

    outname = f"./XSEC2D/{mx1:.1f}_TeV_xsec_dist.png"
    canvas.SaveAs(outname)
    print(f"[Saved] {outname}")


# import csv
# from collections import defaultdict

# # 파일명
# input_file = "cross_sections.csv"
# # MX1별 데이터 분류
# data_by_mx1 = defaultdict(list)

# # lam 값 → bin index 매핑
# lam_mapping = {
#     0.08: 1,
#     0.1:  2,
#     0.5:  3,
#     1.0:  4,
# }

# # 라벨용 리스트
# labels = ["0.08", "0.1", "0.5", "1.0"]

# # 입력 파일 읽기
# with open(input_file, "r") as f:
#     reader = csv.reader(f)
#     for row in reader:
#         mx1, lam1, lam2, xsec, xsec_err = row
#         mx1 = float(mx1)
#         lam1 = float(lam1)
#         lam2 = float(lam2)
#         xsec = float(xsec)
#         data_by_mx1[mx1].append((lam1, lam2, xsec))

# # ROOT 스타일
# ROOT.gStyle.SetOptStat(0)
# ROOT.gStyle.SetPalette(ROOT.kRainBow)

# # MX1별 그림 그리기
# for mx1, entries in data_by_mx1.items():
#     hist = ROOT.TH2F(
#         f"hlego2_mx1_{mx1}",
#         f"Cross Section [pb] (MX1 = {mx1:.1f} TeV);#lambda1;#lambda2",
#         4, 0.5, 4.5,
#         4, 0.5, 4.5
#     )

#     # 축 라벨
#     for i, label in enumerate(labels):
#         hist.GetXaxis().SetBinLabel(i+1, label)
#         hist.GetYaxis().SetBinLabel(i+1, label)

#     # 데이터 채우기
#     for lam1, lam2, xsec in entries:
#         binX = lam_mapping.get(lam1)
#         binY = lam_mapping.get(lam2)
#         if not binX or not binY:
#             print(f"[WARNING] Unknown lambda: {lam1}, {lam2}")
#             continue
#         hist.SetBinContent(binX, binY, xsec)
#         print(binX, binY, xsec)

#     # 캔버스 및 드로우
#     canvas = ROOT.TCanvas(f"clego2_mx1_{mx1}", f"MX1 = {mx1:.1f}", 800, 800)
#     canvas.SetLogz()  # 이 줄을 추가
#     hist.Draw("LEGO2Z")

#     outname = f"{mx1:.1f}_TeV_xsec_dist_lego2z.png"
#     canvas.SaveAs(outname)
#     print(f"[Saved] {outname}")
