#!/usr/bin/env python3
# plot_heatmaps_from_csv.py  (table-style heatmap)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def parse_list(arg: str):
    # "0.03,0.05,0.07" -> [0.03, 0.05, 0.07]
    if arg is None:
        return None
    return [float(x.strip()) for x in arg.split(",") if x.strip()]

def apply_constraints(df: pd.DataFrame,
                      lam1_list=None, lam1_range=None,
                      lam2_list=None, lam2_range=None) -> pd.DataFrame:
    out = df.copy()

    if lam1_list is not None:
        out = out[out["lam1"].isin(lam1_list)]
    if lam1_range is not None:
        lo, hi = lam1_range
        out = out[(out["lam1"] >= lo) & (out["lam1"] <= hi)]

    if lam2_list is not None:
        out = out[out["lam2"].isin(lam2_list)]
    if lam2_range is not None:
        lo, hi = lam2_range
        out = out[(out["lam2"] >= lo) & (out["lam2"] <= hi)]

    return out

def fmt_sig6(x: float) -> str:
    # 유효숫자 6자리
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return f"{x:.6g}"

def make_table_heatmaps(csv_path: str,
                        out_dir: str = "heatmaps",
                        value_col: str = "width",
                        lam1_list=None, lam1_range=None,
                        lam2_list=None, lam2_range=None,
                        show_color=False):
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)

    # 숫자형 캐스팅
    for c in ["mx1mass", "lam1", "lam2", "width", "width_err"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 제약 적용
    df = apply_constraints(df, lam1_list, lam1_range, lam2_list, lam2_range)

    # mx1mass마다 생성
    for mx1, sub in df.groupby("mx1mass"):
        if sub.empty:
            continue

        lam1_vals = np.sort(sub["lam1"].unique())
        lam2_vals = np.sort(sub["lam2"].unique())  # 작은 lam2가 아래로 가게 origin='lower'

        # 그리드 생성
        grid = np.full((len(lam2_vals), len(lam1_vals)), np.nan, dtype=float)
        lam1_to_j = {v: j for j, v in enumerate(lam1_vals)}
        lam2_to_i = {v: i for i, v in enumerate(lam2_vals)}

        for _, r in sub.iterrows():
            i = lam2_to_i[r["lam2"]]
            j = lam1_to_j[r["lam1"]]
            grid[i, j] = r[value_col]

        fig, ax = plt.subplots(figsize=(0.8 * max(6, len(lam1_vals)),
                                        0.6 * max(6, len(lam2_vals))))

        # 표 목적이면 색은 거의 의미 없음.
        # 그래도 셀 경계를 보기 위해 imshow를 쓰되,
        # 기본은 show_color=False로 컬러맵 영향 최소화.
        if show_color:
            im = ax.imshow(grid, origin="lower", aspect="auto")
        else:
            white = np.ones_like(grid, dtype=float)  # 전부 1
            im = ax.imshow(
                white,
                origin="lower",
                aspect="auto",
                cmap="gray",     # 0=검정, 1=흰색
                vmin=0.0,
                vmax=1.0
                )
        # 틱/라벨
        ax.set_title(f"Ratio [%] ({value_col})  mx1mass={mx1:g}")
        ax.set_xlabel("lam1 (columns)")
        ax.set_ylabel("lam2 (rows)")

        ax.set_xticks(np.arange(len(lam1_vals)))
        ax.set_xticklabels([f"{v:g}" for v in lam1_vals], rotation=90)

        ax.set_yticks(np.arange(len(lam2_vals)))
        ax.set_yticklabels([f"{v:g}" for v in lam2_vals])

        # 셀 경계선(표 느낌)
        ax.set_xticks(np.arange(-0.5, len(lam1_vals), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(lam2_vals), 1), minor=True)
        ax.grid(which="minor", linestyle="-", linewidth=0.6)
        ax.tick_params(which="minor", bottom=False, left=False)

        # 숫자 텍스트(유효숫자 6자리)
        for i in range(len(lam2_vals)):
            for j in range(len(lam1_vals)):
                txt = fmt_sig6(grid[i, j])
                txt_modi = float(txt)/(mx1*1000)*100 # GeV, %
                #print(txt_modi)
                ax.text(j, i, f"{txt_modi:.4f}", ha="center", va="center", fontsize=9)

        # 컬러바는 표 목적이면 기본 OFF
        # 필요하면 --show-color 켜서 같이 볼 수 있게만 해둠
        if show_color:
            fig.colorbar(im, ax=ax, label=value_col)

        plt.tight_layout()
        out_png = out_dir / f"table_{value_col}_mx1_{mx1:g}.png"
        plt.savefig(out_png, dpi=250)
        plt.close(fig)
        print(f"Saved: {out_png}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()

    p.add_argument("csv", help="input csv path")
    p.add_argument("--out", default="heatmaps", help="output directory")
    p.add_argument("--value", default="width", choices=["width", "width_err"],
                   help="which column to put in cells")

    # lam1 / lam2 constraints
    p.add_argument("--lam1", default=None,
                   help="comma-separated lam1 list, e.g. 0.03,0.05,0.07")
    p.add_argument("--lam1-range", nargs=2, type=float, default=None,
                   metavar=("LO", "HI"), help="lam1 range inclusive, e.g. --lam1-range 0.03 0.3")

    p.add_argument("--lam2", default=None,
                   help="comma-separated lam2 list, e.g. 0.04,0.06,0.08,0.1")
    p.add_argument("--lam2-range", nargs=2, type=float, default=None,
                   metavar=("LO", "HI"), help="lam2 range inclusive, e.g. --lam2-range 0.04 1.0")

    p.add_argument("--show-color", action="store_true",
                   help="also use color scale + colorbar (default: off, table-style)")

    args = p.parse_args()

    lam1_list = parse_list(args.lam1)
    lam2_list = parse_list(args.lam2)

    make_table_heatmaps(
        csv_path=args.csv,
        out_dir=args.out,
        value_col=args.value,
        lam1_list=lam1_list,
        lam1_range=args.lam1_range,
        lam2_list=lam2_list,
        lam2_range=args.lam2_range,
        show_color=args.show_color,
    )


