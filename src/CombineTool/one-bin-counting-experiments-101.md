# CLs Limit Setting in 1-Bin Counting Experiments

## Phenomenology Study를 위한 실전 가이드

> **교재 기반**: Behnke, Kröninger, Schott, Schörner-Sadenius (eds.), _Data Analysis in High Energy Physics: A Practical Guide to Statistical Methods_ (Wiley-VCH, 2014)
> 
> **적용 사례**: Bottom-associated monojet channel을 통한 non-thermal dark matter 탐색
> 
> **목적**: 다른 학생들에게도 설명할 수 있는 수준으로, 교과서의 통계 프레임워크를 1-bin counting experiment 관점에서 정리

---

## 1. 큰 그림: 우리가 하려는 것

BSM(Beyond Standard Model) 탐색에서 가장 기본적인 질문은 이것이다:

> "데이터에서 새로운 물리 신호가 보이는가? 보이지 않는다면, 신호의 세기를 얼마나 제한할 수 있는가?"

이 질문에 답하는 통계적 도구가 **hypothesis testing**이고, 그 결과를 정량화하는 방법이 **CLs limit setting**이다.

**1-bin counting experiment**란 가장 단순한 형태의 탐색을 말한다: 특정 selection cut 이후 남은 event 수 $N$을 세는 것. BDT cut을 적용한 후의 monojet analysis가 정확히 이 경우에 해당한다.

---

## 2. 통계적 모델 (Statistical Model)

### 2.1 Poisson 분포 — 모든 것의 출발점

교과서 Ch.1 (Barlow)에서 설명하듯, 입자물리 실험에서 event count는 **Poisson 분포**를 따른다:

$$P(N | \nu) = \frac{\nu^N}{N!} e^{-\nu}$$

여기서 $\nu$는 expected event 수(평균), $N$은 관측된 event 수.

### 2.2 Signal + Background 모델

1-bin counting experiment에서 expected event 수는:

$$\nu = \mu \cdot s_0 + b$$

|기호|의미|예시 (monojet)|
|---|---|---|
|$\mu$|signal strength parameter|$\mu = 1$이면 nominal signal, $\mu = 0$이면 background-only|
|$s_0$|expected signal yield (nominal)|BDT cut 후 남은 signal MC events (from `sg_after` in CSV)|
|$b$|expected background yield|BDT cut 후 남은 background MC events ($t\bar{t}$, W+jets, Z+jets, diboson)|

**Likelihood function** (교과서 Eq. 3.13의 단순 버전):

$$L(N | \mu, b) = \frac{(\mu s_0 + b)^N}{N!} e^{-(\mu s_0 + b)}$$

> **핵심 포인트**: $s_0$는 signal CSV의 `sg_after` 값에서 직접 가져와야 한다. $b_0$로 근사하면 안 된다. 이것은 실제 분석에서 겪었던 버그이기도 하다.

---

## 3. 두 가지 가설 (Hypotheses)

교과서 Ch.3 (Schott)의 프레임워크를 따르면:

### 3.1 Null Hypothesis $H_0$: Background-only

$$H_0: \mu = 0 \quad \Rightarrow \quad \nu = b$$

"새로운 물리는 없다" — Standard Model 과정만으로 데이터를 설명.

### 3.2 Alternative Hypothesis $H_1$: Signal + Background

$$H_1: \mu = 1 \quad \Rightarrow \quad \nu = s_0 + b$$

"특정 coupling ($\lambda_1, \lambda_2$)과 mass ($M_{X_1}$)에서 BSM 신호가 존재한다."

### 3.3 일반화: arbitrary $\mu$

Exclusion limit을 설정할 때는 $\mu$를 자유 파라미터로 두고, 어떤 $\mu$ 값까지 배제할 수 있는지를 탐색한다.

---

## 4. Test Statistic 선택

### 4.1 왜 test statistic이 필요한가

교과서 Sec. 3.1.2: 관측 데이터 $N$으로부터 가설의 호환성을 판단하려면, 데이터를 하나의 숫자로 요약하는 **test statistic** $t$가 필요하다.

### 4.2 1-bin counting에서의 선택지

**가장 단순한 선택**: $t = N$ (관측 event 수 그 자체)

