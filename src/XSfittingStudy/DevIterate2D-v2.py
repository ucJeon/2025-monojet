import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d import Axes3D  # noqa

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def model_2d(X, A, B=4.0):
    x1, x2 = X
    return A * (x1**2 * x2**2) / (B * x1**2 + x2**2)

def safe_float(s):
    if s is None: return np.nan
    dotted = str(s).replace("-", ".")
    cleaned = ".".join(dotted.split(".")[:2])
    try: return float(cleaned)
    except: return np.nan

def do_2d_fit(df_sub, B_FIXED):
    x1 = df_sub["lam1"].to_numpy(dtype=float)
    x2 = df_sub["lam2"].to_numpy(dtype=float)
    z  = df_sub["xsec [pb]"].to_numpy(dtype=float)
    ze = df_sub["xsec_err [pb]"].to_numpy(dtype=float)
    ze = np.where(ze <= 0, np.maximum(1e-12, 0.05 * np.abs(z)), ze)
    popt, pcov = curve_fit(
        lambda X, A: model_2d(X, A, B_FIXED),
        (x1, x2), z, p0=[z.max()],
        sigma=ze, absolute_sigma=True
    )
    return float(popt[0]), float(np.sqrt(np.diag(pcov))[0])

# -----------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------
csv_path = "/users/ujeon/2025-monojet/condor/23.XS-2Dplot/cross_sections.csv"
out_root = "IterFit_2D"
os.makedirs(out_root, exist_ok=True)

df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()
parts = df["sample"].str.split("_", expand=True)
df["mx1"]  = parts[1].apply(safe_float)
df["lam1"] = parts[2].apply(safe_float)
df["lam2"] = parts[3].apply(safe_float)

GRID_FULL = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
B_FIXED   = 4.0
THRESH    = 0.15   # 15%

