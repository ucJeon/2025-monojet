#!/usr/bin/env python3
import numpy as np
import csv
import ROOT
import os
import argparse

ROOT.gStyle.SetOptStat(0)
ROOT.gROOT.SetBatch(True)

BASE_DIR = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_training/results"


def get_tmva_root_path(target, base_dir=BASE_DIR):
    path1 = os.path.join(base_dir, target, target, "TMVA_output.root")
    path2 = os.path.join(base_dir, target, "TMVA_output.root")
    if os.path.exists(path1):
        return path1
    if os.path.exists(path2):
        return path2
    return None


def GenPlot(target, output_dir, csv_writer=None, base_dir=BASE_DIR):
    frame_line_width = 5
    hist_line_width = 5
    axis_label_size = 0.045
    axis_tick_length = 0.03
    legend_text_size = 0.037

    file_path = get_tmva_root_path(target, base_dir=base_dir)
    if file_path is None:
        print(f"[WARN] TMVA_output.root not found for target: {target}")
        return

    train_S_path = "dataset/Method_BDT/BDT/MVA_BDT_Train_S"
    train_B_path = "dataset/Method_BDT/BDT/MVA_BDT_Train_B"
    test_S_path  = "dataset/Method_BDT/BDT/MVA_BDT_S"
    test_B_path  = "dataset/Method_BDT/BDT/MVA_BDT_B"

    rfile = ROOT.TFile.Open(file_path, "READ")
    if not rfile or rfile.IsZombie():
        print(f"[WARN] Cannot open ROOT file: {file_path}")
        return

    print(f"--- Plotting existing BDT Histograms from: {file_path} ---")

    h_train_signal     = rfile.Get(train_S_path)
    h_train_background = rfile.Get(train_B_path)
    h_test_signal      = rfile.Get(test_S_path)
    h_test_background  = rfile.Get(test_B_path)

    if not all([h_train_signal, h_train_background, h_test_signal, h_test_background]):
        print(f"[WARN] Missing one or more histograms in {file_path}")
        rfile.Close()
        return

    c = ROOT.TCanvas(f"c_{target}", "BDT Response", 1600, 1200)
    c.SetFrameLineWidth(frame_line_width)
    c.SetLogy(False)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.09)
    c.SetBottomMargin(0.12)

    ks_signal     = h_train_signal.KolmogorovTest(h_test_signal, "X")
    ks_background = h_train_background.KolmogorovTest(h_test_background, "X")

    print(f"KS Test (Signal Train vs Signal Test): {ks_signal:.4f}")
    print(f"KS Test (Background Train vs Background Test): {ks_background:.4f}")

    parts     = target.split("_")
    mx1       = parts[0].replace("MX1", "")
    ntrees    = parts[1].replace("nTree", "")
    maxdepth  = parts[2].replace("maxDepth", "")

    if csv_writer is not None:
        csv_writer.writerow([mx1, ntrees, maxdepth, f"{ks_background:.4f}", f"{ks_signal:.4f}"])

    common_title = "BDT Response;BDT Response;Normalized Entries"
    for h in [h_train_signal, h_train_background, h_test_signal, h_test_background]:
        h.SetTitle(common_title)

    h_train_background.SetLineColor(ROOT.kRed)
    h_train_background.SetFillColor(ROOT.kRed)
    h_train_background.SetFillStyle(3345)
    h_train_background.SetLineWidth(hist_line_width)

    h_train_signal.SetLineColor(ROOT.kBlue)
    h_train_signal.SetFillColor(ROOT.kBlue)
    h_train_signal.SetFillStyle(3354)
    h_train_signal.SetLineWidth(hist_line_width)

    h_test_background.SetMarkerColor(ROOT.kRed)
    h_test_background.SetMarkerStyle(20)
    h_test_background.SetMarkerSize(2)
    h_test_background.SetLineColor(ROOT.kRed)

    h_test_signal.SetMarkerColor(ROOT.kBlue)
    h_test_signal.SetMarkerStyle(20)
    h_test_signal.SetMarkerSize(2)
    h_test_signal.SetLineColor(ROOT.kBlue)
    
    num_bins_x = h_train_background.GetNbinsX()
    frame = ROOT.TH1F(f"frame_{target}", common_title, num_bins_x, -0.3, 0.3)
    frame.SetMaximum(0.2)
    frame.SetMinimum(0)

    num_bins_x = h_train_background.GetNbinsX()
    frame = ROOT.TH1F(f"frame_{target}", common_title, num_bins_x, -0.3, 0.3)
    frame.SetMaximum(0.2)
    frame.SetMinimum(0)

    frame.GetXaxis().SetTitleSize(axis_label_size)
    frame.GetXaxis().SetLabelSize(axis_label_size)
    frame.GetXaxis().SetTickLength(axis_tick_length)
    frame.GetYaxis().SetTitleSize(axis_label_size)
    frame.GetYaxis().SetLabelSize(axis_label_size)
    frame.GetYaxis().SetTitleOffset(1.2)
    frame.GetYaxis().SetTickLength(axis_tick_length)
    frame.GetXaxis().SetRangeUser(-0.3, 0.3)
    frame.Draw("AXIS")

    if h_train_background.Integral() > 0:
        h_train_background.DrawNormalized("HIST SAME")
    if h_train_signal.Integral() > 0:
        h_train_signal.DrawNormalized("HIST SAME")
    if h_test_background.Integral() > 0:
        h_test_background.DrawNormalized("P SAME")
    if h_test_signal.Integral() > 0:
        h_test_signal.DrawNormalized("P SAME")

    legend1 = ROOT.TLegend(0.25, 0.79, 0.55, 0.89)
    legend1.SetBorderSize(0)
    legend1.SetFillStyle(0)
    legend1.SetTextSize(legend_text_size)
    legend1.AddEntry(h_train_signal, "Signal (Train)", "F")
    legend1.AddEntry(h_train_background, "Background (Train)", "F")
    legend1.Draw()

    legend2 = ROOT.TLegend(0.55, 0.79, 0.85, 0.89)
    legend2.SetBorderSize(0)
    legend2.SetFillStyle(0)
    legend2.SetTextSize(legend_text_size)
    legend2.AddEntry(h_test_signal, "Signal (Test)", "P")
    legend2.AddEntry(h_test_background, "Background (Test)", "P")
    legend2.Draw()
    
    latex = ROOT.TLatex()
    latex.SetNDC()

