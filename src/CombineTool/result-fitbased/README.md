# HiggsCombine Tool

This directory contains the HiggsCombine setup and datacard-based limit-setting workflow for the b-associated monojet analysis.

---

## Setup

### HiggsCombine Tool Setup

`CMSSW` is required.

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_14_1_0_pre4
```

Before running HiggsCombine, the following commands are required each session:

```bash
# From the repository root
source /cvmfs/cms.cern.ch/cmsset_default.sh
# From CMSSW_14_1_0_pre4/src/
cmsenv
```

---

## Datacard Structure

### Signal Normalization

The signal is normalized to the MadGraph5 LO cross section at the reference coupling point $(\lambda_1^{\rm ref}, \lambda_2^{\rm ref}) = (0.1, 0.1)$, for each $m_{X_1}$ mass point.

The datacard `rate` for signal is:

$$\mathrm{rate~sig} = \sigma_{\mathrm{ref}} \times \mathcal{L} \times 1000 \times \varepsilon_{\mathrm{ref}}$$

where:

- $\sigma_{\rm ref} = \sigma(\lambda_1^{\rm ref}, \lambda_2^{\rm ref})$ [pb] — from `src/23.XS-2Dplot/cross_sections.csv`
- $\mathcal{L}$ ($\mathrm{fb}^{-1}$) — target integrated luminosity (300 or 3000)
- $\varepsilon_{\rm ref} = \varepsilon_{\rm sel} \times \varepsilon_{\rm BDT}$ — combined selection and BDT efficiency at the reference point

The input cross sections at the reference point $(\lambda_1, \lambda_2) = (0.1, 0.1)$ are:

|$m_{X_1}$ [TeV]|$\sigma_{\rm ref}$ [pb]|$\varepsilon_{\rm ref}$|`rate_sig` ($\mathcal{L}=300~\mathrm{fb}^{-1}$)|
|:-:|:-:|:-:|-:|
|1.0|1.1688e-02|0.1323|463.8095|
|1.5|1.6016e-03|0.1198|57.5397|
|2.0|3.2885e-04|0.1322|13.0420|
|2.5|8.1617e-05|0.1374|3.3636|

> **Note**: `rate_sig` values are computed from `cross_section_SG.csv` and `efficiency_SG.csv`. See `src/23.XS-2Dplot/` and `src/Efficiency-signal/` for the full tables.

The datacard format (example: Run3, $m_{X_1}=1.0$ TeV, `stats` mode) is:

```
imax 1  number of channels
jmax 1  number of backgrounds
kmax *
----------------------------------------------------------------------
bin          bin1
observation  -1
----------------------------------------------------------------------
bin                      bin1                bin1
process                  sig                 bkg
process                  0                   1
rate                     4638.0954           46929.5125
----------------------------------------------------------------------
# signal normalized to xs_ref=... pb at (lam1=0.1, lam2=0.1), L=300 fb-1, eps_ref=...
stat_bkg        lnN     -                   1.0120
```

> `observation -1` instructs Combine to use a pre-fit Asimov dataset ($n_{\rm obs} = b_0$), ensuring a fully blind analysis.

### Systematic Uncertainty Modes

|Mode|Applied Uncertainties|
|---|---|
|`none`|None|
|`stats`|BKG statistical (lnN)|
|`sys1`|stats + signal XSEC 10% (lnN)|
|`sys2`|sys1 + JES 5% (sig+bkg, lnN)|
|`sys3`|sys2 + MET 4% (sig+bkg, lnN)|

Datacards for all modes are in `datacards/`.

---

## Running AsymptoticLimits

### Blind Analysis

This analysis uses a **fully blind** setup:

- `observation -1` in the datacard (Asimov: $n_{\rm obs} = b_0$, pre-fit)
- `--run blind` in Combine (enforces pre-fit Asimov, no fit to data)

> **Why `--run blind` and not `--run expected`?** `--run expected` performs a background-only fit to data first, then uses the post-fit state as Asimov — this is **not fully blind**. `--run blind` uses the pre-fit model directly. See: https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/part5/longexerciseanswers/#b-running-combine-for-a-blind-analysis

The command to run AsymptoticLimits for a single datacard is:

```bash
combine -M AsymptoticLimits \
    ./datacards/datacard_lumi300_mx11-0_cut0p1050_stats.txt \
    -n .Lumi300.MX10.stats \
    -m 1000 \
    --run blind
