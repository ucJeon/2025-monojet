"""
parse_results-xsfit.py

outputs-xsfit/ 의 ROOT 파일에서 r_up (모든 quantile) 을 읽고
N_exc = r_quantile × rate_sig_ref 를 계산해 results-xsfit.csv 로 저장.

rate_sig_ref = xs_ref(lam1=0.1, lam2=0.1) × lumi × 1000 × eff_gb_ref
"""

import os
import ROOT
import pandas as pd

ROOT.gROOT.SetBatch(True)

SRC       = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src"
PATH_XS   = f"{SRC}/23.XS-2Dplot/cross_section_SG.csv"
PATH_EFF  = f"{SRC}/Efficiency-signal/efficiency.csv"
OUTDIR    = os.path.join(os.path.dirname(__file__), "outputs-xsfit")

OPTIMAL_CUTS = {1.0: 0.105, 1.5: 0.135, 2.0: 0.144, 2.5: 0.152}
MODEL        = "v2_2500_4"
LAM_REF      = 0.1   # 기준점 lam1 = lam2 = 0.1

MX_TAG  = {1.0: ("MX10", 1000), 1.5: ("MX15", 1500),
           2.0: ("MX20", 2000), 2.5: ("MX25", 2500)}
QUANTILE_NAMES = {
    0.025: "exp_m2s",
    0.160: "exp_m1s",
    0.500: "exp_med",
    0.840: "exp_p1s",
    0.975: "exp_p2s",
}

def load_refs():
    df_xs  = pd.read_csv(PATH_XS).set_index(["mx1", "lam1", "lam2"])
    df_eff = pd.read_csv(PATH_EFF).set_index(["mx1", "lam1", "lam2", "model", "bdt_cut"])
    refs = {}
    for mx1, cut in OPTIMAL_CUTS.items():
        xs_ref  = df_xs.loc[(mx1, LAM_REF, LAM_REF), "xs"]
        eff_ref = df_eff.loc[(mx1, LAM_REF, LAM_REF, MODEL, cut), "eff_gb"]
        refs[mx1] = {"xs_ref": xs_ref, "eff_ref": eff_ref, "cut": cut}
    return refs

def read_root(path):
    f = ROOT.TFile(path)
    t = f.Get("limit")
    result = {}
    for entry in t:
        q = round(float(t.quantileExpected), 3)
        result[q] = float(t.limit)
    f.Close()
    return result

def main():
    refs   = load_refs()
    modes  = ["none", "stats", "sys1", "sys2", "sys3"]
    lumis  = [300, 3000]
    records = []

    for lumi in lumis:
        for mode in modes:
            for mx1, (mx_tag, mh) in MX_TAG.items():
                fname = f"/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/CombineTool/outputs-xsfit/higgsCombine.Lumi{lumi}.{mx_tag}.{mode}.xsfit.AsymptoticLimits.mH{mh}.root"
                fpath = os.path.join(OUTDIR, fname)
                if not os.path.exists(fpath):
                    print(f"[SKIP] {fname}")
                    continue

                r_vals = read_root(fpath)
                ref    = refs[mx1]
                rate_sig_ref = ref["xs_ref"] * lumi * 1000 * ref["eff_ref"]

                row = {
                    "mx1":           mx1,
                    "lumi":          lumi,
                    "mode":          mode,
                    "xs_ref":        ref["xs_ref"],
                    "eff_ref":       ref["eff_ref"],
                    "rate_sig_ref":  rate_sig_ref,
                }
                for q, name in QUANTILE_NAMES.items():
                    r = r_vals.get(q, float("nan"))
                    row[f"r_{name}"]     = r
                    row[f"N_exc_{name}"] = r * rate_sig_ref

                records.append(row)
                print(f"  mx1={mx1} lumi={lumi} mode={mode}: "
                      f"r_med={row['r_exp_med']:.4f}  "
                      f"N_exc={row['N_exc_exp_med']:.2f}")

    df = pd.DataFrame(records)
    out = os.path.join(os.path.dirname(__file__), "results-xsfit.csv")
    df.to_csv(out, index=False, float_format="%.6g")
    print(f"\nSaved: {out}  ({len(df)} rows)")

if __name__ == "__main__":
    main()
