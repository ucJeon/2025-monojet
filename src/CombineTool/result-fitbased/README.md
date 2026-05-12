# result-fitbased — XS-fit 기반 Exclusion Contour

Cross-section 해석 공식과 efficiency 보간을 이용해 (λ₁, λ₂) 평면에서
smooth한 배제 경계선을 그리는 워크플로우.

기존 yield-spline 방식의 wriggle 문제를 해결하고, 물리적으로 올바른
cross section 기반 배제를 수행한다. 자세한 이론적 배경은
[`xsfit-approach-101.md`](../xsfit-approach-101.md)를 참고.

---

## 핵심 아이디어

기준점 (λ₁, λ₂) = (0.1, 0.1) 에서 Combine을 **1회** 실행해 N_exc를 추출한다.

$$N_{\rm exc} = r_{\rm up}^{\rm median} \times \sigma_{\rm ref} \times \mathcal{L} \times 1000 \times \varepsilon_{\rm ref}$$

임의의 점 (λ₁, λ₂)는 아래 조건을 만족할 때 **배제**된다:

$$\sigma(\lambda_1, \lambda_2) \times \varepsilon(\lambda_1, \lambda_2) \times \mathcal{L} \times 1000 > N_{\rm exc}$$

배제 경계선(contour)은 등호 조건으로 결정되며, σ가 해석 공식이고 ε이 smooth
2D spline이므로 격자 해상도와 무관하게 임의로 dense하게 그릴 수 있다.

---

## 입력 파일

| 파일 | 내용 | 경로 |
|------|------|------|
| `results-xsfit.csv` | r_up (5 quantile), N_exc per (mx1, lumi, mode) | `../results-xsfit.csv` |
| `cross_section_SG.csv` | MG5 계산 XS (mx1, lam1, lam2) | `src/23.XS-2Dplot/` |
| `efficiency.csv` | BDT-cut 이후 eff_gb per (mx1, lam1, lam2, model, bdt_cut) | `src/Efficiency-signal/` |

---

## 파이프라인

### Step 1 — Combine 실행 (CMSSW 환경)

```bash
# CMSSW 환경 진입 (CombineTool/ 에서)
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd CMSSW_14_1_0_pre4/src && cmsenv && cd -

bash run_asymptotic_w-blind_card-all-xsfit.sh
```

- 입력: `datacards/datacards_XSEC-JES-MET_noObs/` (observation=-1, blind)
- 기준점: λ₁ = λ₂ = 0.1
- 스캔: lumi ∈ {300, 3000} × mode ∈ {none, stats, sys1, sys2, sys3} × MX1 ∈ {1.0, 1.5, 2.0, 2.5}
- 출력: `outputs-xsfit/higgsCombine.Lumi{L}.MX{mx}.{mode}.xsfit.AsymptoticLimits.mH{mh}.root`

Combine 출력 예시 (lumi=300, MX10, stats):
```
Expected  2.5%: r < ...
Expected 16.0%: r < ...
Expected 50.0%: r < ...   ← median, 주로 사용
Expected 84.0%: r < ...
Expected 97.5%: r < ...
```

### Step 2 — r_up 파싱 및 N_exc 계산

```bash
# CMSSW 환경 필요 (ROOT import)
python3 parse_results-xsfit.py
```

- `outputs-xsfit/*.root` → quantile별 r_up 읽기
- `rate_sig_ref = xs_ref × lumi × 1000 × eff_ref` 계산
- `N_exc_{quantile} = r_{quantile} × rate_sig_ref`
- 출력: `results-xsfit.csv`

`results-xsfit.csv` 컬럼:

| 컬럼 | 설명 |
|------|------|
| `mx1, lumi, mode` | 식별자 |
| `xs_ref, eff_ref, rate_sig_ref` | 기준점 값 |
| `r_exp_{m2s,m1s,med,p1s,p2s}` | quantile별 r_up |
| `N_exc_exp_{m2s,m1s,med,p1s,p2s}` | 대응하는 N_exc |

### Step 3 — Contour 플롯

```bash
python3 plot_contour_fitbased.py
```