- 교과서 Fig. 3.1의 예시가 정확히 이 경우
- $H_0$ 하에서 $t = N \sim \text{Poisson}(b)$
- $H_1$ 하에서 $t = N \sim \text{Poisson}(s_0 + b)$

**더 강력한 선택**: Profile likelihood ratio (교과서 Sec. 11.2.2)

$$q_\mu = -2 \ln \frac{L(\mu, \hat{\hat{b}})}{L(\hat{\mu}, \hat{b})}$$

- $\hat{\hat{b}}$: $\mu$를 고정했을 때 $b$의 conditional MLE (profile)
- $\hat{\mu}, \hat{b}$: 전체 likelihood를 maximize하는 global MLE
- Neyman-Pearson lemma에 의해, likelihood ratio가 optimal test statistic

> **Monojet 분석에서**: 우리는 단순 counting ($t = N$)을 사용한다. Nuisance parameter가 있을 경우 profile likelihood ratio를 쓸 수도 있지만, 1-bin counting에서는 두 접근이 본질적으로 동일한 정보를 사용한다.

---

## 5. p-Value와 Confidence Level

### 5.1 p-value의 정의

교과서 Sec. 3.5:

> $p$-value는 "null hypothesis가 참이라고 가정했을 때, 관측된 것만큼 또는 그 이상으로 극단적인 결과를 얻을 확률"이다.

$$p_0 = P(t \geq t_{\text{obs}} | H_0) = \sum_{N=N_{\text{obs}}}^{\infty} \frac{b^N}{N!} e^{-b}$$

이것이 작을수록 $H_0$ (background-only)를 **기각할 근거가 강하다** — 즉, 데이터가 background-only 가설과 양립하기 어렵다는 뜻이다.

### 5.2 Significance (Z-value)

$$p \text{-value} \longleftrightarrow Z\text{-value}$$

Gaussian의 upper tail probability로 변환:

$$p = \frac{1}{2}\left[1 - \text{erf}\left(\frac{Z}{\sqrt{2}}\right)\right]$$

|Z|p-value|의미|
|---|---|---|
|1.64|0.05|95% CL exclusion|
|3|$1.3 \times 10^{-3}$|"Evidence"|
|5|$2.9 \times 10^{-7}$|"Discovery"|

### 5.3 Counting experiment에서의 근사 significance

교과서 Eq. 3.8 부근의 근사식들:

$$Z \approx \frac{S}{\sqrt{S + B}} \quad \text{(단순 근사)}$$

$$Z \approx \sqrt{2\left[(S+B)\ln\left(1 + \frac{S}{B}\right) - S\right]} \quad \text{(Asimov 근사, 더 정확)}$$

여기서 $S = \mu s_0$, $B = b$.

---

## 6. CLs Method — 핵심

### 6.1 왜 CLs가 필요한가

교과서 Sec. 3.6과 Sec. 4.6.2에서 설명하는 핵심 문제:

**문제**: 순수한 frequentist upper limit ($CL_{s+b}$)는 background가 downward fluctuation하면, 실험이 sensitivity가 없는 signal 영역까지 배제해버릴 수 있다.

교과서의 예시 (Sec. 4.6.2): $N \sim \text{Poisson}(\theta + \nu)$에서 $N_{\text{obs}} = 0$이고 $\nu$가 클 때, $\theta$에 대한 frequentist upper limit이 실제로는 실험이 민감하지 않은 작은 $\theta$ 값까지 배제하게 된다.

> "if two experiments have different background contaminations but observe the same number of events, the experiment with the larger contamination will be able to exclude more signal" — 교과서 Sec. 4.6.2

이것은 물리적으로 부당하다.

### 6.2 CLs의 정의

교과서 Sec. 3.6과 Sec. 11.2.2.3에 따르면:

세 가지 confidence level을 정의한다 (Fig. 11.5 참조):

**$CL_{s+b}$**: signal+background 가설 하에서의 p-value

$$CL_{s+b} = P(t \geq t_{\text{obs}} | H_1) = P(t \geq t_{\text{obs}} | s+b)$$

**$CL_b$**: background-only 가설 하에서의 p-value

$$CL_b = P(t \geq t_{\text{obs}} | H_0) = P(t \geq t_{\text{obs}} | b\text{-only})$$

**$CL_s$**: 보정된 confidence level

$$\boxed{CL_s = \frac{CL_{s+b}}{CL_b}}$$

### 6.3 Exclusion 기준