# ----------------------------
# (1) Left-top: Title (bold 느낌)
# ----------------------------
    latex.SetTextFont(62)  # bold
    latex.SetTextSize(0.05)
    latex.SetTextAlign(11)  # left-top
    latex.DrawLatex(0.13, 0.94, "BDT Response")

# ----------------------------
# (2) Right-top: mass info
# ----------------------------
# mx1 = "1-0" → "1.0"
    mx1_val = mx1.replace("-", ".")
    latex.SetTextFont(62)
    latex.SetTextSize(0.05)
    latex.SetTextAlign(31)  # right-top
    latex.DrawLatex(0.95, 0.94, f"m_{{X_{{1}}}} = {mx1_val} TeV")

# ----------------------------
# (3) KS values (left area 아래쪽으로)
# ----------------------------
    latex.SetTextAlign(11)
    latex.SetTextSize(0.035)

    # latex.DrawLatex(0.3, 0.75, f"KS p-value (S) = {ks_signal:.4f}")
    # latex.DrawLatex(0.3, 0.70, f"KS p-value (B) = {ks_background:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"BDT_{target}.png")
    c.SaveAs(output_path)
    print(f"Plot saved as {output_path}")

    rfile.Close()
    c.Close()
    del c
    del rfile


def Draw2DCorr_MET_BDT(target, output_dir, base_dir=BASE_DIR):
    file_path = get_tmva_root_path(target, base_dir=base_dir)
    if file_path is None:
        print(f"[WARN] TMVA_output.root not found for target: {target}")
        return

    f = ROOT.TFile.Open(file_path, "READ")
    if not f or f.IsZombie():
        print(f"[WARN] cannot open {file_path}")
        return

    testTree = f.Get("dataset/TestTree")
    if not testTree:
        print(f"[WARN] dataset/TestTree not found in {file_path}")
        f.Close()
        return

    c2 = ROOT.TCanvas(f"c2_{target}", f"BDT vs METPt ({target})", 800, 600)
    c2.SetLeftMargin(0.12)
    c2.SetBottomMargin(0.12)

    h_frame = ROOT.TH2F(
        f"h_frame_{target}",
        "BDT response vs METPt (Test);METPt [GeV];BDT response",
        50, 0, 1000, 50, -1.0, 1.0
    )
    h_frame.Draw()

    testTree.SetMarkerStyle(20)
    testTree.SetMarkerSize(0.7)

    testTree.SetMarkerColor(ROOT.kRed)
    testTree.Draw("BDT:METPt", "classID==1", "P SAME")

    testTree.SetMarkerColor(ROOT.kBlue)
    testTree.Draw("BDT:METPt", "classID==0", "P SAME")

    bg_dummy = ROOT.TH1F(f"bg_dummy_{target}", "", 1, 0, 1)
    bg_dummy.SetMarkerStyle(20)
    bg_dummy.SetMarkerSize(0.7)
    bg_dummy.SetMarkerColor(ROOT.kRed)

    sig_dummy = ROOT.TH1F(f"sig_dummy_{target}", "", 1, 0, 1)
    sig_dummy.SetMarkerStyle(20)
    sig_dummy.SetMarkerSize(0.7)
    sig_dummy.SetMarkerColor(ROOT.kBlue)

    leg = ROOT.TLegend(0.15, 0.75, 0.45, 0.88)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.AddEntry(bg_dummy, "Background (Test)", "P")
    leg.AddEntry(sig_dummy, "Signal (Test)", "P")
    leg.Draw()

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"BDT_vs_METPt_scatter_{target}.png")
    c2.SaveAs(out_path)
    print(f"2D scatter plot saved as {out_path}")

    f.Close()
    c2.Close()
    del c2
    del f