- `results-xsfit.csv`에서 N_exc_exp_med (및 ±1σ) 읽기
- `cross_section_SG.csv` → MX1별 A 파라미터 iterative fitting
- `efficiency.csv` → RectBivariateSpline 2D 보간
- 500×500 dense grid에서 signal yield 계산 후 contour 추출
- 출력: `plots/contour_lumi{L}_{mode}_{log|lin}.{pdf,png}`

λ_crit 수치 결과는 `lam_crit_summary.csv`로 저장된다.

---

## 입력 물리 함수

### XS 해석 공식

$$\sigma(\lambda_1, \lambda_2) = \frac{A \cdot \lambda_1^2 \cdot \lambda_2^2}{4.0 \cdot \lambda_1^2 + \lambda_2^2}$$

A는 MX1별로 MG5 계산값에 iterative fitting으로 결정 (threshold 10%):

| MX1 [TeV] | A | 주의 |
|-----------|---|------|
| 1.0 | 5.4682 | — |
| 1.5 | 0.81048 | — |
| 2.0 | 0.16842 | MG5와 최대 ~10% 편차 |
| 2.5 | 0.042582 | MG5와 최대 ~10% 편차 |

### Efficiency 보간

```python
from scipy.interpolate import RectBivariateSpline
spline = RectBivariateSpline(lam1_vals, lam2_vals, eff_matrix, kx=3, ky=3)
```

MX1별 최적 BDT cut에서의 eff_gb를 사용:

| MX1 | BDT cut |
|-----|---------|
| 1.0 | 0.105 |
| 1.5 | 0.135 |
| 2.0 | 0.144 |
| 2.5 | 0.152 |

---

## Uncertainty Modes

| mode | 적용 불확도 |
|------|------------|
| `none` | 없음 |
| `stats` | BKG statistical (lnN) |
| `sys1` | stats + XSEC 10% (signal) |
| `sys2` | sys1 + JES 5% (sig+bkg) |
| `sys3` | sys2 + MET 4% (sig+bkg) |

---

## 주요 결과

### λ_crit 요약 (lumi=300 fb⁻¹, stats mode)

<!-- TODO: lam_crit_summary.csv 에서 발췌 -->

| MX1 [TeV] | λ₁_crit (fixed λ₂=0.5) | λ₂_crit (fixed λ₁=0.5) |
|-----------|------------------------|------------------------|
| 1.0 | | |
| 1.5 | | |
| 2.0 | | |
| 2.5 | | |

### 예시 Contour Plot

<!-- TODO: plots/contour_lumi300_stats_log.png -->

---

## 파일 구조

```
result-fitbased/
├── README.md
├── plot_contour_fitbased.py     # Step 3 메인 스크립트
├── lam_crit_summary.csv         # λ_crit 수치 결과 (모든 lumi×mode×mx1)
├── plots/
│   ├── contour_lumi{L}_{mode}_log.{pdf,png}
│   ├── contour_lumi{L}_{mode}_lin.{pdf,png}
│   ├── eff_slices_all.pdf        # efficiency slice 검증 플롯
│   ├── grid_panels_MX{mx1}.pdf   # grid-level 검증
│   ├── sig_lumi_compare_MX{mx1}.pdf
│   └── xs_residual_all.pdf       # A fitting 잔차
└── verify/
    └── verify_grids.py           # A fitting / eff 보간 검증 스크립트
```

---

## 기존 방식과의 비교

| 항목 | 기존 (`result/`) | 이 방식 (`result-fitbased/`) |
|------|-----------------|------------------------------|
| Combine 실행 횟수 | MX1별 1회 (기준점 고정) | MX1별 1회 (기준점 고정) |
| Contour 계산 | r_up × σ 비율 (해석 공식) | N_exc 역치, xs 공식 + eff spline |
| Signal yield 처리 | BDT CSV에서 직접 읽기 (spline) | xs × ε 공식 계산 |
| Wriggle | 발생 가능 (MC stat + spline 아티팩트) | 없음 (해석 공식이 smooth) |
| λ 범위 외삽 | 격자 범위 제한 | 해석 공식으로 임의 범위 가능 |
