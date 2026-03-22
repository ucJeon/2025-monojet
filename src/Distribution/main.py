"""
main.py
-------
실행하면 sample 목록을 출력하고 index를 입력받아
해당 sample의 BDT response PNG를 저장한다.

  0번 → Signal (mx1, lam1, lam2 추가 입력)
  1~N → Background process
        → whole     : 모든 파일 합산 PNG 1장
        → subsample : 파일별 개별 PNG
"""

import ROOT
from array import array
from pathlib import Path

from bdt_eval import load_bdt_reader, fill_histogram, fill_bkg_histograms, yield_at_cut
from plot_bdt import plot_bdt_each_bkg


# ══════════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════════

DATA_DIR  = Path("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_training/results"
                 "6.1.MergingFiles/z_300fb_COMPLETE_v1.0.2/SPLIT")

FLAG      = "v3f0p5SPLIT"
N_TREES   = 2000
MAX_DEPTH = 4
N_BINS    = 1000
WEIGHT_BR = "weight_corr"

def xml_path(mx1, n_trees=N_TREES, max_depth=MAX_DEPTH, flag=FLAG):
    base = "/users/ujeon/2025-monojet/condor/6.BDTtrainning/6.5.BDT_Result"
    return (f"{base}/MX1{mx1}_nTree{n_trees}_maxDepth{max_depth}_{flag}"
            f"/dataset/weights/TMVAClassification_BDT.weights.xml")


# ══════════════════════════════════════════════════════════
# Background 파일 목록
# ══════════════════════════════════════════════════════════

BKG_PROCESS = {
    "ttbar"  : [f"ttbar.{i}.root"  for i in range(1, 10)],
    "wjets"  : [f"wjets.{i}.root"  for i in range(2, 9)],
    "ww2l2v" : ["ww2l2v.0.root"],
    "wwlv2q" : [f"wwlv2q.{i}.root" for i in range(1, 10)],
    "wz2l2q" : [f"wz2l2q.{i}.root" for i in range(1, 10)],
    "wz3l1v" : ["wz3l1v.0.root"],
    "wzlv2q" : [f"wzlv2q.{i}.root" for i in range(1, 10)],
    "zjets"  : [f"zjets.{i}.root"  for i in range(2, 9)],
    "zz4l"   : ["zz4l.0.root"],
}

BKG_LABELS = list(BKG_PROCESS.keys())


# ══════════════════════════════════════════════════════════
# 출력 헬퍼
# ══════════════════════════════════════════════════════════

def print_sample_list():
    print("\n[ Sample 목록 ]")
    print("  0 : Signal  (mx1, lam1, lam2 입력 필요)")
    for i, label in enumerate(BKG_LABELS, start=1):
        print(f"  {i} : {label}")
    print()


def ask_mode():
    print("  1 : whole      (모든 파일 합산 → PNG 1장)")
    print("  2 : subsample  (파일별 개별 PNG)")
    return input("mode 입력 → ").strip()


# ══════════════════════════════════════════════════════════
# Signal PNG
# ══════════════════════════════════════════════════════════

def run_signal(mx1: str, lam1: str, lam2: str,
               out_dir: str = "./plots"):

    xml = xml_path(mx1)
    if not Path(xml).exists():
        print(f"[ERROR] XML 없음: {xml}")
        return

    reader, var_bufs, var_names = load_bdt_reader(xml, FLAG)

    sig_fname = f"Signal_{mx1}_{lam1}_{lam2}.0.root"
    sig_path  = DATA_DIR / sig_fname
    if not sig_path.exists():
        print(f"[ERROR] Signal 없음: {sig_path}")
        return

    sig_weight = WEIGHT_BR
    f_tmp = ROOT.TFile.Open(str(sig_path))
    if f_tmp and not f_tmp.IsZombie():
        t_tmp = f_tmp.Get("events")
        if t_tmp and not t_tmp.GetListOfBranches().FindObject(WEIGHT_BR):
            sig_weight = "weight"
            print(f"  [WARN] weight_corr 없음 → weight 사용")
        f_tmp.Close()

    sig_label = f"Signal_{mx1}_{lam1}_{lam2}"
    print(f"[INFO] {sig_label} 처리 중...")
    h = fill_histogram(
        reader, var_bufs, var_names,
        root_file     = str(sig_path),
        weight_branch = sig_weight,
        n_bins        = N_BINS,
        hist_name     = f"h_{sig_label}",
        hist_title    = sig_label,
    )
    plot_bdt_each_bkg({sig_label: h}, out_dir=out_dir)


