import pandas as pd
import numpy  as np
import os
import re

PATH_CUTFLOW      = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/outputs/cutflowcsv/v2"
PATH_BDTOUT       = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_cut/out"
PATH_POSTPROC_V2  = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/v2"

def list_indices(signal_name, path=PATH_CUTFLOW):
    pattern = re.compile(
        rf'^cutflow_{re.escape(signal_name)}\.0\.(\d+)_v2\.csv$'
    )
    indices = []
    for fname in os.listdir(path):
        match = pattern.match(fname)
        if match:
            indices.append(int(match.group(1)))
    return sorted(indices)

def _parse_cut_tag(tag):
    """'0p1050' -> 0.1050, 'm1p0000' -> -1.0"""
    if tag.startswith('m'):
        return -float(tag[1:].replace('p', '.'))
    return float(tag.replace('p', '.'))


def _hyphen_to_float(s):
    """'1-0' -> 1.0, '0-03' -> 0.03"""
    return float(s.replace('-', '.'))


def _parse_signal_name(name):
    """'Signal_1-0_0-03_0-04.0' -> (mx1=1.0, lam1=0.03, lam2=0.04)"""
    name = re.sub(r'\.0$', '', name)       # strip trailing .0 job indicator
    parts = name[len('Signal_'):].split('_')
    return _hyphen_to_float(parts[0]), _hyphen_to_float(parts[1]), _hyphen_to_float(parts[2])


def _float_to_hyphen(f):
    """1.0 -> '1-0', 1.5 -> '1-5'"""
    return f"{f:.1f}".replace('.', '-')


def _parse_model_tag(model_tag):
    """'v2_2500_4' -> (version='v2', ntree='2500', depth='4')"""
    parts = model_tag.split('_')
    return parts[0], parts[1], parts[2]


def read_eval_ngen_nsel(model_tag, postproc_root=PATH_POSTPROC_V2):
    """
    data_eval_MX1{mx1}_nTree{ntree}_maxDepth{depth}_{version} ROOT 파일에서
    N_gen(Ngen 브랜치)과 N_sel_1(tree entries)을 읽어 DataFrame으로 반환.
    """
    import ROOT
    ROOT.gROOT.SetBatch(True)

    version, ntree, depth = _parse_model_tag(model_tag)
    records = []

    for mx1_float in [1.0, 1.5, 2.0, 2.5]:
        mx1_tag  = _float_to_hyphen(mx1_float)
        dir_name = f"data_eval_MX1{mx1_tag}_nTree{ntree}_maxDepth{depth}_{version}"
        dir_path = os.path.join(postproc_root, dir_name)
        if not os.path.isdir(dir_path):
            continue

        for fname in sorted(os.listdir(dir_path)):
            if not fname.endswith('.root'):
                continue
            match = re.match(
                r'^sel_(Signal_[0-9\-]+_[0-9\-]+_[0-9\-]+)\.0_v\d+\.root$',
                fname
            )
            if match is None:
                continue
            signal_name = match.group(1)
            mx1, lam1, lam2 = _parse_signal_name(signal_name)
            if lam1 == 2.0 or lam2 == 2.0:
                continue

            fpath = os.path.join(dir_path, fname)
            try:
                f = ROOT.TFile(fpath)
                t = f.Get('events')
                if not t:
                    f.Close()
                    continue
                n_sel_1 = int(t.GetEntries())
                t.GetEntry(0)
                n_gen = int(t.Ngen)
                f.Close()
                records.append({
                    'mx1':     mx1,
                    'lam1':    lam1,
                    'lam2':    lam2,
                    'N_gen':   n_gen,
                    'N_sel_1': n_sel_1,
                })
            except Exception:
                pass

    return pd.DataFrame(records)