$$CL_s < 0.05 \quad \Longleftrightarrow \quad \text{95% CL에서 signal hypothesis 배제}$$

### 6.4 직관적 이해

|상황|$CL_{s+b}$|$CL_b$|$CL_s$|해석|
|---|---|---|---|---|
|Data가 s+b와 비호환|작다|크다|작다|→ 배제 (정당)|
|Background downward fluctuation|작다|작다|~1|→ 배제 안 함 (보호!)|
|Sensitivity 없음|~0.5|~0.5|~1|→ 배제 안 함 (보호!)|

$CL_b$로 나누는 것은 "background-only에서도 이런 관측은 드물다"는 경우를 보정하는 것이다. 이렇게 하면 sensitivity가 없는 영역을 잘못 배제하는 것을 방지한다.

---

## 7. 실전 구현: Toy Monte Carlo

### 7.1 알고리즘 (1-bin counting)

교과서 Sec. 10.5 (Ensemble Tests)와 Sec. 11.2의 프레임워크:

```
입력: s_0 (expected signal), b (expected background), N_obs (관측값)
      n_toys (toy experiment 수)

[Step 1] s+b toys 생성
   for i = 1 to n_toys:
       N_toy[i] = Poisson(mu * s_0 + b)    # s+b 가설에서 sampling

[Step 2] b-only toys 생성
   for i = 1 to n_toys:
       N_toy_b[i] = Poisson(b)             # b-only 가설에서 sampling

[Step 3] CL 계산
   CL_{s+b} = (N_toy >= N_obs인 toy의 비율)   # s+b toys에서
   CL_b     = (N_toy_b >= N_obs인 toy의 비율)  # b-only toys에서
   CL_s     = CL_{s+b} / CL_b

[Step 4] Exclusion 판단
   if CL_s < 0.05 → 이 signal hypothesis를 95% CL에서 배제
```

### 7.2 Upper limit on $\mu$ 찾기

$\mu$를 scan하면서 $CL_s(\mu) = 0.05$가 되는 지점을 찾으면, 그것이 $\mu$의 95% CL upper limit이다.

```
for mu in [0.01, 0.02, ..., 5.0]:
    s = mu * s_0
    # toy experiments로 CL_s(mu) 계산
    if CL_s(mu) == 0.05:
        mu_upper = mu   # → 이것이 95% CL upper limit
```

이것을 cross section으로 변환:

$$\sigma_{\text{upper}} = \mu_{\text{upper}} \times \sigma_{\text{theory}}$$

---

## 8. Systematic Uncertainty 포함하기

### 8.1 Nuisance Parameters

교과서 Sec. 3.5.2: systematic uncertainty를 **nuisance parameter**로 likelihood에 포함시킨다.

Background yield uncertainty의 경우:

$$L(N, \tilde{b} | \mu, \nu_b) = \underbrace{\frac{(\mu s_0 + \nu_b)^N}{N!} e^{-(\mu s_0 + \nu_b)}}_{\text{main measurement}} \times \underbrace{\frac{1}{\sqrt{2\pi}\sigma_b} e^{-\frac{(\tilde{b} - \nu_b)^2}{2\sigma_b^2}}}_{\text{auxiliary constraint}}$$

여기서:

- $\nu_b$: 실제 background rate (nuisance parameter)
- $\tilde{b}$: background의 best estimate (auxiliary measurement)
- $\sigma_b$: background uncertainty

### 8.2 Log-normal vs Gaussian constraint

실제 분석에서 background yield처럼 양수여야 하는 양에는 **log-normal** constraint가 더 적절하다:

$$\kappa = 1 + \sigma_b / b$$

$$\tilde{\nu}_b = b \cdot \kappa^{\theta}, \quad \theta \sim \mathcal{N}(0, 1)$$

이것은 Denis와의 논의에서 나온 LnN uncertainty treatment와 일치한다.

### 8.3 Toy에서의 구현

교과서 Sec. 3.5.2의 두 가지 접근:

**Marginalisation (Bayesian-inspired)**:

```
for each toy:
    b_varied = draw from constraint (Gaussian or LogNormal)
    N_toy = Poisson(mu * s_0 + b_varied)
```

**Profiling**:

각 toy에서 likelihood를 nuisance parameter에 대해 maximize한 후 test statistic을 계산.

