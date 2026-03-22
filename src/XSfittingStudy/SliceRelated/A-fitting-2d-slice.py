import os
import numpy as np
import pandas as pd
import argparse
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import ROOT

# -----------------------------------------------------------------------
# ROOT Global Settings
# -----------------------------------------------------------------------
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)
ROOT.gStyle.SetLineWidth(3)
ROOT.gStyle.SetFrameLineWidth(3)
ROOT.gStyle.SetHistLineWidth(3)
ROOT.gStyle.SetPadTickX(1)
ROOT.gStyle.SetPadTickY(1)
ROOT.gStyle.SetTitleFont(42, "XYZ")
ROOT.gStyle.SetLabelFont(42, "XYZ")
ROOT.gStyle.SetTitleSize(0.05, "XYZ")
ROOT.gStyle.SetLabelSize(0.045, "XYZ")
ROOT.gStyle.SetTitleOffset(1.2, "Y")
ROOT.gStyle.SetPadLeftMargin(0.14)
ROOT.gStyle.SetPadRightMargin(0.05)
ROOT.gStyle.SetPadBottomMargin(0.13)
ROOT.gStyle.SetPadTopMargin(0.08)

# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Integrated 2D-fit, Heatmap, Surface and Slice plots")
parser.add_argument("--slice", type=str, required=True, choices=["lam1", "lam2"])
parser.add_argument("--fix",   type=float, required=True)
args = parser.parse_args()

print(f"Executing: slice={args.slice}, fix={args.fix}")

# -----------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------
def model_2d(X, A, B=4.0):
    x1, x2 = X
    return A * (x1**2 * x2**2) / (B * x1**2 + x2**2)

def safe_float(s):
    """Handles parsing issues like '1.0.0' or '1-0-0'"""
    if s is None: return np.nan
    dotted = str(s).replace("-", ".")
    cleaned = ".".join(dotted.split(".")[:2])
    try: return float(cleaned)
    except: return np.nan

def select_close(s: pd.Series, val: float, atol: float = 1e-9) -> np.ndarray:
    return np.isclose(s.to_numpy(dtype=float), val, atol=atol, rtol=0)

# -----------------------------------------------------------------------
# Paths & Data Loading
# -----------------------------------------------------------------------
csv_path = "/users/ujeon/2025-monojet/condor/23.XS-2Dplot/cross_sections.csv"
out_dir  = f"Study_{args.slice}-{args.fix}"
os.makedirs(out_dir, exist_ok=True)

df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()
parts = df["sample"].str.split("_", expand=True)

df["mx1"]  = parts[1].apply(safe_float)
df["lam1"] = parts[2].apply(safe_float)
df["lam2"] = parts[3].apply(safe_float)

allowed_2d = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
df_2d = df[df["lam1"].isin(allowed_2d) & df["lam2"].isin(allowed_2d)].copy()
B_FIXED = 4.0
THRESH = 0.10 # 10% threshold