def build_efficiency_df(model_tag=None):
    """
    BDT_cut/out 폴더를 순회하며
    (mx1, lam1, lam2, model, bdt_cut, N_gen, N_sel_1, N_sel_2, N_bdt, ..., N_sel_check)
    DataFrame을 반환한다.

    N_gen, N_sel_1 : data_eval ROOT 파일에서 읽음 (BDT inference용 eval 세트)
    N_sel_2        : BDT cut sig CSV 의 'count before'
    N_bdt          : BDT cut sig CSV 의 'count after'
    N_sel_check    : N_sel_1 / N_sel_2 (일치 확인용)

    Parameters
    ----------
    model_tag : str or None
        'v2_2500_4' 등 특정 모델만 필터링. None 이면 전체 수집.
    """
    # --- step 1: BDT cut sig CSV 수집 ---
    records = []

    for folder in sorted(os.listdir(PATH_BDTOUT)):
        if folder == 'FINAL':
            continue
        folder_path = os.path.join(PATH_BDTOUT, folder)
        if not os.path.isdir(folder_path):
            continue

        idx = folder.rfind('_')
        if idx == -1:
            continue
        mtag, cut_tag = folder[:idx], folder[idx + 1:]

        if folder.split('_')[0] != 'v2':
            continue

        if model_tag is not None and mtag != model_tag:
            continue

        if not re.fullmatch(r'm?[0-9]+p[0-9]+', cut_tag):
            continue
        bdt_cut = round(_parse_cut_tag(cut_tag), 4)

        for fname in sorted(os.listdir(folder_path)):
            if not (fname.startswith('sig_lumi300_mx1') and fname.endswith('.csv')):
                continue

            df_sig = pd.read_csv(os.path.join(folder_path, fname))

            for _, row in df_sig.iterrows():
                mx1, lam1, lam2 = _parse_signal_name(str(row['signal']))
                if lam1 == 2.0 or lam2 == 2.0:
                    continue
                records.append({
                    'mx1':     mx1,
                    'lam1':    lam1,
                    'lam2':    lam2,
                    'model':   mtag,
                    'bdt_cut': bdt_cut,
                    'N_sel_2': int(row['count before']),
                    'N_bdt':   int(row['count after']),
                })

    df = pd.DataFrame(records)
    _empty_cols = ['mx1', 'lam1', 'lam2', 'model', 'bdt_cut',
                   'N_gen', 'N_sel_1', 'N_sel_2', 'N_bdt',
                   'eff_gs', 'eff_sb', 'eff_gb', 'N_sel_check']
    if df.empty:
        return pd.DataFrame(columns=_empty_cols)

    # --- step 2: eval ROOT 파일에서 N_gen, N_sel_1 읽어 merge ---
    eval_parts = []
    for mtag_iter in df['model'].unique():
        eval_parts.append(read_eval_ngen_nsel(mtag_iter))
    df_eval = pd.concat(eval_parts, ignore_index=True).drop_duplicates(
        subset=['mx1', 'lam1', 'lam2']
    )

    df = df.merge(df_eval, on=['mx1', 'lam1', 'lam2'], how='left')

    # --- step 3: 효율 및 비율 계산 ---
    df['eff_gs']      = df['N_sel_1'] / df['N_gen']
    df['eff_sb']      = df['N_bdt']   / df['N_sel_1']
    df['eff_gb']      = df['N_bdt']   / df['N_gen']
    df['N_sel_check'] = df['N_sel_1'] / df['N_sel_2']

    return df[_empty_cols]

# def write_selectionInfo(df_bdt):
def rewrite_selectionInfo():
    records = []
    # 모든 cutflow csv 순회
    for fname in sorted(os.listdir(PATH_CUTFLOW)):
        if not (fname.startswith('cutflow_Signal_') and fname.endswith('_v2.csv')):
            continue
        fullpath = os.path.join(PATH_CUTFLOW, fname)
        # -------------------------------------------------
        # Signal name 추출
        # cutflow_Signal_2-5_1-0_1-0.0.27_v2.csv
        # -> Signal_2-5_1-0_1-0
        # -------------------------------------------------
        match = re.match(
            r'^cutflow_(Signal_[0-9\-]+_[0-9\-]+_[0-9\-]+)\.0\.\d+_v2\.csv$',
            fname
        )
        if match is None:
            continue
        signal_name = match.group(1)
        mx1, lam1, lam2 = _parse_signal_name(signal_name)
        # -------------------------------------------------
        # cutflow 읽기
        # -------------------------------------------------
        df_cut = pd.read_csv(
            fullpath,
            comment='#'
        )
        # generated row
        row_gen = df_cut[df_cut['cut'] == 'generated']
        # sel row
        row_sel = df_cut[df_cut['cut'] == 'sel']
        if len(row_gen) == 0 or len(row_sel) == 0:
            continue
        N_gen = int(row_gen.iloc[0]['n_raw'])
        N_sel = int(row_sel.iloc[0]['n_raw'])
        records.append({
            'mx1': mx1,
            'lam1': lam1,
            'lam2': lam2,
            'N_gen': N_gen,
            'N_sel_crosscheck': N_sel,
        })
    # -----------------------------------------------------
    # 같은 signal point끼리 merge(sum)
    # -----------------------------------------------------
    df = pd.DataFrame(records)
    if len(df) == 0:
        return pd.DataFrame(
            columns=[
                'mx1',
                'lam1',
                'lam2',
                'N_gen',
                'N_sel_crosscheck'
            ]
        )
    df = (
        df
        .groupby(['mx1', 'lam1', 'lam2'], as_index=False)
        .sum()
    )
    return df