> **Monojet 분석에서**: MC statistical uncertainty ($\sigma_{b_0}$, quadrature sum)를 nuisance parameter로 처리한다. BDT cut ≈ 0.15–0.17에서 relative uncertainty가 급격히 상승하는 것은 high-weight/low-count event 때문이므로, 이 영역에서의 limit은 신중히 해석해야 한다.

---

## 9. Expected Limit과 Brazil Band

### 9.1 Expected (Median) Limit

교과서 Sec. 11.2.2.3과 Sec. 4.6.2:

"만약 진짜로 signal이 없다면($H_0$ 참), 이 실험이 설정할 수 있는 전형적인 limit은?"

1. $H_0$ (b-only)에서 많은 pseudo-experiment를 생성
2. 각 pseudo-experiment에서 $\mu$의 95% CL upper limit을 구함
3. 이 limit distribution의 **median** = expected limit

### 9.2 Brazil Band ($\pm 1\sigma$, $\pm 2\sigma$ bands)

Expected limit distribution의 quantile들:

|Band|Quantile|의미|
|---|---|---|
|$-2\sigma$|2.5%|매우 운이 좋은 경우의 limit|
|$-1\sigma$|16%|운이 좋은 경우|
|Median|50%|전형적인 경우|
|$+1\sigma$|84%|운이 나쁜 경우|
|$+2\sigma$|97.5%|매우 운이 나쁜 경우|

이것을 mass나 coupling parameter의 함수로 그리면 **Brazil band plot**이 된다.

---

## 10. Monojet Analysis에 대한 적용

### 10.1 분석 구조 요약

```
Signal: pp → X₁ (→ invisible) + u + b   (MET + monojet)

Parameters:
  M_X1 ∈ {1.0, 1.5, 2.0, 2.5} TeV
  λ₁:   16-point grid (0.03 – 2.0)
  λ₂:   15-point grid (0.04 – 2.0)

Pipeline:
  MadGraph5 → Pythia8 → Delphes3
  → postprocess.cpp (kinematic variables)
  → TMVA BDT training (10 input variables)
  → BDT cut optimization
  → CLs limit setting (run_limit.py)
```

### 10.2 1-bin counting으로의 mapping

|교과서 notation|Monojet 분석에서의 대응|
|---|---|
|$N_{\text{obs}}$|BDT cut 이후 관측(또는 expected) event 수|
|$s_0$|Signal CSV의 `sg_after` (해당 benchmark point)|
|$b$|Background yield ($t\bar{t}$ + W+jets + Z+jets + diboson), `sample_info.cpp`에서|
|$\sigma_b$|MC statistical uncertainty (quadrature sum)|
|$\mu$|signal strength = $\sigma / \sigma_{\text{theory}}$|
|Luminosity|300 fb$^{-1}$ 또는 3000 fb$^{-1}$|

### 10.3 Cross-section parameterization과의 연결

2D fitting model:

$$\sigma(\lambda_1, \lambda_2) = \frac{A \cdot \lambda_1^2 \cdot \lambda_2^2}{B \cdot \lambda_1^2 + \lambda_2^2}, \quad B = 4.0$$

이 parameterization은 coupling space의 각 point에서 $s_0$를 예측하고, 따라서 CLs limit을 coupling plane 전체에 대해 그릴 수 있게 해준다. 15% deviation threshold과 iterative outlier-dropping으로 유효 영역을 결정한다.

### 10.4 Limit의 물리적 해석

$\mu_{\text{upper}} < 1$이면: 해당 $(M_{X_1}, \lambda_1, \lambda_2)$ point에서의 이론적 cross section이 배제됨

$$\sigma_{\text{theory}}(M_{X_1}, \lambda_1, \lambda_2) > \sigma_{\text{upper}}^{95%\text{CL}}$$

→ 이 parameter space point는 (해당 luminosity에서) 실험적으로 허용되지 않음

---

## ★ 11. Discovery Reach (5σ) 계산법

> 이 섹션은 exclusion (95% CL)과 대비되는 **discovery potential (5σ)** 의 계산법을 다룬다. 교과서 Sec. 11.2.1.1, Sec. 11.2.2.2–3, 그리고 Fig. 11.7b의 프레임워크를 따른다.

### 11.1 Exclusion vs Discovery: 근본적인 차이

둘은 **서로 다른 가설을 기각하는 것**이다:

