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
parser = argparse.ArgumentParser(description="2D-fit A, then draw ROOT slice plots")
parser.add_argument("--slice", type=str, required=True, choices=["lam1", "lam2"],
                    help="Which axis to fix: lam1 → scan lam2, lam2 → scan lam1")
parser.add_argument("--fix",   type=float, required=True,
                    help="Value of the fixed lambda")
args = parser.parse_args()

print(f"slice={args.slice}, fix={args.fix}")

# -----------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------
csv_path = "/users/ujeon/2025-monojet/condor/23.XS-2Dplot/cross_sections.csv"
out_dir  = f"{args.slice}-{args.fix}"
os.makedirs(out_dir, exist_ok=True)

# -----------------------------------------------------------------------
# Load & parse CSV
# -----------------------------------------------------------------------
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()
parts      = df["sample"].str.split("_", expand=True)
df["mx1"]  = parts[1].str.replace("-", ".", regex=False).astype(float)
df["lam1"] = parts[2].str.replace("-", ".", regex=False).astype(float)
df["lam2"] = (
    parts[3]
    .str.replace("-", ".", regex=False)
    .str.replace(r"\.0+$", "", regex=True)
    .astype(float)
)

# -----------------------------------------------------------------------
# Allowed grid for 2-D fit  (same as the 2-D script)
# -----------------------------------------------------------------------
# allowed_2d  = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
allowed_2d  = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
df_2d       = df[df["lam1"].isin(allowed_2d) & df["lam2"].isin(allowed_2d)].copy()

# Allowed grid for slice plots (original 1-D script)
XSpoint_list = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

B_FIXED = 4.0   # B is fixed to this value in the slice plot


# -----------------------------------------------------------------------
# 2-D model  (identical to the scipy script)
# -----------------------------------------------------------------------
def model_2d(X, A, B):
    x1, x2 = X
    return A * (x1**2 * x2**2) / (B * x1**2 + x2**2)


def select_close(s: pd.Series, val: float, atol: float = 1e-9) -> np.ndarray:
    return np.isclose(s.to_numpy(dtype=float), val, atol=atol, rtol=0)