# -----------------------------------------------------------------------
# Main loop per mx1
# -----------------------------------------------------------------------
for mx1_val, df_mx1_all in df.groupby("mx1"):

    out_dir = os.path.join(out_root, f"mx1_{mx1_val:g}")
    os.makedirs(out_dir, exist_ok=True)

    grid_l1      = GRID_FULL.copy()
    grid_l2      = GRID_FULL.copy()
    removed_l1   = []   # 누적 제거된 lam1 값
    removed_l2   = []   # 누적 제거된 lam2 값
    iteration    = 0

    print(f"\n{'='*60}")
    print(f"mx1 = {mx1_val:g} TeV")

    while True:
        # ---- 현재 그리드로 데이터 선택 & fit ----
        df_cur = df_mx1_all[
            df_mx1_all["lam1"].isin(grid_l1) &
            df_mx1_all["lam2"].isin(grid_l2)
        ].copy()

        if len(df_cur) < 3:
            print(f"  [iter {iteration}] 포인트 부족 ({len(df_cur)}), 중단")
            break

        try:
            A_opt, A_err = do_2d_fit(df_cur, B_FIXED)
        except RuntimeError as e:
            print(f"  [iter {iteration}] fit 실패: {e}, 중단")
            break

        x1_cur = df_cur["lam1"].to_numpy(dtype=float)
        x2_cur = df_cur["lam2"].to_numpy(dtype=float)
        z_cur  = df_cur["xsec [pb]"].to_numpy(dtype=float)
        pred   = model_2d((x1_cur, x2_cur), A_opt, B_FIXED)
        # reldev = np.abs(z_cur - pred) / pred
        reldev = np.abs(z_cur - pred) / z_cur

        max_idx  = reldev.argmax()
        max_dev  = reldev[max_idx]
        worst_l1 = x1_cur[max_idx]
        worst_l2 = x2_cur[max_idx]

        print(f"  iter {iteration:02d} | A={A_opt:.5g} ± {A_err:.3g} | "
              f"max dev={max_dev*100:.1f}%  "
              f"at (lam1={worst_l1:.2g}, lam2={worst_l2:.2g})")

        mask_out = reldev > THRESH
        mask_in  = ~mask_out

        # ================================================================
        # PNG: heatmap (left) + 2D surface (right)
        # ================================================================
        # heatmap 축은 항상 GRID_FULL 기준으로 고정
        l1u_full = np.array(GRID_FULL)
        l2u_full = np.array(GRID_FULL)

        # 현재 활성 포인트의 편차를 full grid 위에 매핑
        dev_mat = np.full((len(l2u_full), len(l1u_full)), np.nan)
        for xi, yi, di in zip(x1_cur, x2_cur, reldev * 100):
            ii = np.argmin(np.abs(l2u_full - yi))
            jj = np.argmin(np.abs(l1u_full - xi))
            dev_mat[ii, jj] = di

        fig = plt.figure(figsize=(16, 6), dpi=120)

        # ---- 왼쪽: Deviation Heatmap ----
        ax_hm = fig.add_subplot(1, 2, 1)

        # 배경: 활성 셀은 흰색/회색, 제거 셀은 나중에 hatch로 덮음
        bg = np.where(dev_mat > THRESH * 100, 0.82, 1.0)
        # nan (= 제거된 셀)은 일단 흰색으로
        bg_display = np.where(np.isnan(dev_mat), 1.0, bg)
        ax_hm.imshow(bg_display, origin="lower", cmap="gray",
                     vmin=0, vmax=1, aspect="auto")

        ax_hm.set_xticks(np.arange(len(l1u_full)))
        ax_hm.set_xticklabels([f"{v:g}" for v in l1u_full], fontsize=12)
        ax_hm.set_yticks(np.arange(len(l2u_full)))
        ax_hm.set_yticklabels([f"{v:g}" for v in l2u_full], fontsize=12)
        ax_hm.set_xlabel(r"$\lambda_1$")
        ax_hm.set_ylabel(r"$\lambda_2$")
        ax_hm.set_title(
            f"Deviation heatmap\n"
            f"mx1={mx1_val:g} TeV  |  iter {iteration}  |  "
            f"A={A_opt:.4g}  |  max dev={max_dev*100:.1f}%",
            fontsize=15
        )

        # 수치 표시 (활성 셀만)
        for ii in range(len(l2u_full)):
            for jj in range(len(l1u_full)):
                v = dev_mat[ii, jj]
                if np.isnan(v): continue   # 제거된 셀 → hatch만
                is_worst = (np.isclose(l1u_full[jj], worst_l1) and
                            np.isclose(l2u_full[ii], worst_l2))
                col    = "red"         if is_worst         else \
                         ("darkorange" if v > THRESH * 100 else "black")
                weight = "bold"        if v > THRESH * 100 else "normal"
                txt    = f"[{v:.1f}%]" if is_worst         else f"{v:.1f}%"
                ax_hm.text(jj, ii, txt, ha="center", va="center",
                           fontsize=11, color=col, weight=weight)

        # 최악 포인트 빨간 박스
        worst_jj = np.argmin(np.abs(l1u_full - worst_l1))
        worst_ii = np.argmin(np.abs(l2u_full - worst_l2))
        ax_hm.add_patch(mpatches.Rectangle(
            (worst_jj - 0.5, worst_ii - 0.5), 1, 1,
            fill=False, edgecolor="red", linewidth=2, zorder=4
        ))

        # 제거된 셀 → hatch (누적 removed_l1 × removed_l2 조합)
        # 제거된 lam1 행 전체 + 제거된 lam2 열 전체를 hatch
        for ii, lv2 in enumerate(l2u_full):
            for jj, lv1 in enumerate(l1u_full):
                is_removed = (
                    any(np.isclose(lv1, r) for r in removed_l1) or
                    any(np.isclose(lv2, r) for r in removed_l2)
                )
                if is_removed:
                    ax_hm.add_patch(mpatches.Rectangle(
                        (jj - 0.5, ii - 0.5), 1, 1,
                        fill=True, facecolor="lightgray",
                        edgecolor="dimgray", linewidth=0.5,
                        hatch="////", zorder=3
                    ))

        # ---- 오른쪽: 2D Surface ----
        ax3 = fig.add_subplot(1, 2, 2, projection="3d")

        ax3.scatter(x1_cur[mask_in], x2_cur[mask_in], z_cur[mask_in],
                    c="k", s=30, zorder=5, label="Inlier")
        if np.any(mask_out):
            ax3.scatter(x1_cur[mask_out], x2_cur[mask_out], z_cur[mask_out],
                        c="r", marker="x", s=80, linewidths=2,
                        zorder=6, label=f"Outlier (>{THRESH*100:.0f}%)")

        g1, g2 = np.meshgrid(np.linspace(min(grid_l1), max(grid_l1), 40),
                              np.linspace(min(grid_l2), max(grid_l2), 40))
        ax3.plot_surface(g1, g2, model_2d((g1, g2), A_opt, B_FIXED),
                         cmap="viridis", alpha=0.35, edgecolor="none")

        ax3.set_xlabel(r"$\lambda_1$", labelpad=8)
        ax3.set_ylabel(r"$\lambda_2$", labelpad=8)
        ax3.set_zlabel(r"$\sigma$ [pb]", labelpad=8)
        ax3.set_title(
            f"2D surface fit\n"
            f"mx1={mx1_val:g} TeV  |  iter {iteration}  |  A={A_opt:.4g}",
            fontsize=10
        )
        ax3.view_init(elev=25, azim=-135)
        ax3.legend(fontsize=12, loc="upper left")

        fig.tight_layout()
        fname = os.path.join(out_dir, f"iter{iteration:02d}_mx1_{mx1_val:g}.png")
        fig.savefig(fname, bbox_inches="tight")
        plt.close(fig)
        print(f"    -> saved {fname}")

        # ---- 종료 조건 ----
        if max_dev < THRESH:
            print(f"  max dev {max_dev*100:.1f}% < {THRESH*100:.0f}%  → 수렴, 종료")
            break

        # ---- 최악 포인트의 lam1, lam2를 그리드 & 누적 제거 목록에 반영 ----
        removed_l1.append(worst_l1)
        removed_l2.append(worst_l2)
        grid_l1 = [v for v in grid_l1 if not np.isclose(v, worst_l1)]
        grid_l2 = [v for v in grid_l2 if not np.isclose(v, worst_l2)]

        iteration += 1

    print(f"  최종 grid_l1 = {grid_l1}")
    print(f"  최종 grid_l2 = {grid_l2}")

print(f"\nDone. All outputs in: {out_root}/")