||Exclusion (95% CL)|Discovery (5σ)|
|---|---|---|
|**기각 대상**|$H_1$ (signal+background)|$H_0$ (background-only)|
|**질문**|"이 signal이 없다고 할 수 있나?"|"background만으로 설명 불가능한가?"|
|**기준**|$CL_s < 0.05$|$p_0 < 5.73 \times 10^{-7}$ (= 5σ)|
|**사용하는 toy**|$H_1$에서 생성, $H_0$에서도 생성|$H_0$에서만 생성|
|**Sensitivity 보정**|필요 (CLs의 $CL_b$ 나눗셈)|불필요|

교과서 Sec. 11.2.2.3에서 명확히 구분한다:

> **Discovery**: $H_0$ (background-only)를 기각. $1 - CL_b < 5.73 \times 10^{-7}$이면 5σ.
> 
> **Exclusion**: $H_1$ (signal+background)를 기각. $CL_s < 0.05$이면 95% CL.

### 11.2 Expected Discovery Significance 계산

**핵심 개념** (교과서 Sec. 11.2.1.1, p.359):

> "The **expected significance** is defined as the significance associated with the **median** number of expected events under the $s+b$ hypothesis."

즉: **"signal이 진짜 있다면, 전형적인(median) 실험에서 얼마나 큰 significance를 얻을 수 있는가?"**

#### 방법 1: Asimov 근사 (공식 하나로 끝)

교과서 Eq. 3.9 / Sec. 11.2.1.1 footnote 3:

$$\boxed{Z_{\text{disc}} = \sqrt{2\left[(s_0 + b)\ln\left(1 + \frac{s_0}{b}\right) - s_0\right]}}$$

이 공식은 "Asimov dataset" — 즉 $N_{\text{obs}} = s_0 + b$ (expected event 수 그 자체)를 관측한 것으로 가정했을 때의 significance이다.

**이것이 바로 네 plot의 dashed line을 그리는 공식이다.**

각 $(\lambda_1, \lambda_2)$ grid point에서:

1. Cross-section parameterization으로 $\sigma(\lambda_1, \lambda_2)$를 구한다
2. $s_0 = \sigma \times \epsilon \times \mathcal{L}$ (efficiency × luminosity)를 계산한다
3. $b$는 BDT cut 이후의 background yield
4. 위 공식에 대입하여 $Z_{\text{disc}}$를 구한다
5. $Z_{\text{disc}} = 5$가 되는 contour를 그린다 → **이것이 5σ discovery reach line**

#### 방법 2: Toy MC (더 정확, systematic 포함 가능)

교과서 Sec. 11.2.2.2의 expected significance 계산:

```
[Step 1] s+b pseudo-experiment를 많이 생성
   for i = 1 to n_toys:
       N_toy[i] = Poisson(s_0 + b)

[Step 2] 각 pseudo-experiment의 p_0를 계산
   각 N_toy[i]에 대해:
       p_0(i) = P(N >= N_toy[i] | b-only) = Σ_{k=N_toy[i]}^{∞} Poisson(k|b)
       Z(i) = Φ^{-1}(1 - p_0(i))

[Step 3] Median significance 추출
   Z_expected = median of {Z(1), Z(2), ..., Z(n_toys)}
```

교과서 Fig. 11.6에서 이 과정이 명시적으로 보인다: median $s+b$ experiment의 test statistic 값에서 $1 - CL_b$를 읽어서 significance로 변환.

#### 비교: 왜 두 방법이 (거의) 같은 결과를 주는가

Asimov 근사는 "$N_{\text{obs}} = s_0 + b$" (즉 median Poisson outcome ≈ mean)를 넣은 것이고, toy MC의 median도 결국 같은 값 주변에 있으므로, systematic이 없으면 두 방법은 거의 일치한다. Systematic이 있으면 toy MC가 더 정확하다.

### 11.3 Systematic Uncertainty가 있을 때

교과서 Sec. 11.2.1.3에서 설명하듯, background uncertainty $\Delta b$가 있으면 significance가 떨어진다:

$$Z_{\text{disc}} \approx \frac{s_0}{\sqrt{b + (\Delta b)^2}} \quad \text{(단순 근사, } s_0 \ll b \text{ 일 때)}$$

더 정확하게는 Asimov formula의 확장 (Cowan et al., EPJC 2011):