# -----------------------------------------------------------------------
# Main loop: one plot per mx1 value
# -----------------------------------------------------------------------
for mx1_val, df_mx1_all in df.groupby("mx1"):

    # ---- Step 1: 2-D fit to obtain A_opt --------------------------------
    df_2d_mx1 = df_2d[np.isclose(df_2d["mx1"].to_numpy(dtype=float), mx1_val)]
    if df_2d_mx1.empty:
        print(f"[WARN] mx1={mx1_val:.1f}: no 2-D grid points, skipping")
        continue

    x1_2d   = df_2d_mx1["lam1"].to_numpy(dtype=float)
    x2_2d   = df_2d_mx1["lam2"].to_numpy(dtype=float)
    z_2d    = df_2d_mx1["xsec [pb]"].to_numpy(dtype=float)
    zerr_2d = df_2d_mx1["xsec_err [pb]"].to_numpy(dtype=float)
    zerr_2d = np.where(zerr_2d <= 0, np.maximum(1e-12, 0.05 * np.abs(z_2d)), zerr_2d)

    try:
        popt, pcov = curve_fit(
            lambda X, A, B: model_2d(X, A, B),
            (x1_2d, x2_2d),
            z_2d,
            p0=[z_2d.max(), 2.0],
            sigma=zerr_2d,
            absolute_sigma=True,
        )
        A_opt = float(popt[0])
        A_err = float(np.sqrt(np.diag(pcov))[0])
        B_2d  = float(popt[1])

        # chi2 of 2-D fit (for info only)
        z_pred_2d  = model_2d((x1_2d, x2_2d), A_opt, B_2d)
        res_2d     = (z_2d - z_pred_2d) / zerr_2d
        chi2_2d    = float(np.sum(res_2d**2))
        ndf_2d     = len(z_2d) - 2
        chi2ndf_2d = chi2_2d / ndf_2d if ndf_2d > 0 else float("nan")

        print(f"[mx1={mx1_val:.1f}] 2-D fit -> A={A_opt:.6g} ± {A_err:.3g}, "
              f"B={B_2d:.4g}  chi2/ndf={chi2ndf_2d:.3g}")

        # ---- 2D surface plot (matplotlib) -------------------------------
        g1 = np.linspace(x1_2d.min(), x1_2d.max(), 50)
        g2 = np.linspace(x2_2d.min(), x2_2d.max(), 50)
        G1, G2 = np.meshgrid(g1, g2)
        Z_fit = model_2d((G1, G2), A_opt, B_2d)

        fig = plt.figure(figsize=(8, 6), dpi=150)
        ax  = fig.add_subplot(111, projection="3d")
        ax.scatter(x1_2d, x2_2d, z_2d, c="k", s=25, label="data points")
        ax.plot_surface(G1, G2, Z_fit, cmap="viridis",
                        edgecolor="none", alpha=0.7)
        zmax = max(z_2d.max(), Z_fit.max()) * 1.1
        ax.set_zlim(0, zmax)
        ax.set_xlabel(r"$\lambda_1$", labelpad=10, fontsize=12)
        ax.set_ylabel(r"$\lambda_2$", labelpad=10, fontsize=12)
        ax.set_zlabel(r"$\sigma\;[{\rm pb}]$", labelpad=8, fontsize=12)
        ax.set_title(
            f"mx1 = {mx1_val:.1f}\n"
            f"Fit A = {A_opt:.3f} ± {A_err:.2e},  B = {B_2d:.3f}\n"
            f"chi2/ndf = {chi2ndf_2d:.3f}",
            fontsize=13,
        )
        proxy_data = Line2D([0], [0], marker="o", color="k", linestyle="")
        proxy_surf = Line2D([0], [0], linestyle="none", marker="s",
                            markersize=10,
                            markerfacecolor=plt.cm.viridis(0.5), alpha=0.7)
        ax.legend([proxy_data, proxy_surf],
                  ["data points", "fit surface"], loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.4)

        fname_2d  = f"mx1_{mx1_val:.1f}_2Dfit_surface.png"
        path_2d   = os.path.join(out_dir, fname_2d)
        fig.savefig(path_2d, bbox_inches="tight")
        plt.close(fig)
        print(f"  -> 2D surface saved: {path_2d}")

    except RuntimeError as e:
        print(f"[WARN] mx1={mx1_val:.1f}: 2-D fit failed ({e}), skipping")
        continue

    # ---- Step 2: slice plot using A_opt + B_FIXED -----------------------
    fixed_lam = float(args.fix)

    if args.slice == "lam2":
        # fix lam2, scan lam1
        grp = df_mx1_all[select_close(df_mx1_all["lam2"], fixed_lam)]
        if grp.empty:
            print(f"[WARN] mx1={mx1_val:.1f}: no points at lam2={fixed_lam}")
            continue
        grp = grp[grp["lam1"].isin(XSpoint_list)]
        if grp.empty:
            continue

        x    = grp["lam1"].to_numpy(dtype=float)
        y    = grp["xsec [pb]"].to_numpy(dtype=float)
        yerr = grp["xsec_err [pb]"].to_numpy(dtype=float)

        x_label   = "#lambda_{1}"
        title_fix = f"fixed #lambda_{{2}} = {fixed_lam:.2f}"

        lam   = fixed_lam
        # model: A * (lam1^2 * lam2_fixed^2) / (B*lam1^2 + lam2_fixed^2)
        fexpr = (f"{A_opt}*((x*x)*({lam}*{lam})) "
                 f"/ ({B_FIXED}*(x*x) + ({lam}*{lam}))")

    else:
        # fix lam1, scan lam2
        grp = df_mx1_all[select_close(df_mx1_all["lam1"], fixed_lam)]
        if grp.empty:
            print(f"[WARN] mx1={mx1_val:.1f}: no points at lam1={fixed_lam}")
            continue
        grp = grp[grp["lam2"].isin(XSpoint_list)]
        if grp.empty:
            continue

        x    = grp["lam2"].to_numpy(dtype=float)
        y    = grp["xsec [pb]"].to_numpy(dtype=float)
        yerr = grp["xsec_err [pb]"].to_numpy(dtype=float)

        x_label   = "#lambda_{2}"
        title_fix = f"fixed #lambda_{{1}} = {fixed_lam:.2f}"

        lam   = fixed_lam
        # model: A * (lam1_fixed^2 * lam2^2) / (B*lam1_fixed^2 + lam2^2)
        fexpr = (f"{A_opt}*(({lam}*{lam})*(x*x)) "
                 f"/ ({B_FIXED}*({lam}*{lam}) + (x*x))")

    # yerr safety
    yerr = np.where(yerr <= 0, np.maximum(1e-12, 0.05 * np.abs(y)), yerr)

    order = np.argsort(x)
    x, y, yerr = x[order], y[order], yerr[order]

    n = len(x)
    if n < 2:
        print(f"[WARN] mx1={mx1_val:.1f}: too few slice points (n={n}), skipping")
        continue

    # ---- ROOT canvas ----------------------------------------------------
    c = ROOT.TCanvas(f"c_mx1_{mx1_val:.1f}", "", 900, 700)

    xmin_r, xmax_r = float(np.min(x)), float(np.max(x))
    xr = 0.05 * (xmax_r - xmin_r) if xmax_r > xmin_r else 0.1
    xmin_r -= xr
    xmax_r += xr

    ymax_r = float(np.max(y + yerr))
    frame  = c.DrawFrame(xmin_r, 0.0, xmax_r, ymax_r * 1.40)
    frame.GetXaxis().SetTitle(x_label)
    frame.GetYaxis().SetTitle("#sigma [pb]")
    frame.SetTitle(f"mx1 = {mx1_val:.1f}  |  {title_fix}")

    # TGraphErrors
    gr = ROOT.TGraphErrors(n)
    gr.SetName(f"gr_mx1_{mx1_val:.1f}")
    for i in range(n):
        gr.SetPoint(i, float(x[i]), float(y[i]))
        gr.SetPointError(i, 0.0, float(yerr[i]))
    gr.SetMarkerStyle(20)
    gr.SetMarkerSize(1.2)
    gr.SetLineWidth(3)

    # TF1 — A is already embedded as a constant; NO free parameters
    # We evaluate chi2 manually for display
    f = ROOT.TF1(f"f_mx1_{mx1_val:.1f}", fexpr,
                 float(np.min(x)), float(np.max(x)))
    f.SetLineWidth(4)
    f.SetLineColor(ROOT.kRed)

    # Manual chi2 calculation (no fit, A is fixed from 2-D fit)
    y_model   = np.array([f.Eval(float(xi)) for xi in x])
    residuals = (y - y_model) / yerr
    chi2_1d   = float(np.sum(residuals**2))
    ndf_1d    = n                    # 0 free parameters → ndf = n
    chi2ndf_1d = chi2_1d / ndf_1d if ndf_1d > 0 else float("nan")

    print(f"  slice chi2/ndf = {chi2_1d:.4g}/{ndf_1d} = {chi2ndf_1d:.4g}  "
          f"(A={A_opt:.4g} fixed from 2-D fit, B={B_FIXED})")

    gr.Draw("P SAME")
    f.Draw("L SAME")

    # Legend
    leg = ROOT.TLegend(0.52, 0.65, 0.93, 0.90)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.SetTextFont(42)
    leg.SetTextSize(0.030)

    leg.AddEntry(gr, "cross-section (XS)", "pe")

    line1 = f"A={A_opt:.3g} (from 2D fit), B={B_FIXED:g} (fixed)"
    line2 = f"#chi^{{2}}/ndf = {chi2_1d:.2f}/{ndf_1d:d} = {chi2ndf_1d:.2f}"
    leg.AddEntry(f, f"#splitline{{curve: {line1}}}{{{line2}}}", "l")
    leg.Draw()

    outpath = os.path.join(out_dir,
                           f"mx1_{mx1_val:.1f}_{args.slice}_fix{args.fix:.2f}.png")
    c.SaveAs(outpath)
    c.Close()
    print(f"  -> saved {outpath}")