```

To run all mass points, luminosity scenarios, and systematic modes:

```bash
for lumi in 300 3000; do
  for mode in none stats sys1 sys2 sys3; do
    combine -M AsymptoticLimits \
        ./datacards/datacard_lumi${lumi}_mx11-0_cut0p1050_${mode}.txt \
        -n .Lumi${lumi}.MX10.${mode} -m 1000 --run blind
    combine -M AsymptoticLimits \
        ./datacards/datacard_lumi${lumi}_mx11-5_cut0p1350_${mode}.txt \
        -n .Lumi${lumi}.MX15.${mode} -m 1500 --run blind
    combine -M AsymptoticLimits \
        ./datacards/datacard_lumi${lumi}_mx12-0_cut0p1440_${mode}.txt \
        -n .Lumi${lumi}.MX20.${mode} -m 2000 --run blind
    combine -M AsymptoticLimits \
        ./datacards/datacard_lumi${lumi}_mx12-5_cut0p1520_${mode}.txt \
        -n .Lumi${lumi}.MX25.${mode} -m 2500 --run blind
  done
done
```

> The corresponding shell script is `run_asymptotic_w-blind_card-all.sh`.

Each run produces an output ROOT file:

```
higgsCombine.Lumi{L}.MX{mx}.{mode}.AsymptoticLimits.mH{mh}.root
```

and prints the expected upper limits on the signal strength $r$:

```
Expected  2.5%: r < 0.2031
Expected 16.0%: r < 0.2699
Expected 50.0%: r < 0.3740   ← median expected, used for exclusion
Expected 84.0%: r < 0.5201
Expected 97.5%: r < 0.6913
```

The **median expected** (`Expected 50.0%`) $r$-value is used as the primary result.

Summary of median expected $r$ values for $\mathcal{L} = 300$ fb$^{-1}$:

|$m_{X_1}$ [TeV]|none|stats|sys1|sys2|sys3|
|:-:|:-:|:-:|:-:|:-:|:-:|
|1.0|0.2920|0.3740|0.3809|1.1055|1.3984|
|1.5|0.8086|0.9375|0.9531|1.3672|1.5859|
|2.0|2.0078|2.2891|2.3203|2.6953|2.9141|
|2.5|4.6094|5.1094|5.2031|5.5312|5.7344|

---

## Analysis

All analysis scripts are in `./result-fitbased/`.

### Step 1 — r-value extraction

Parse $r_{\rm up}$ (all 5 quantiles) from the ROOT output files and compute the 95% CL excluded signal yield $N_{\rm exc}$:

```bash
python3 result-fitbased/parse_results-xsfit.py
```

This script reads `outputs-xsfit/*.root` and produces `results-xsfit.csv` with columns:

|Column|Description|
|---|---|
|`mx1, lumi, mode`|Identifiers|
|`xs_ref, eff_ref, rate_sig_ref`|Reference point values|
|`r_exp_m2s, r_exp_m1s, r_exp_med, r_exp_p1s, r_exp_p2s`|Quantile $r$-values|
|`N_exc_exp_med`|$N_{\rm exc} = r_{\rm up}^{\rm med} \times \sigma_{\rm ref} \times \mathcal{L} \times 1000 \times \varepsilon_{\rm ref}$|

---

### Step 2 — Exclusion Contour (XS-fit based)

```bash
python3 result-fitbased/plot_contour_fitbased.py
```

#### Why XS-fit based (not yield-spline)?

The previous approach interpolated $N_s(\lambda_1, \lambda_2)$ directly with a cubic spline, which caused **wriggle artifacts** in the exclusion contour because $\sigma_{\rm th} \propto \lambda_1^n \lambda_2^m$ is highly nonlinear on a sparse grid.

The XS-fit based approach separates the two contributions:

- $\sigma(\lambda_1, \lambda_2)$ — analytic and smooth (known from theory)
- $\varepsilon(\lambda_1, \lambda_2)$ — smooth 2D spline (geometrically varies slowly)

This yields a smooth, artifact-free contour at arbitrary resolution.

#### Exclusion condition

The 95% CL excluded signal yield at the reference point is:

$$N_{\rm exc} = r_{\rm up}^{\rm med} \times \sigma_{\rm ref} \times \mathcal{L} \times 1000 \times \varepsilon_{\rm ref}$$

A coupling point $(\lambda_1, \lambda_2)$ is **excluded** when:

$$\sigma(\lambda_1, \lambda_2) \times \varepsilon(\lambda_1, \lambda_2) \times \mathcal{L} \times 1000 > N_{\rm exc}$$

The exclusion boundary (contour) is the equality condition.

#### Cross-section parametrization

$$\sigma(\lambda_1, \lambda_2) = \frac{A \cdot \lambda_1^2 \cdot \lambda_2^2}{4.0 \cdot \lambda_1^2 + \lambda_2^2}$$

$A$ is determined per $m_{X_1}$ by iterative fitting to MG5 LO values (threshold 10%):

|$m_{X_1}$ [TeV]|$A$|
|:-:|:-:|
|1.0|5.4682|
|1.5|0.81048|
|2.0|0.16842|
|2.5|0.042582|

#### Efficiency interpolation

```python
from scipy.interpolate import RectBivariateSpline
spline = RectBivariateSpline(lam1_vals, lam2_vals, eff_matrix, kx=3, ky=3)
```

BDT cut values per $m_{X_1}$:

|$m_{X_1}$ [TeV]|BDT cut|
|:-:|:-:|
|1.0|0.105|
|1.5|0.135|
|2.0|0.144|
|2.5|0.152|

Output plots are saved to `result-fitbased/plots/contour_lumi{L}_{mode}_{log|lin}.pdf`.

---

### Step 3 — Critical Coupling Values

To quote a single number per mass point, 1D slices through the contour are taken by fixing one coupling at $\lambda = 0.5$ and solving for the critical value of the other.

Example for $\mathcal{L} = 300$ fb$^{-1}$, `stats` mode:

|$m_{X_1}$ [TeV]|$\lambda_1^{\rm crit}$ (fixed $\lambda_2=0.5$)|$\lambda_2^{\rm crit}$ (fixed $\lambda_1=0.5$)|
|:-:|:-:|:-:|
|1.0|<0.03|0.054|
|1.5|0.043|0.088|
|2.0|0.072|0.139|
|2.5|0.109|0.204|

Full results across all luminosity and systematic scenarios are in `result-fitbased/lam_crit_summary.csv`.

Critical $\lambda_2$ values as systematic uncertainties are added incrementally ($\mathcal{L} = 300$ fb$^{-1}$):

|Uncertainty|1.0 TeV|1.5 TeV|2.0 TeV|2.5 TeV|
|---|:-:|:-:|:-:|:-:|
|stats only|<0.05|<0.09|<0.14|<0.20|
|stats + xsec (10%)|<0.05|<0.09|<0.14|<0.21|
|stats + xsec + JES (5%)|<0.10|<0.11|<0.15|<0.21|
|stats + xsec + JES + MET (4%)|<0.11|<0.11|<0.16|<0.22|

---

### Ordering Independence

Systematic uncertainties were added in two orderings to verify that the final limits are independent of the order in which they are introduced (intermediate values may differ):

**Order 1**: stats → xsec → JES → MET

|Uncertainty|1.0 TeV|1.5 TeV|2.0 TeV|2.5 TeV|
|---|:-:|:-:|:-:|:-:|
|stats only|<0.05|<0.09|<0.14|<0.20|
|stats + xsec (10%)|<0.05|<0.09|<0.14|<0.21|
|stats + xsec + JES (5%)|<0.10|<0.11|<0.15|<0.21|
|stats + xsec + JES + MET (4%)|<0.11|<0.11|<0.16|<0.22|

**Order 2**: stats → MET → JES → xsec

|Uncertainty|1.0 TeV|1.5 TeV|2.0 TeV|2.5 TeV|
|---|:-:|:-:|:-:|:-:|
|stats only|<0.05|<0.09|<0.14|<0.20|
|stats + MET (4%)|<0.09|<0.10|<0.15|<0.21|
|stats + MET + JES (5%)|<0.11|<0.11|<0.16|<0.21|
|stats + MET + JES + xsec (10%)|<0.11|<0.11|<0.16|<0.22|

Final limits agree between orderings. ✅

---

## Directory Structure

```
CombineTool/
├── README.md                        # this file
├── run_asymptotic_w-blind_card-all.sh   # blind analysis run script
├── datacards/                       # input datacards (observation=-1)
│   └── datacard_lumi{L}_mx1{mx}.{cut}_{mode}.txt
├── outputs-xsfit/                   # Combine ROOT output files
│   └── higgsCombine.Lumi{L}.MX{mx}.{mode}.*.root
└── result-fitbased/                 # XS-fit based analysis
    ├── parse_results-xsfit.py       # Step 1: r_up extraction
    ├── plot_contour_fitbased.py     # Step 2: contour plotting
    ├── results-xsfit.csv            # r_up and N_exc per scenario
    ├── lam_crit_summary.csv         # critical lambda values
    └── plots/
        ├── contour_lumi{L}_{mode}_log.pdf
        ├── contour_lumi{L}_{mode}_lin.pdf
        └── eff_slices_all.pdf
```

---

## References

- HiggsAnalysis-CombinedLimit: https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/
- Blind analysis: https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/part5/longexerciseanswers/#b-running-combine-for-a-blind-analysis
- Asymptotic formulae: Cowan et al., Eur.Phys.J. C71 (2011) 1554, [arXiv:1007.1727](https://arxiv.org/abs/1007.1727)
- Signal cross sections: `src/23.XS-2Dplot/cross_section_SG.csv`
- Signal efficiency: `src/Efficiency-signal/efficiency_SG.csv`
