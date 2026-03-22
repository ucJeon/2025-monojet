import ROOT
import os

var1_list = ["1-0", "1-5", "2-0", "2-5"]
var2_list = ["0-08", "0-1", "0-3","0-5","0-8","1-0", "2-0"]
var3_list = ["0-08", "0-1", "0-3","0-5","0-8","1-0", "2-0"]

import argparse

parser = argparse.ArgumentParser(description='')
parser.add_argument('--run', type=str,default=None,
                    help='sum the integers (default: find the max)')
args = parser.parse_args()
if args.run == None:
    print("[WARN] PLEASE input: --run <run number>")
    print("[INFO] RECOMENDATION: 1452674")
    exit()

def dash_to_float(s: str) -> float:
    # "1-0" -> 1.0, "0-08" -> 0.08, "2-5" -> 2.5
    return float(s.replace("-", "."))

files_dict = {}
base_path = f"/users/ujeon/2025-monojet/condor/21.DistributionMX1/outputs/{args.run}"

# 파일 분류
for file in os.listdir(base_path):
    parts = file.split("_")
    if len(parts) < 4:
        continue
    var1 = parts[1]
    var2 = parts[2]
    var3 = parts[3].split(".")[0]
    key = (var1, var2, var3)
    if key not in files_dict:
        files_dict[key] = []
    files_dict[key].append(os.path.join(base_path, file))


def get_branch_min_max_manual(tree, branch):
    min_val = float('inf')
    max_val = float('-inf')
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        value = getattr(tree, branch, None)
        if value is None:
            continue
        try:
            val = float(value)
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
        except:
            continue
    if min_val == float('inf') or max_val == float('-inf'):
        return None, None
    return min_val, max_val

def draw_grid_canvas(var1, files_dict, var2_list, var3_list, branch="mx1mass", tree_name="events"):
    ROOT.gStyle.SetOptStat(0)
    canvas = ROOT.TCanvas(f"canvas_{var1}", f"MX1Mass Grid for var1={var1}", 2400, 2400)
    canvas.Divide(7, 7,  0.0001, 0.0001)
    all_hists = []

    # ✅ 1. 기준 X축 범위 계산: (var2, var3) = ("1-0", "1-0")
    ref_key = (var1, "1-0", "1-0")
    ref_min, ref_max = None, None

    if ref_key in files_dict:
        ref_min = float("inf")
        ref_max = float("-inf")
        for file_path in files_dict[ref_key]:
            f = ROOT.TFile.Open(file_path)
            if not f or f.IsZombie(): continue
            tree = f.Get(tree_name)
            bmin, bmax = get_branch_min_max_manual(tree, branch)
            if bmin is not None and bmax is not None:
                ref_min = min(ref_min, bmin)
                ref_max = max(ref_max, bmax)

    if ref_min == float("inf") or ref_max == float("-inf") or ref_min == ref_max:
        print(f"[FATAL] Invalid reference X range for key {ref_key}")
        return
    print(f"[INFO] Reference X range: ({ref_min:.2f}, {ref_max:.2f})")
    
    fix_min = 0
    if var1 == "1-0":
        fix_max = 2000
    elif var1 == "1-5":
        fix_max = 2000
    elif var1 == "2-0":
        fix_max = 2000    
    elif var1 == "2-5":
        fix_max = 2000   
    elif var1 == "2-0":
        fix_max = 2000
 
    fix_nbin = int(fix_max / 7)
    # ✅ 2. 각 subplot에 적용
    for v3 in var3_list:
        for v2 in var2_list:
            row = var3_list.index(v3)
            col = var2_list.index(v2)
            # 4 by 4, 아래는 5 by 5 padindex = (3 - row) * 4 + col + 1
            padindex = (6 - row) * 7 + col + 1
            key = (var1, v2, v3)
            print(key, padindex)
            canvas.cd(padindex)

            if key not in files_dict:
                print(f"[WARN] No data for {key}")
                # 패드에 No entries 텍스트 출력
                latex = ROOT.TLatex()
                latex.SetNDC()
                latex.SetTextFont(42)
                latex.SetTextSize(0.05)
                latex.DrawLatex(0.3, 0.5, "No entries")
                continue

            hist_name = f"h_{var1}_{v2}_{v3}"
            # hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", 100, ref_min, ref_max)
            # hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", fix_nbin, fix_min, fix_max)
            hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", 50, 800, 1200)
            if var1 == "1-0":
                # 중심 1000, ±10%
                hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", 50, 0, 2000)
            elif var1 == "1-5":
                # 중심 1500, ±10%
                hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", 50, 0, 3000)
            elif var1 == "2-0":
                # 중심 2000, ±10%
                hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", 50, 0, 4000)
            elif var1 == "2-5":
                # 중심 2500, ±10%
                hist = ROOT.TH1F(hist_name, f"{var1}, {v2}, {v3};{branch};Entries", 50, 0, 5000)
            mx1f=dash_to_float(var1)
            hist.SetDirectory(0)
            hist.SetStats(0)
            hist.SetTitle("")
            # hist.GetXaxis().SetTitle(r"M_{X_{1}} [GeV]")
            hist.GetXaxis().SetTitle("")
            hist.GetYaxis().SetTitle("")
            hist.GetXaxis().SetLabelSize(0)  # X축 눈금 제거
            hist.GetYaxis().SetLabelSize(0)  # ✅ Y축 눈금 제거
            hist.SetLineWidth(5)          # 기본값이 1, 2–3 정도가 가독성 좋습니다.
            # hist.GetXaxis().SetLabelSize(0.08)   # 상대 크기, 보통 0.03~0.05 사이
            hist.GetXaxis().SetTitleOffset(0.2)
            ROOT.gPad.SetFrameLineWidth(5)
            
            all_hists.append(hist)

            has_entries = False
            for file_path in files_dict[key]:
                f = ROOT.TFile.Open(file_path)
                tree = f.Get(tree_name)
                for i in range(tree.GetEntries()):
                    tree.GetEntry(i)
                    value = getattr(tree, branch, None)
                    if value is not None:
                        try:
                            hist.Fill(float(value))
                            #if hist.Integral() > 0:
                            #    hist.Scale(1.0 / hist.Integral()) 
                            has_entries = True
                        except:
                            continue

            if has_entries:
                text_opt=True
                if text_opt==True:
                    # 1) mean / width 계산 (width = RMS)
                    mean  = hist.GetMean()
                    width = hist.GetRMS()   # 또는 hist.GetStdDev()
                    hist.Draw()
                    # 2) subplot 위에 텍스트 출력
                    txt = ROOT.TLatex()
                    txt.SetNDC(True)
                    txt.SetTextFont(42)
                    txt.SetTextSize(0.1)   # 필요하면 조절
                    txt.SetTextAlign(33)  # Right-Top 정렬 (x는 오른쪽 기준)
                    x = 0.875
                    txt.DrawLatex(x, 0.88, f"{mean:.1f}")
                    txt.DrawLatex(x, 0.78, f"{width:.1f}")
                elif text_opt!=True:
                    hist.Draw()
            else:
                latex = ROOT.TLatex()
                latex.SetNDC()
                latex.SetTextFont(42)
                latex.SetTextSize(0.05)
                latex.DrawLatex(0.3, 0.5, "No entries")

    canvas.Update()
    canvas.SaveAs(f"./MassDistGridPlot/mx1mass_grid_{var1}.png")
    print(f"[SAVE] ./MassDistGridPlot/mx1mass_grid_{var1}.png")

# 실행
for var1 in var1_list:
    print(var1)
    draw_grid_canvas(var1, files_dict, var2_list, var3_list)