# -----------------------------------------------------------------------
# Main Loop per mx1
# -----------------------------------------------------------------------
for mx1_val, df_mx1_all in df.groupby("mx1"):
    df_2d_mx1 = df_2d[np.isclose(df_2d["mx1"].to_numpy(dtype=float), mx1_val)]
    if df_2d_mx1.empty: continue

    x1_2d = df_2d_mx1["lam1"].to_numpy(dtype=float)
    x2_2d = df_2d_mx1["lam2"].to_numpy(dtype=float)
    z_2d  = df_2d_mx1["xsec [pb]"].to_numpy(dtype=float)
    zerr_2d = df_2d_mx1["xsec_err [pb]"].to_numpy(dtype=float)
    zerr_2d = np.where(zerr_2d <= 0, np.maximum(1e-12, 0.05 * np.abs(z_2d)), zerr_2d)

    try:
        # ---- Step 1: 2-D Fit ----
        popt, pcov = curve_fit(
            lambda X, A: model_2d(X, A, B_FIXED),
            (x1_2d, x2_2d), z_2d, p0=[z_2d.max()],
            sigma=zerr_2d, absolute_sigma=True
        )
        A_opt = float(popt[0])
        A_err = float(np.sqrt(np.diag(pcov))[0])

        # ---- Step 2: Deviation Heatmap (Matplotlib) ----
        l1_vals = np.sort(df_2d_mx1["lam1"].unique())
        l2_vals = np.sort(df_2d_mx1["lam2"].unique())
        dev_mat = np.full((len(l2_vals), len(l1_vals)), np.nan)
        bg_mat  = np.ones_like(dev_mat) 

        for _, r in df_2d_mx1.iterrows():
            i = np.where(l2_vals == r["lam2"])[0][0]
            j = np.where(l1_vals == r["lam1"])[0][0]
            pred = model_2d((r["lam1"], r["lam2"]), A_opt, B_FIXED)
            dev = abs(r["xsec [pb]"] - pred) / pred * 100.0
            dev_mat[i, j] = dev
            if dev > (THRESH * 100): bg_mat[i, j] = 0.85 # Gray for Outliers

        fig_hm, ax_hm = plt.subplots(figsize=(8, 7), dpi=120)
        ax_hm.imshow(bg_mat, origin="lower", cmap="gray", vmin=0, vmax=1, aspect="auto")
        ax_hm.set_title(f"Rel. Deviation [%] | mx1={mx1_val:g} TeV\n(A={A_opt:.4g}, B={B_FIXED})")
        ax_hm.set_xticks(np.arange(len(l1_vals))); ax_hm.set_xticklabels(l1_vals)
        ax_hm.set_yticks(np.arange(len(l2_vals))); ax_hm.set_yticklabels(l2_vals)
        ax_hm.set_xlabel(r"$\lambda_1$"); ax_hm.set_ylabel(r"$\lambda_2$")

        for i in range(len(l2_vals)):
            for j in range(len(l1_vals)):
                v = dev_mat[i, j]
                if not np.isnan(v):
                    ax_hm.text(j, i, f"{v:.1f}%", ha="center", va="center",
                               color="red" if v > 10 else "black", weight="bold" if v > 10 else "normal")
        fig_hm.savefig(os.path.join(out_dir, f"heatmap_mx1_{mx1_val:g}.png"))
        plt.close(fig_hm)

        # ---- Step 3: 2D Surface Plot (Matplotlib) ----
        rel_dev_2d = np.abs(z_2d - model_2d((x1_2d, x2_2d), A_opt, B_FIXED)) / model_2d((x1_2d, x2_2d), A_opt, B_FIXED)
        mask_drop = rel_dev_2d > THRESH
        mask_in = ~mask_drop

        fig_3d = plt.figure(figsize=(8, 6), dpi=120)
        ax3 = fig_3d.add_subplot(111, projection="3d")
        ax3.scatter(x1_2d[mask_in], x2_2d[mask_in], z_2d[mask_in], c="k", s=25, label="Inliers")
        if np.any(mask_drop):
            ax3.scatter(x1_2d[mask_drop], x2_2d[mask_drop], z_2d[mask_drop], c="r", marker="x", s=50, label="Outliers")
        
        g1, g2 = np.meshgrid(np.linspace(0.1, 1.0, 30), np.linspace(0.1, 1.0, 30))
        ax3.plot_surface(g1, g2, model_2d((g1, g2), A_opt, B_FIXED), cmap="viridis", alpha=0.4, edgecolor="none")
        ax3.set_xlabel(r"$\lambda_1$"); ax3.set_ylabel(r"$\lambda_2$"); ax3.set_zlabel(r"$\sigma$ [pb]")
        ax3.view_init(elev=25, azim=-135)
        fig_3d.savefig(os.path.join(out_dir, f"surface_mx1_{mx1_val:g}.png"), bbox_inches="tight")
        plt.close(fig_3d)

        # ---- Step 4: Slice Plot (ROOT) ----
        fixed_lam = float(args.fix)
        if args.slice == "lam2":
            grp = df_mx1_all[select_close(df_mx1_all["lam2"], fixed_lam)]
            scan_col = "lam1"; x_label = "#lambda_{1}"; title_fix = f"#lambda_{{2}} = {fixed_lam:.1f}"
        else:
            grp = df_mx1_all[select_close(df_mx1_all["lam1"], fixed_lam)]
            scan_col = "lam2"; x_label = "#lambda_{2}"; title_fix = f"#lambda_{{1}} = {fixed_lam:.1f}"

        grp = grp[grp[scan_col].isin(allowed_2d)].sort_values(scan_col)
        if len(grp) < 2: continue

        x_vals = grp[scan_col].to_numpy()
        y_vals = grp["xsec [pb]"].to_numpy()
        yerr_vals = np.where(grp["xsec_err [pb]"] <= 0, 0.05 * y_vals, grp["xsec_err [pb]"])

        # Iterative Drop within Slice
        f_temp_expr = f"{A_opt}*((x*x)*({fixed_lam}**2))/({B_FIXED}*(x*x)+({fixed_lam}**2))" if args.slice=="lam2" else \
                      f"{A_opt}*(({fixed_lam}**2)*(x*x))/({B_FIXED}*({fixed_lam}**2)+(x*x))"
        f_temp = ROOT.TF1("f_temp", f_temp_expr, 0.1, 1.0)
        
        x_it, y_it, yerr_it = x_vals.copy(), y_vals.copy(), yerr_vals.copy()
        dropped = []
        while len(x_it) > 2:
            y_mod = np.array([f_temp.Eval(xi) for xi in x_it])
            rel_dev = np.abs(y_it - y_mod) / y_mod
            max_idx = rel_dev.argmax()
            if rel_dev[max_idx] < THRESH: break
            dropped.append((x_it[max_idx], y_it[max_idx], yerr_it[max_idx]))
            x_it, y_it, yerr_it = np.delete(x_it, max_idx), np.delete(y_it, max_idx), np.delete(yerr_it, max_idx)

        c = ROOT.TCanvas(f"c_{mx1_val:g}", "", 600, 600)
        frame = c.DrawFrame(0.0, 0.0, 1.1, np.max(y_vals)*1.4)
        frame.GetXaxis().SetTitle(x_label); frame.GetYaxis().SetTitle("#sigma [pb]")
        frame.SetTitle(f"mx1={mx1_val:g} TeV | {title_fix}")

        # Graphs & Functions
        gr_in = ROOT.TGraphErrors(len(x_it), x_it, y_it, np.zeros(len(x_it)), yerr_it)
        gr_in.SetMarkerStyle(20); gr_in.SetLineWidth(2)
        
        f_2d_proj = ROOT.TF1("f2d", f_temp_expr, 0.1, 1.0)
        f_2d_proj.SetLineColor(ROOT.kRed); f_2d_proj.SetLineStyle(2); f_2d_proj.Draw("SAME")

        f_slice_fit = ROOT.TF1("f_fit", f_temp_expr.replace(str(A_opt), "[0]"), 0.1, 1.0)
        f_slice_fit.SetParameter(0, A_opt)
        gr_in.Fit(f_slice_fit, "RQ")
        f_slice_fit.SetLineColor(ROOT.kBlue); f_slice_fit.Draw("SAME")
        gr_in.Draw("P SAME")

        if dropped:
            dr_x, dr_y, dr_e = zip(*dropped)
            gr_out = ROOT.TGraphErrors(len(dr_x), np.array(dr_x), np.array(dr_y), np.zeros(len(dr_x)), np.array(dr_e))
            gr_out.SetMarkerStyle(24); gr_out.SetMarkerColor(ROOT.kGray+1); gr_out.Draw("P SAME")

        c.SaveAs(os.path.join(out_dir, f"slice_mx1_{mx1_val:g}.png"))
        print(f"  -> Finished mx1={mx1_val:g}")

    except Exception as e:
        print(f"[SKIP] mx1={mx1_val:g} due to error: {e}")

print(f"\nAll plots saved in: {out_dir}")