def build_bkg_df(model_tag=None):
    """
    BDT_cut/out 폴더에서 bkg_lumi300_mx1*.csv의 TOTAL 행을 읽어
    (model, bdt_cut, mx1, b0_ref, sigmab0_ref) DataFrame 반환.

    b0_ref      = b0_300 / 300   (L=1 fb⁻¹ 기준)
    sigmab0_ref = sigmab0_300 / 300
    → datacard 생성 시: b0(L) = b0_ref × L
    """
    LUMI_REF = 300.0
    records = []

    for folder in sorted(os.listdir(PATH_BDTOUT)):
        if folder == 'FINAL':
            continue
        folder_path = os.path.join(PATH_BDTOUT, folder)
        if not os.path.isdir(folder_path):
            continue

        idx = folder.rfind('_')
        if idx == -1:
            continue
        mtag, cut_tag = folder[:idx], folder[idx + 1:]

        if folder.split('_')[0] != 'v2':
            continue

        if model_tag is not None and mtag != model_tag:
            continue

        if not re.fullmatch(r'm?[0-9]+p[0-9]+', cut_tag):
            continue
        bdt_cut = round(_parse_cut_tag(cut_tag), 4)

        for fname in sorted(os.listdir(folder_path)):
            match = re.match(r'^bkg_lumi(\d+)_mx1(\d+-\d+)\.csv$', fname)
            if not match:
                continue
            if int(match.group(1)) != 300:
                continue
            mx1 = _hyphen_to_float(match.group(2))

            df_bkg = pd.read_csv(os.path.join(folder_path, fname))
            total_row = df_bkg[df_bkg['sample'] == 'TOTAL']
            if total_row.empty:
                continue

            b0_300      = float(total_row.iloc[0]['b0'])
            sigmab0_300 = float(total_row.iloc[0]['sigmab0'])

            records.append({
                'model':       mtag,
                'bdt_cut':     bdt_cut,
                'mx1':         mx1,
                'b0_ref':      b0_300 / LUMI_REF,
                'sigmab0_ref': sigmab0_300 / LUMI_REF,
            })

    cols = ['model', 'bdt_cut', 'mx1', 'b0_ref', 'sigmab0_ref']
    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records, columns=cols).sort_values(
        ['model', 'mx1', 'bdt_cut']
    ).reset_index(drop=True)


def main():
    df_sig = build_efficiency_df()
    df_sig.to_csv('efficiency.csv', index=False, float_format='%.4f')
    print(df_sig)
    print(f"\nsignal efficiency shape: {df_sig.shape}")

    df_bkg = build_bkg_df()
    df_bkg.to_csv('bkg_yield.csv', index=False, float_format='%.6f')
    print(df_bkg)
    print(f"\nbkg yield shape: {df_bkg.shape}")


if __name__ == '__main__':
    main()


'''

df = pd.read_csv("cross_section_SG.csv")
df = df.set_index(["mx1", "lam1", "lam2"])

# 이제 아래처럼 접근 가능
xs     = df.loc[(1.0, 0.1, 0.1), "xs"]
xs_err = df.loc[(1.0, 0.1, 0.1), "xs_err"]
'''
