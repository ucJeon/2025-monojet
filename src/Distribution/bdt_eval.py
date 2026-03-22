"""
bdt_eval.py
-----------
TMVA BDT evaluation 유틸리티.
  - load_bdt_reader       : XML weights 로드, TMVA Reader 생성
  - fill_histogram        : ROOT 파일 하나 → TH1F
  - fill_bkg_histograms   : process별 여러 파일 → TH1F dict
  - scan_significance     : BDT cut scan → DataFrame + CSV
  - yield_at_cut          : 특정 cut에서 sample별 yield 출력
"""

import ROOT
from array import array
from pathlib import Path


# ══════════════════════════════════════════════════════════
# 학습에 사용한 변수 목록 (flag별)
# ══════════════════════════════════════════════════════════

VAR_DEFS = {
    "var5": [
        "ubDeltaR", "u1PT", "b1PT", "ubDeltaPhi", "METPt",
    ],
    "var6": [
        "ubDeltaR", "u1PT", "b1PT", "ubDeltaPhi", "METPt", "METuDeltaPhi",
    ],
    "PEP": [
        "u1PT", "b1PT", "METPt", "u1Eta", "b1Eta", "u1Phi", "b1Phi", "METPhi",
    ],
    "v1": [
        "u1PT", "b1PT", "METPt", "u1Eta", "b1Eta",
        "ubDeltaR", "ubDeltaPhi", "bMETDeltaPhi", "METuDeltaPhi",
        "ubDeltaMt", "bMETDeltaMt", "METuDeltaMt",
    ],
    "v2": [
        "u1PT", "b1PT", "METPt", "u1Eta", "b1Eta",
        "ubDeltaR", "ubDeltaPhi", "bMETDeltaPhi", "METuDeltaPhi",
        "METuDeltaMt",
    ],
    "v4": [
        "u1PT", "b1PT", "METPt", "u1Eta", "b1Eta",
        "ubDeltaR", "ubDeltaPhi", "bMETDeltaPhi", "METuDeltaPhi",
        "METuDeltaMt", "u1_Efrac", "b1_Efrac",
    ],
}

# 같은 변수셋을 쓰는 flag들을 묶어서 관리
FLAG_VARKEY = {
    "var5"                    : "var5",
    "AMD"                     : "var5",
    "var6"                    : "var6",
    "PEP"                     : "PEP",
    "v1"                      : "v1",
    "v2"                      : "v2",
    "v2-modiTauVeto-more1jets": "v2",
    "v2-modiTauVeto-only1jets": "v2",
    "v3"                      : "v2",
    "v32"                     : "v2",
    "v3f0p8"                  : "v2",
    "v3f0p5"                  : "v2",
    "v3f0p5SPLIT"             : "v2",
    "v4"                      : "v4",
}


# ══════════════════════════════════════════════════════════
# 1. TMVA Reader 생성
# ══════════════════════════════════════════════════════════

def load_bdt_reader(xml_file: str, flag: str):
    """
    TMVA Reader를 생성하고 BDT weights를 로드한다.

    Returns
    -------
    reader    : ROOT.TMVA.Reader
    var_bufs  : dict  {변수명 -> std::vector<float>(1)}
    var_names : list  [변수명, ...]   (학습 순서와 동일)
    """
    var_key = FLAG_VARKEY.get(flag)
    if var_key is None:
        raise ValueError(f"알 수 없는 flag: '{flag}'\n사용 가능: {list(FLAG_VARKEY)}")

    var_names = VAR_DEFS[var_key]

    reader   = ROOT.TMVA.Reader("!Color:!Silent")
    var_bufs = {}
    for vname in var_names:
        buf = ROOT.std.vector("float")(1)
        var_bufs[vname] = buf
        reader.AddVariable(vname, buf.data())

    reader.BookMVA("BDT", xml_file)
    return reader, var_bufs, var_names


# ══════════════════════════════════════════════════════════
# 2. ROOT 파일 하나 → TH1F
# ══════════════════════════════════════════════════════════