$$Z_{\text{disc}} = \left[, 2\left((s_0+b)\ln\frac{(s_0+b)(b+\sigma_b^2)}{b^2+(s_0+b)\sigma_b^2} - \frac{b^2}{\sigma_b^2}\ln\left(1+\frac{\sigma_b^2 s_0}{b(b+\sigma_b^2)}\right)\right),\right]^{1/2}$$

Toy MC에서는 자연스럽게 포함된다:

```
for each toy:
    b_varied = draw from LogNormal(b, σ_b)     # nuisance 변동
    N_toy = Poisson(s_0 + b_varied)            # s+b에서 생성
    p_0 = P(N >= N_toy | b_varied)             # b-only에서 평가 (profiled)
```

### 11.4 Monojet Analysis에서의 구현

네 plot을 재현하는 구체적 절차:

```python
# === Discovery Reach Contour (5σ line) ===

import numpy as np
from scipy.stats import norm

def asimov_discovery_Z(s, b):
    """Asimov expected discovery significance.
       교과서 Eq. 3.9 / Sec. 11.2.1.1"""
    if s <= 0 or b <= 0:
        return 0.0
    return np.sqrt(2 * ((s + b) * np.log(1 + s/b) - s))

# 각 grid point에서 계산
for mx1 in [1.0, 1.5, 2.0, 2.5]:  # TeV
    Z_grid = np.zeros((len(lam1_grid), len(lam2_grid)))

    for i, lam1 in enumerate(lam1_grid):
        for j, lam2 in enumerate(lam2_grid):
            # 1) signal yield: parameterization 또는 CSV에서
            sigma = xs_parameterization(lam1, lam2, mx1)
            s0 = sigma * efficiency * luminosity  # = sg_after
            b  = background_yield_after_bdt_cut   # 모든 mx1에 대해 동일

            # 2) Asimov significance
            Z_grid[i, j] = asimov_discovery_Z(s0, b)

    # 3) Z = 5 contour 그리기
    plt.contour(lam1_grid, lam2_grid, Z_grid.T,
                levels=[5.0],                    # ← 5σ
                linestyles='dashed',
                colors=color_for_mx1)

    # 비교: Z에 해당하는 exclusion contour는
    # CLs = 0.05가 되는 mu_upper = 1 contour (solid line)
```

### 11.5 같은 Plot에 두 Contour가 그려지는 이유

네 plot에서:

- **Solid lines (95% CL)**: 이 coupling에서의 signal을 **배제**할 수 있는 경계. 선 아래쪽(작은 coupling)은 sensitivity 밖이므로 배제할 수 없음.
- **Dashed lines (5σ)**: 이 coupling에서의 signal을 **발견**할 수 있는 경계. 선 아래쪽(작은 coupling)은 발견 불가.

항상 **discovery contour가 exclusion contour보다 위에 있다** (더 큰 coupling 필요). 이유:

$$5\sigma \text{ discovery} \quad \text{vs} \quad 95% \text{ CL exclusion} \approx 1.64\sigma$$

Discovery는 $Z = 5$를 요구하지만, exclusion은 $Z \approx 1.64$면 충분하다. 따라서 같은 signal 세기에서 exclusion은 가능하지만 discovery는 불가능한 영역이 존재한다. 이 사이의 영역이 바로:

> **"배제는 할 수 있지만 발견은 못하는"** 중간 영역

이것은 물리적으로 "실험이 이 parameter space를 probe할 수는 있지만, 확실한 claim을 하기에는 signal이 부족한" 영역이다.

### 11.6 Discovery vs Exclusion: 핵심 대비 요약

```
                  coupling 큰 쪽 (signal 강함)
                         ↑
     ┌───────────────────┼───────────────────┐
     │                   │                   │
     │   5σ 발견 가능     │                   │
     │   (dashed 위쪽)    │                   │
     │                   │                   │
     ├─ ─ ─ ─ ─ ─ ─ ─ ─ ┤  5σ dashed line   │
     │                   │                   │
     │   배제 가능하지만   │                   │
     │   발견은 불가능     │  ← 이 영역이 핵심! │
     │                   │                   │
     ├───────────────────┤  95% solid line    │
     │                   │                   │
     │   배제도 발견도     │                   │
     │   불가능           │                   │
     │   (sensitivity 밖) │                   │
     └───────────────────┼───────────────────┘
                         ↓
                  coupling 작은 쪽 (signal 약함)
```