# ══════════════════════════════════════════════════════════
# Background PNG
# ══════════════════════════════════════════════════════════

def run_bkg_whole(reader, var_bufs, var_names,
                  label: str, out_dir: str = "./plots"):
    """모든 파일 합산 → PNG 1장."""

    fnames  = BKG_PROCESS[label]
    h_total = ROOT.TH1F(f"h_{label}", f"BDT response — {label}", N_BINS, -1, 1)
    h_total.SetDirectory(0)
    h_total.Sumw2()

    for fname in fnames:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  [WARN] 없음: {fname} — skip")
            continue
        h_tmp = fill_histogram(
            reader, var_bufs, var_names,
            root_file     = str(fpath),
            weight_branch = WEIGHT_BR,
            n_bins        = N_BINS,
            hist_name     = f"h_tmp_{label}_{fname}",
        )
        h_total.Add(h_tmp)

    plot_bdt_each_bkg({label: h_total}, out_dir=out_dir)


def run_bkg_subsample(reader, var_bufs, var_names,
                      label: str, out_dir: str = "./plots"):
    """파일별 개별 PNG. 파일명의 번호를 label에 붙여서 저장."""

    fnames = BKG_PROCESS[label]
    hists  = {}

    for fname in fnames:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  [WARN] 없음: {fname} — skip")
            continue

        # "ttbar.3.root" → "ttbar_3" 형태로 label 생성
        stem       = Path(fname).stem          # "ttbar.3"
        sub_label  = stem.replace(".", "_")    # "ttbar_3"

        print(f"  [INFO] {fname} 처리 중...")
        h = fill_histogram(
            reader, var_bufs, var_names,
            root_file     = str(fpath),
            weight_branch = WEIGHT_BR,
            n_bins        = N_BINS,
            hist_name     = f"h_{sub_label}",
            hist_title    = sub_label,
        )
        hists[sub_label] = h

    plot_bdt_each_bkg(hists, out_dir=out_dir)


# ══════════════════════════════════════════════════════════
# 인터랙티브 실행
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":

    print_sample_list()
    idx = int(input("index 입력 → ").strip())

    if idx == 0:
        mx1  = input("mx1  (예: 1-0) → ").strip()
        lam1 = input("lam1 (예: 0-1) → ").strip()
        lam2 = input("lam2 (예: 0-1) → ").strip()
        run_signal(mx1, lam1, lam2)

    elif 1 <= idx <= len(BKG_LABELS):
        label = BKG_LABELS[idx - 1]
        mx1   = input("mx1  (BDT weights 선택용, 예: 1-0) → ").strip()

        xml = xml_path(mx1)
        if not Path(xml).exists():
            print(f"[ERROR] XML 없음: {xml}")
        else:
            reader, var_bufs, var_names = load_bdt_reader(xml, FLAG)

            print()
            mode = ask_mode()

            if mode == "1":
                run_bkg_whole(reader, var_bufs, var_names, label)
            elif mode == "2":
                run_bkg_subsample(reader, var_bufs, var_names, label)
            else:
                print(f"[ERROR] 유효하지 않은 mode: {mode}")

    else:
        print(f"[ERROR] 유효하지 않은 index: {idx}  (0 ~ {len(BKG_LABELS)})")