def fill_histogram(reader, var_bufs, var_names,
                   root_file     : str,
                   weight_branch : str   = "weight",
                   tree_name     : str   = "events",
                   n_bins        : int   = 1000,
                   hist_name     : str   = "h_bdt",
                   hist_title    : str   = "BDT response"):
    """
    ROOT 파일을 열고 모든 이벤트에 대해 BDT score를 계산해서
    가중치를 적용한 TH1F를 반환한다.
    """
    f = ROOT.TFile.Open(root_file)
    if not f or f.IsZombie():
        raise FileNotFoundError(f"파일을 열 수 없음: {root_file}")

    tree = f.Get(tree_name)
    if not tree:
        f.Close()
        raise RuntimeError(f"TTree '{tree_name}' 없음: {root_file}")

    # branch address 연결
    bufs = {}
    for vname in var_names:
        buf = ROOT.std.vector("float")(1)
        bufs[vname]      = buf
        var_bufs[vname]  = buf          # reader와 동기화
        tree.SetBranchAddress(vname, buf.data())

    w_buf = ROOT.std.vector("double")(1)
    tree.SetBranchAddress(weight_branch, w_buf.data())

    h = ROOT.TH1F(hist_name, hist_title, n_bins, -1, 1)
    h.SetDirectory(0)   # 파일 닫아도 히스토그램 유지
    h.Sumw2()

    import math
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        # NaN 이벤트 디버그 출력
        for v in var_names:
            if math.isnan(bufs[v][0]):
                print(f"  [DBG] NaN  file={root_file.split('/')[-1]}  entry={i}  var={v}")
        h.Fill(reader.EvaluateMVA("BDT"), w_buf[0])

    f.Close()
    return h


# ══════════════════════════════════════════════════════════
# 3. Background process별 히스토그램 채우기
# ══════════════════════════════════════════════════════════

def fill_bkg_histograms(reader, var_bufs, var_names,
                        bkg_process   : dict,
                        data_dir      : str,
                        weight_branch : str = "weight",
                        n_bins        : int = 1000):
    """
    process별로 여러 ROOT 파일을 합산해서 히스토그램 하나씩 만든다.

    Parameters
    ----------
    bkg_process : dict  {process명 -> [파일명, ...]}
                  e.g. {"ttbar": ["ttbar.1.root", "ttbar.2.root", ...]}
    data_dir    : ROOT 파일들이 있는 디렉터리 경로

    Returns
    -------
    hists : dict  {process명 -> ROOT.TH1F}
    """
    data_dir = Path(data_dir)
    hists    = {}

    for proc, fnames in bkg_process.items():
        h_total = ROOT.TH1F(f"h_{proc}", f"BDT response — {proc}", n_bins, -1, 1)
        h_total.SetDirectory(0)
        h_total.Sumw2()

        for fname in fnames:
            fpath = data_dir / fname
            if not fpath.exists():
                print(f"  [WARN] 없음: {fpath.name} — skip")
                continue
            h_tmp = fill_histogram(
                reader, var_bufs, var_names,
                root_file     = str(fpath),
                weight_branch = weight_branch,
                n_bins        = n_bins,
                hist_name     = f"h_tmp_{proc}_{fname}",
            )
            h_total.Add(h_tmp)

        # yield 출력
        err_arr = array("d", [0.0])
        y = h_total.IntegralAndError(1, h_total.GetNbinsX(), err_arr)
        print(f"  {proc:<12}  yield = {y:.2f} ± {err_arr[0]:.2f}")

        hists[proc] = h_total

    return hists


# ══════════════════════════════════════════════════════════
# 4. 특정 cut에서 sample별 yield 출력
# ══════════════════════════════════════════════════════════

def yield_at_cut(hists: dict, bdt_cut: float):
    """bdt_cut 이상의 yield를 sample별로 출력."""
    print(f"\n{'Sample':<30} {'Yield':>12} {'±Err':>10}")
    print("-" * 54)
    for label, h in hists.items():
        first_bin = h.FindBin(bdt_cut)
        err_arr   = array("d", [0.0])
        y = h.IntegralAndError(first_bin, h.GetNbinsX(), err_arr)
        print(f"  {label:<28} {y:>12.4f} {err_arr[0]:>10.4f}")
    print()