---

## 12. 흔한 함정과 체크리스트

교과서 전반과 실제 분석 경험에서:

### 함정 1: $s_0$와 $b_0$ 혼동

$s_0$는 각 benchmark point $(M_{X_1}, \lambda_1, \lambda_2)$마다 다르다. Signal CSV의 `sg_after` 값을 직접 사용해야 한다.

### 함정 2: BDT cut에 따른 uncertainty 급변

BDT cut ≈ 0.15–0.17에서 background의 relative uncertainty가 급격히 증가한다. 이것은 statistical artifact (high-weight, low-count events)이므로, limit의 안정성을 BDT cut 함수로 확인해야 한다.

### 함정 3: CLs를 "confidence level"로 부르는 것

교과서 Sec. 11.2.2.3에서 명시하듯, $CL_s$는 진정한 confidence level이 아니라 confidence level의 비율(ratio)이다. 이것은 frequentist coverage를 보장하지 않으므로, 해석과 다른 결과와의 비교 시 주의가 필요하다.

### 함정 4: Expected limit 없이 observed limit만 보고하는 것

Expected limit과 brazil band는 분석의 sensitivity를 보여준다. Observed limit이 expected band 안에 있는지 확인하는 것은 분석 검증의 핵심이다.

### 함정 5: Signal uncertainty의 출처 혼동

Signal cross section의 이론적 uncertainty는 LHC DM Working Group prescription과 MadGraph5 manual (Alwall et al., JHEP 2014)을 참조해야 한다. SM background uncertainty prescription과는 다르다.

---

## 13. 요약: 한눈에 보는 흐름도

```
                    ┌─────────────────────────────┐
                    │  Physics Model 정의          │
                    │  (MX1, λ1, λ2) → σ_theory   │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  MC Simulation               │
                    │  MadGraph → Pythia → Delphes │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Event Selection             │
                    │  BDT training + cut → s₀, b  │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Statistical Model            │
                    │  L(N|μ,b) = Poisson(μs₀+b)   │
                    │  + nuisance constraints       │
                    └─────┬────────────┬──────────┘
                          │            │
            ┌─────────────▼──┐   ┌─────▼─────────────┐
            │  EXCLUSION      │   │  DISCOVERY         │
            │  (95% CL)       │   │  (5σ)              │
            │                 │   │                    │
            │  CLs scan:      │   │  Asimov Z:         │
            │  기각 대상: H₁   │   │  기각 대상: H₀     │
            │  CLs < 0.05     │   │  Z ≥ 5             │
            │  → μ_upper      │   │  → Z(s₀,b) contour │
            └────────┬────────┘   └────────┬───────────┘
                     │                     │
            ┌────────▼─────────────────────▼───────────┐
            │  Combined Contour Plot                    │
            │  (λ₁, λ₂) plane:                         │
            │    solid  = 95% CL exclusion              │
            │    dashed = 5σ discovery reach             │
            │    per M_X1 = {1.0, 1.5, 2.0, 2.5} TeV   │
            └──────────────────────────────────────────┘
```

---

## 14. 교과서 참고 섹션 정리

|주제|교재 위치|핵심 내용|
|---|---|---|
|Poisson 분포|Ch.1, Sec. 1.3.2|Counting experiment의 기본 분포|
|Hypothesis testing 기본|Ch.3, Sec. 3.1|$H_0$, $H_1$, type I/II error, power|
|Test statistic 선택|Ch.3, Sec. 3.2|Neyman-Pearson lemma, likelihood ratio|
|p-value와 significance|Ch.3, Sec. 3.5|Z-value 변환, $S/\sqrt{S+B}$ 근사|
|Systematic uncertainty 포함|Ch.3, Sec. 3.5.2|Marginalisation vs profiling|
|Test inversion → limit|Ch.3, Sec. 3.6|CLs 도입의 motivation|
|Neyman construction|Ch.4, Sec. 4.3.1|Confidence belt, coverage|
|Poisson mean의 upper limit|Ch.4, Sec. 4.3.3.4|Garwood interval, Feldman-Cousins|
|Nuisance parameter 처리|Ch.4, Sec. 4.3.6|Profiling, Bayesian elimination, coverage check|
|Sensitivity와 CLs|Ch.4, Sec. 4.6.2|Power constraint, CLs의 motivation|
|Ensemble test (toy MC)|Ch.10, Sec. 10.5|Pseudo-experiment 생성, limit distribution|
|Profile likelihood ratio|Ch.11, Sec. 11.2.2|Full search procedure walk-through|
|CLs 실전 적용|Ch.11, Sec. 11.2.2.3|$CL_{s+b}$, $CL_b$, $CL_s$ 정의와 exclusion|
|Expected discovery significance|Ch.11, Sec. 11.2.1.1|Median s+b experiment의 significance|
|Discovery vs exclusion 기준|Ch.11, Sec. 11.2.2.3|5σ discovery, 95% CL exclusion 규칙|
|Expected significance vs luminosity|Ch.11, Fig. 11.7b|$Z$ vs $\mathcal{L}$ plot, discovery reach 추정|
|Asimov significance 공식|Ch.3, Eq. 3.9|$Z = \sqrt{2[(s+b)\ln(1+s/b)-s]}$|