def Auto(tag, output_base, version="v2", base_dir=BASE_DIR):
    os.makedirs(output_base, exist_ok=True)

    csv_path = os.path.join(output_base, f"ks_results_{tag}_{version}.csv")
    csv_file = open(csv_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["mx1", "ntrees", "maxdepth", "KSval_B", "KSval_S"])

    for mx1 in ["1-0", "1-5", "2-0", "2-5"]:
        for ntree in np.linspace(1000, 5000, 9):
            for maxdepth in np.linspace(3, 7, 5):
                target = f"MX1{mx1}_nTree{int(ntree)}_maxDepth{int(maxdepth)}_{tag}_{version}"
                GenPlot(target, output_base, csv_writer, base_dir=base_dir)
                Draw2DCorr_MET_BDT(target, output_base, base_dir=base_dir)

    csv_file.close()
    print(f"[INFO] CSV saved: {csv_path}")


def build_target(mx1: str, ntree: int, maxdepth: int, tag: str, version: str) -> str:
    """조각 인수로 target 문자열 조립."""
    return f"MX1{mx1}_nTree{ntree}_maxDepth{maxdepth}_{tag}_{version}"


def main():
    parser = argparse.ArgumentParser(description="Draw TMVA BDT output plots.")
    parser.add_argument("--mode", choices=["single", "auto"], required=True,
                        help="single: one target, auto: scan predefined grid")

    # ── single 모드용 조각 인수 ──────────────────────────────────────────
    parser.add_argument("--mx1", type=str, default=None,
                        help='MX1 값, e.g. "1-0", "2-5"')
    parser.add_argument("--ntree", type=int, default=None,
                        help='nTree 값, e.g. 2500')
    parser.add_argument("--maxdepth", type=int, default=None,
                        help='maxDepth 값, e.g. 4')

    # ── 공통 ────────────────────────────────────────────────────────────
    parser.add_argument("--tag", type=str, default="uc",
                        help='Tag, e.g. "uc"')
    parser.add_argument("--version", type=str, default="v2",
                        help='Version, e.g. "v2"')
    parser.add_argument("--output", type=str, required=True,
                        help="Directory to save plots/csv")
    parser.add_argument("--base", type=str, default=BASE_DIR,
                        help="Base results directory")
    parser.add_argument("--no-scatter", action="store_true",
                        help="Skip 2D scatter plot")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.mode == "single":
        if any(v is None for v in [args.mx1, args.ntree, args.maxdepth]):
            parser.error("single 모드에는 --mx1, --ntree, --maxdepth 가 모두 필요합니다.")

        target = build_target(args.mx1, args.ntree, args.maxdepth, args.tag, args.version)
        print(f"[INFO] target: {target}")

        csv_path = os.path.join(args.output, f"ks_results_single_{target}.csv")
        with open(csv_path, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["mx1", "ntrees", "maxdepth", "KSval_B", "KSval_S"])
            GenPlot(target, args.output, csv_writer, base_dir=args.base)
            if not args.no_scatter:
                Draw2DCorr_MET_BDT(target, args.output, base_dir=args.base)

        print(f"[INFO] CSV saved: {csv_path}")

    elif args.mode == "auto":
        Auto(args.tag, args.output, version=args.version, base_dir=args.base)


if __name__ == "__main__":
    main()

