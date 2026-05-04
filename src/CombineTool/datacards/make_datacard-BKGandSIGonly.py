#!/usr/bin/env python3
"""
make_datacard_syst.py
---------------------
Incremental systematic uncertainty study용 datacard 생성

모드:
  none  : uncertainty 없음 (observation only)
  stats : bkg MC stat only
  sys1  : stats + xsec_sig (15%)
  sys2  : stats + xsec_sig + btag_eff (6%)
  sys3  : stats + xsec_sig + btag_eff + jes (5%)
  sys4  : stats + xsec_sig + btag_eff + jes + met_model (4%)

Usage:
  python3 make_datacard_syst.py
"""

import pandas as pd
import os

# ============================================================
# Systematic uncertainty 정의
# (이름, sig lnN값, bkg lnN값)
# '-' = 해당 프로세스에 영향 없음
# ============================================================

SYST_STEPS = [
    # sys1
    ("xsec_sig",   "1.10", "-"),
    # sys2
    # ("btag_eff",   "1.06", "1.06"),
    # sys3
    ("jes",        "1.05", "1.05"),
    # sys4
    ("met_model",  "1.04", "1.04"),
]
'''
SYST_STEPS = [
    ("met_model",  "1.04", "1.04"),
    ("met_model",  "1.04", "1.04"),
    # ("jes",        "1.05", "1.05"),
    ("xsec_sig",   "1.10", "-"),
]
'''

# 모드 정의: 각 모드에서 포함할 SYST_STEPS의 수
'''
MODES = {
    "none":  None,        # stats도 없음
    "stats": 0,           # stat_bkg만
    "sys1":  1,           # stat_bkg + xsec_sig
    "sys2":  2,           # stat_bkg + xsec_sig + btag_eff
    "sys3":  3,           # stat_bkg + xsec_sig + btag_eff + jes
    "sys4":  4,           # stat_bkg + xsec_sig + btag_eff + jes + met_model
}
'''
MODES = {
    "none":  None,        # stats도 없음
    "stats": 0,           # stat_bkg만
    "sys1":  1,           # stat_bkg + xsec_sig
    "sys2":  2,           # stat_bkg + xsec_sig + jes
    "sys3":  3,           # stat_bkg + xsec_sig + jes + met_model
}
# ============================================================

def generate_datacard(version, ntrees, maxdepth, bdt_cut, lumi, mx1,
                      unc_mode="stats", out_dir="."):

    # 1. 경로 설정
    cut_str    = f"{abs(bdt_cut):.4f}".replace('.', 'p')
    prefix     = "m" if bdt_cut < 0 else ""
    folder_name = f"{version}_{ntrees}_{maxdepth}_{prefix}{cut_str}"
    base_path  = (f"/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/"
                  f"BDT_cut/out/{folder_name}")

    mx1_dash   = mx1.replace('.', '-')
    bkg_path   = os.path.join(base_path, f"bkg_lumi{lumi}_mx1{mx1_dash}.csv")
    sig_path   = os.path.join(base_path, f"sig_lumi{lumi}_mx1{mx1_dash}.csv")

    print(f"[INFO] BKG: {bkg_path}")
    print(f"[INFO] SIG: {sig_path}")

    output_file = os.path.join(
        out_dir,
        f"datacard_lumi{lumi}_mx1{mx1_dash}_cut{cut_str}_{unc_mode}.txt"
    )

    # 2. Background (TOTAL row) 추출
    df_bkg   = pd.read_csv(bkg_path)
    df_total = df_bkg[df_bkg['sample'] == 'TOTAL'].iloc[0]
    bkg_rate     = float(df_total['b0'])
    bkg_stat_err = float(df_total['sigmab0'])

    # 3. Signal (lam1=0.1, lam2=0.1 기준점) 추출
    df_sig = pd.read_csv(sig_path)
    try:
        target_sig = df_sig[df_sig['signal'].str.contains("_0-1_0-1.0")].iloc[0]
    except (IndexError, KeyError):
        print(f"[WARN] lam=0.1 기준점 미발견 → 첫 번째 행 사용")
        target_sig = df_sig.iloc[0]

    sig_rate = float(target_sig['sg after'])

    # 4. observation (Asimov: bkg_rate 반올림)
    observations = int(round(bkg_rate))
    col_w = 20

    # ============================================================
    # 5. kmax 계산
    # ============================================================
    n_syst = MODES[unc_mode]  # None or int

    if n_syst is None:
        # "none": stat도 syst도 없음 → kmax=0
        kmax = 0
    else:
        # stat_bkg(1) + n_syst개
        kmax = 1 + n_syst

    # ============================================================
    # 6. Datacard 작성
    # ============================================================
    card = [
        "imax 1  number of channels",
        "jmax 1  number of backgrounds",
        f"kmax {'*' if kmax > 0 else 0}",
        "-" * 70,
        "bin         bin1",
        "-" * 70,
        "bin".ljust(25)     + "bin1".ljust(col_w) + "bin1".ljust(col_w),
        "process".ljust(25) + "sig".ljust(col_w)  + "bkg".ljust(col_w),
        "process".ljust(25) + "0".ljust(col_w)    + "1".ljust(col_w),
        "rate".ljust(25)    + f"{sig_rate:<{col_w}.4f}" + f"{bkg_rate:<{col_w}.4f}",
        "-" * 70,
    ]

    # ---- stat_bkg ----
    if n_syst is not None:   # stats 이상이면 stat_bkg 추가
        if bkg_rate > 0:
            b_unc = 1.0 + bkg_stat_err / bkg_rate
            card.append(
                f"stat_bkg".ljust(16) +
                f"lnN".ljust(8) +
                f"{'-':<{col_w}}" +
                f"{b_unc:.4f}"
            )
        else:
            card.append(f"stat_bkg".ljust(16) + "lnN".ljust(8) +
                        f"{'-':<{col_w}}" + "1.0000")

    # ---- incremental systematics ----
    if n_syst is not None and n_syst > 0:
        for name, sig_val, bkg_val in SYST_STEPS[:n_syst]:
            card.append(
                f"{name}".ljust(16) +
                f"lnN".ljust(8) +
                f"{sig_val:<{col_w}}" +
                f"{bkg_val}"
            )

    # 7. 저장
    os.makedirs(out_dir, exist_ok=True)
    with open(output_file, "w") as f:
        f.write("\n".join(card) + "\n")

    print(f"[DONE] {output_file}  "
          f"| Sig={sig_rate:.2f}  Bkg={bkg_rate:.2f}  "
          f"stat_rel={bkg_stat_err/bkg_rate:.4f}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    configs = [
        {"mx1": "1-0", "cut": 0.1050},
        {"mx1": "1-5", "cut": 0.1350},
        {"mx1": "2-0", "cut": 0.1440},
        {"mx1": "2-5", "cut": 0.1520},
    ]

    for lumi in [300, 3000]:
        for conf in configs:
            for mode in MODES:
                print(f"\n=== lumi={lumi}  mx1={conf['mx1']}  mode={mode} ===")
                generate_datacard(
                    version="v2", ntrees=2500, maxdepth=4,
                    bdt_cut=conf["cut"],
                    lumi=lumi,
                    mx1=conf["mx1"],
                    unc_mode=mode,
                    out_dir="datacards",
                )
