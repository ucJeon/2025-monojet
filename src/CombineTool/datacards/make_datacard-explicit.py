import pandas as pd
import os

import pandas as pd
import os

def generate_datacard(version, ntrees, maxdepth, bdt_cut, lumi, mx1, sig_yield=1.0, unc_mode="all"):
    """
    sig_yield: mx1, lam1=0.1, lam2=0.1 조건에서 필터링된 시그널의 기대 이벤트 수
    """
    # 1. 경로 및 파일 설정
    cut_str = f"{abs(bdt_cut):.4f}".replace('.', 'p')
    prefix = "m" if bdt_cut < 0 else ""
    folder_name = f"{version}_{ntrees}_{maxdepth}_{prefix}{cut_str}"
    # 실제 환경에 맞게 경로 수정 필요
    base_path = f"/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_cut/out/{folder_name}"

    input_file = f"bkg_lumi{lumi}_mx1{mx1.replace('.', '-')}.csv"
    output_file = f"datacard_lumi{lumi}_mx1{mx1.replace('.', '-')}_cut{cut_str}_{unc_mode}.txt"
    full_input_path = os.path.join(base_path, input_file)

    if not os.path.exists(full_input_path):
        print(f"Error: 파일을 찾을 수 없습니다 -> {full_input_path}")
        return

    # 2. 데이터 로드 및 전처리
    df = pd.read_csv(full_input_path)
    
    # [수정] 'TOTAL' 행은 제외하고 실제 백그라운드 샘플만 추출
    df_bkg = df[df['sample'] != 'TOTAL'].copy()
    
    # 프로세스 이름 간소화 (sel_ttbar.1_v2.root -> ttbar.1)
    def clean_name(name):
        return name.replace("sel_", "").replace(f"_{version}.root", "")
    
    df_bkg['proc_name'] = df_bkg['sample'].apply(clean_name)

    # Observation은 모든 백그라운드의 합 (Integer rounding)
    observations = int(round(df_bkg['b0'].sum()))
    n_bkg = len(df_bkg)

    # 3. 데이터카드 상단 (Header)
    card = []
    card.append(f"imax 1  number of channels")
    card.append(f"jmax {n_bkg}  number of backgrounds")
    card.append(f"kmax *")
    card.append("-" * 120)
    card.append(f"bin         bin1")
    card.append(f"observation {observations}")
    card.append("-" * 120)

    # Bin, Process, ID, Rate 라인 생성
    col_width = 18
    proc_list = ["sig"] + df_bkg['proc_name'].tolist()
    
    card.append("bin".ljust(25) + "".join([b.ljust(col_width) for b in ["bin1"] * (n_bkg + 1)]))
    card.append("process".ljust(25) + "".join([p.ljust(col_width) for p in proc_list]))
    card.append("process".ljust(25) + "".join([str(i).ljust(col_width) for i in range(n_bkg + 1)]))

    # [수정] 시그널 초기값 반영 (lam1=0.1, lam2=0.1 기준 yield)
    rate_list = [sig_yield] + df_bkg['b0'].tolist()
    card.append("rate".ljust(25) + "".join([f"{r:<{col_width}.4f}" for r in rate_list]))
    card.append("-" * 120)

    # 4. 오차 추가 로직
    if unc_mode == "none":
        card[2] = "kmax 0"
    else:
        # (A) Systematic Uncertainties
        if unc_mode == "all":
            syst_uncs = {
                "lumi": {"all": 1.023},
                "xs_ttbar": {"ttbar": 1.06},
                "xs_wjets": {"wjets": 1.04},
                "xs_zjets": {"zjets": 1.04},
                "xs_diboson": {"ww": 1.05, "wz": 1.05, "zz": 1.05},
                "sig_eff": {"sig": 1.10}
            }

            for unc_name, config in syst_uncs.items():
                row_vals = ["-"] * (n_bkg + 1)
                active = False
                for i, p_name in enumerate(proc_list):
                    if "all" in config:
                        row_vals[i] = f"{config['all']:.3f}"
                        active = True
                    else:
                        for key, val in config.items():
                            if key in p_name:
                                row_vals[i] = f"{val:.3f}"
                                active = True
                if active:
                    card.append(f"{unc_name:<15} lnN".ljust(25) + "".join([v.ljust(col_width) for v in row_vals]))

        # (B) Statistical Uncertainties
        # [수정] lnN 대신 autoMCStats 사용 권장 (백그라운드가 많을 때 Combine 버그 방지)
        if unc_mode in ["stats", "all"]:
            # 기존 방식(lnN)을 유지하고 싶다면 아래 주석 해제, 아니면 autoMCStats 사용
            for idx, (db_idx, row) in enumerate(df_bkg.iterrows()):
                val, err = row['b0'], row['sigmab0']
                if val > 0 and err > 0:
                    unc_val = 1 + (err / val)
                    row_vals = ["-"] * (n_bkg + 1)
                    row_vals[idx + 1] = f"{unc_val:.4f}" # idx+1은 sig 다음 순서
                    card.append(f"stat_{row['proc_name'] :<15} lnN".ljust(25) + "".join([v.ljust(col_width) for v in row_vals]))

    # [추가] 데이터카드 맨 아래에 통계 오차 자동 계산 한 줄 추가 (Combine 권장 방식)
    # card.append("bin1 autoMCStats 10") 

    # 5. 파일 저장
    with open(output_file, "w") as f:
        f.write("\n".join(card))
    print(f"[{unc_mode.upper()}] Datacard created: {output_file}")
# ==========================================
# 실행부: 세 가지 모드를 모두 생성하여 비교 가능
# ==========================================
if __name__ == "__main__":
    configs = [{"mx1": "1-0", "cut": 0.1050}, 

               {"mx1": "2-0", "cut": 0.1440}]
    modes = ["none", "stats", "all"] # (1), (2), (3) 단계별 생성
    
    for lumi in [300]:
        for conf in configs:
            for m in modes:
                generate_datacard(
                    version="v2", ntrees=2500, maxdepth=4, 
                    bdt_cut=conf["cut"], lumi=lumi, mx1=conf["mx1"],
                    unc_mode=m
                )