---

## 부록 A: 핵심 공식 모음

$$\boxed{L(N|\mu, b) = \frac{(\mu s_0 + b)^N}{N!} e^{-(\mu s_0 + b)}}$$

$$\boxed{CL_s = \frac{CL_{s+b}}{CL_b} = \frac{P(t \geq t_{\text{obs}} | s+b)}{P(t \geq t_{\text{obs}} | b\text{-only})}}$$

$$\boxed{CL_s(\mu_{\text{upper}}) = 0.05 \quad \Longrightarrow \quad \sigma_{\text{upper}} = \mu_{\text{upper}} \times \sigma_{\text{theory}}}$$

$$\boxed{Z_{\text{Asimov}} = \sqrt{2\left[(s+b)\ln\left(1+\frac{s}{b}\right) - s\right]}}$$

---

## 부록 B: 다른 학생에게 설명할 때의 핵심 포인트

1. **"왜 단순히 $N_{\text{obs}} > b$인지 보면 안 되나요?"** → Poisson fluctuation 때문. $b = 100$이어도 $N_{\text{obs}} = 110$이 나올 확률은 상당하다. 통계적으로 정량화해야 한다.
    
2. **"$CL_{s+b}$만 쓰면 안 되나요?"** → Background가 downward fluctuation하면, sensitivity 없는 signal도 배제해버린다. $CL_b$로 나누는 것이 이에 대한 보호장치.
    
3. **"Toy MC를 왜 돌리나요? 공식으로 계산하면 안 되나요?"** → 단순 Poisson이면 공식으로도 된다. 하지만 systematic uncertainty가 들어가면 analytical solution이 복잡하거나 불가능해진다. Toy가 가장 일반적이고 robust한 방법.
    
4. **"Expected limit은 뭐고, 왜 필요한가요?"** → "Signal이 없을 때 이 실험이 typical하게 설정할 수 있는 limit." 이것이 실험의 sensitivity를 정의한다. Observed limit만으로는 fluctuation인지 real effect인지 판단할 수 없다.
    
5. **"Brazil band가 뭔가요?"** → Expected limit 주변의 $\pm 1\sigma$, $\pm 2\sigma$ 변동 범위. Observed limit이 이 band 안에 있으면 "background-only와 호환," 밖에 있으면 "뭔가 있거나, 뭔가 잘못됐거나."
    
6. **"Discovery reach (5σ line)는 어떻게 계산하나요?"** → "Signal이 진짜 있다고 가정했을 때, median 실험에서 background-only를 5σ로 기각할 수 있는가?"를 묻는 것. Asimov 공식 $Z = \sqrt{2[(s+b)\ln(1+s/b)-s]}$에 $s_0$와 $b$를 넣어서 $Z \geq 5$인 영역을 찾으면 된다. Exclusion과 달리 $H_0$를 기각하는 것이고, CLs 같은 보정이 불필요하다.
    
7. **"왜 discovery line이 항상 exclusion line 위에 있나요?"** → $5\sigma$는 $1.64\sigma$ (95% CL)보다 훨씬 높은 기준이므로, 같은 signal에 대해 배제는 가능하지만 발견은 불가능한 중간 영역이 항상 존재한다. 두 선 사이가 바로 "probe는 하지만 claim은 못하는" 영역.
