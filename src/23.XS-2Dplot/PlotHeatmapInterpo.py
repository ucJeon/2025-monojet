import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from matplotlib.colors import LogNorm

# ============================================================
# USER CONFIG
# ============================================================
CMAP         = "viridis"
OUTPUT_DIR   = "XSEC2D_Planes"
DPI          = 300

# ============================================================

def plot_simple_xsec_plane(csv_path: str, mx1_target: float):
    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        return

    # 헤더 공백 제거 및 로드
    df_raw = pd.read_csv(csv_path)
    df_raw.columns = [c.strip() for c in df_raw.columns]

    # (2)번 코드 기준: 첫 번째 컬럼이 sample_name, 두 번째가 xsec
    col_name = df_raw.columns[0]
    xsec_col = df_raw.columns[1]

    parsed_data = []
    for _, row in df_raw.iterrows():
        sample = str(row[col_name])
        try:
            # (2)번 코드 파싱 로직 적용
            # 예: "MX1_1-0_0-03_0-04" 형태일 경우
            parts = sample.split("_")
            mx1  = float(parts[1].replace("-", "."))
            
            # 특정 MX1만 필터링
            if abs(mx1 - mx1_target) > 0.01: 
                continue
                
            lam1 = float(parts[2].replace("-", "."))
            # lam2의 경우 rstrip(".0") 처리가 필요할 수 있어 안전하게 float 변환
            lam2 = float(parts[3].replace("-", ".").rstrip(".0")) if parts[3].endswith(".0") else float(parts[3].replace("-", "."))
            
            xsec = float(row[xsec_col])
            # parsed_data.append([lam1, lam2, xsec])
            if lam1 <= 1.0 and lam2 <= 1.0:
                parsed_data.append([lam1, lam2, xsec])
        except Exception as e:
            # 파싱 실패 시 출력 (디버깅용)
            # print(f"[DEBUG] Parsing failed for {sample}: {e}")
            continue

    df = pd.DataFrame(parsed_data, columns=['l1', 'l2', 'xsec'])
    
    if df.empty:
        print(f"[WARN] No matching data for MX1 = {mx1_target}. Check your CSV or MX1 value.")
        return

    # 100 factor 이상의 부드러운 평면 보간
    xi = np.linspace(df['l1'].min(), df['l1'].max(), 200)
    yi = np.linspace(df['l2'].min(), df['l2'].max(), 200)
    X, Y = np.meshgrid(xi, yi)
    
    # 로그 보간 (Cross-section의 급격한 변화 대응)
    grid_z = griddata(
        (df['l1'], df['l2']), 
        np.log10(df['xsec']), 
        (X, Y), 
        method='cubic'
    )
    grid_z = 10**grid_z

    # Plot (Style 1 학습 결과 반영)
    fig, ax = plt.subplots(figsize=(4, 3))
    im = ax.imshow(
        grid_z, origin="lower", aspect="auto",
        extent=[xi.min(), xi.max(), yi.min(), yi.max()],
        cmap=CMAP, 
        norm=LogNorm(vmin=df['xsec'].min(), vmax=df['xsec'].max())
    )

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(r"Cross Section $\sigma$ [pb]", fontsize=11)

    ax.set_xlabel(r"$\lambda_{1}$", fontsize=12)
    ax.set_ylabel(r"$\lambda_{2}$", fontsize=12)
    #ax.set_title(rf"Cross Section Plane ($M_{{X_1}}$ = {mx1_target:.1f} TeV)", 
    #             fontsize=13, fontweight='bold', pad=12)

    plt.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fname = f"{OUTPUT_DIR}/XSEC_MX1_{mx1_target:.1f}_Plane.png"
    plt.savefig(fname, dpi=DPI)
    print(f"[SAVE] {fname}")
    plt.close()

if __name__ == "__main__":
    input_csv = "cross_sections.csv"
    
    # 예시: MX1 리스트 (본인의 데이터에 맞춰 수정)
    # 예: 0.5, 1.0, 1.5 등
    for val in [1.0,1.5,2.0,2.5]: 
        plot_simple_xsec_plane(input_csv, val)
