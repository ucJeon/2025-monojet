# Higgs Combine Tool
This directory contains the HiggsCombine setup and datacard-based limit-setting workflow.

## Setup

### HiggsCombine Tool Setup

`CMSSW` is needed for this task.
```
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_14_1_0_pre4
```

before running `HiggsCombine` tools, below commands are required.
```
# At current directory
source /cvmfs/cms.cern.ch/cmsset_default.sh
# At ./CMSSW_14_1_0_pre4/src
cmsenv
```

## Running AsymptoticLimits

Run `run_asymptotic_card-all.sh` to compute AsymptoticLimits and obtain the expected upper limit on the signal strength r.

For example, to obtain the r-value upper limit for MX1 = 1.0 TeV with statistical uncertainty only:
```
lumi=300 # Run3, 300 fb-1
mode=stats # statistical uncertainty as gaussian constraint with log-normal are applied
DC="./datacards/datacard_lumi${lumi}_mx11-0_cut${c10}_${mode}.txt"
echo "[RUN] ${DC}"
combine -M AsymptoticLimits $DC \
    -n .Lumi${lumi}.MX10.${mode} \
    -m 1000 \ # mX1 = 1.0 TeV = 1000 GeV, just for root file prefix
    --run expected
```
For the `$mode` are considered as
- none : without statistical uncertainties 
- stats : with statistical uncertainties 
- sys1 : + 10% signal cross-section uncertainty for signal side
- sys2 : + 5% JES uncertainties for signal and background both side
- sys3 : + 4% MET uncertainties for signal and background both side
In detail, you can check the modes in the folder `datacards`

The datacard referenced by $DC in the example above has the following format (Run3 Lumi, $m_{X_1}$=1.0TeV, mode=stats):
```
imax 1  number of channels
jmax 1  number of backgrounds
kmax *
----------------------------------------------------------------------
bin         bin1
observation 46930
----------------------------------------------------------------------
bin                      bin1                bin1                
process                  sig                 bkg                 
process                  0                   1                   
rate                     4638.0954           46929.5125          
----------------------------------------------------------------------
stat_bkg        lnN     -                   1.0120
```
Note that if the line `observation 46930` is omitted in the `datacard` as input to Combine, you would see the warning `No observed data 'data_obs' in the workspace. Cannot compute limit.`.

As a result, 
- (1) it print-out the expected signal strength r
- (2) and make **output root file** names `higgsCombine.Lumi300.MX10.stats.AsymptoticLimits.mH1000.root`
```
=============================================================
 lumi=300  mode=stats
============================================================
[RUN] ./datacards/datacard_lumi300_mx11-0_cut0p1050_stats.txt
Expected  2.5%: r < 0.2031
Expected 16.0%: r < 0.2699
Expected 50.0%: r < 0.3740
Expected 84.0%: r < 0.5201
Expected 97.5%: r < 0.6913
```
In above, `Expected 50.0%` r-value is used for calculating the upper limit on the parameter space.
Following procedure, **the output root file** is used for getting r-value

If use `observed` run mode instead of `expected` run mode, you can see the observed r value as
```
Observed Limit: r < 0.3749
```
with `run_asymptotic_w-observed_card-all.sh` run script



## Analysis
It is performed in the `./result` folder. the results are processed by following procedures

### Step1 (`run_step1.sh`)
- `run_step1.sh` is run-script for `step1_make-table.py` which is make markdown style table.
- Make `resultcard_expected.txt` as summary table
- by parsing `median expected r` from **output root files**.
- Below tables are summary of **expected median r** for integrated luminosity=300 fb⁻¹. 

| $M_{X_1}$ [TeV] |  none  | stats  |  sys1  |  sys2  |  sys3  |
| :-------------: | :----: | :----: | :----: | :----: | :----: |
|       1.0       | 0.2920 | 0.3740 | 0.3809 | 1.1055 | 1.3984 |
|       1.5       | 0.8086 | 0.9375 | 0.9531 | 1.3672 | 1.5859 |
|       2.0       | 2.0078 | 2.2891 | 2.3203 | 2.6953 | 2.9141 |
|       2.5       | 4.6094 | 5.1094 | 5.2031 | 5.5312 | 5.7344 |

### Step2 (`run_step2.sh`)
- `run_step2.sh` is run-script for `step2_plot-expected-contour.py` which is 
- (1) print-out for $\lambda_{1}$ and $\lambda_{2}$ critical values when $\lambda_{i}$=0.5 and
- (2) make contour plots in the folder `plots_expected` varying luminosity scenarios and uncertainty mode.
- below tables are one of the example for the case of Run3 Luminosity and statistical uncertainty considered only
- below figure is contour plot for the same case.

| MX1 | lam1_crit (fixed lam2=0.5) | lam2_crit (fixed lam1=0.5) |
|---|---|---|
| 1.0 | <0.03 | 0.054 |
| 1.5 | 0.043 | 0.088 |
| 2.0 | 0.072 | 0.139 |
| 2.5 | 0.109 | 0.204 |

[The examples contour plot mentioned](./plots_expected/limit_stats_lumi300.png)

### Converting r-value to coupling upper limit

The r-value from HiggsCombine represents the upper limit on the signal strength modifier μ.
To convert this into a coupling upper limit, the cross-section parameterization is used.

The signal rate in the datacard is generated at a reference coupling point
(λ₁_ref, λ₂_ref) = (0.5, 0.5):

$$N_s^{\rm nominal} = \sigma(\lambda_1^{\rm ref}, \lambda_2^{\rm ref}) \times \mathcal{L} \times \epsilon_s$$

The excluded cross section is:

$$\sigma^{\rm excluded} = r_{\rm up} \times \sigma(\lambda_1^{\rm ref}, \lambda_2^{\rm ref})$$

Using the parameterization $\sigma \propto |\lambda_1|^2 |\lambda_2|^2 / (4|\lambda_1|^2 + |\lambda_2|^2)$,
the upper limit on λ₂ (with λ₁ = 0.5 fixed) is obtained by solving:

$$r_{\rm up} = \frac{\sigma(\lambda_1, \lambda_2^{\rm up})}{\sigma(\lambda_1^{\rm ref}, \lambda_2^{\rm ref})} = \frac{|\lambda_2^{\rm up}|^2 (4|\lambda_1^{\rm ref}|^2 + |\lambda_2^{\rm ref}|^2)}{|\lambda_2^{\rm ref}|^2 (4|\lambda_1|^2 + |\lambda_2^{\rm up}|^2)}$$

With λ₁ = λ₁_ref = 0.5, this simplifies to:

$$r_{\rm up} = \frac{|\lambda_2^{\rm up}|^2 (1 + |\lambda_2^{\rm ref}|^2)}{|\lambda_2^{\rm ref}|^2 (1 + |\lambda_2^{\rm up}|^2)}$$

This is solved numerically for λ₂_up.

### Running the conversion

```bash
cd result/
python run_limit.py --lumi 300 --lam1_ref 0.5 --lam2_ref 0.5
```

This script:
1. Reads r-values from the root files produced by `combine`
2. Solves the above equation numerically for each mass point
3. Outputs the λ₂ upper limit table

### Output format

```
## Summary: lumi=300 fb⁻¹ (λ₁ = 0.5 fixed)
| Uncertainty | 1.0 TeV | 1.5 TeV | 2.0 TeV | 2.5 TeV |
|---|---|---|---|---|
| stats only | < 0.054 | < 0.088 | < 0.14 | < 0.20 |
```

### Consistency checks

**Luminosity scaling (stats-limited regime):**

$$\frac{r_{\rm up}(3000)}{r_{\rm up}(300)} \approx \frac{1}{\sqrt{10}} \approx 0.316$$

Equivalently in coupling space:

$$\frac{\lambda_2^{\rm up}(3000)}{\lambda_2^{\rm up}(300)} \approx 10^{-1/8} \approx 0.75$$

Verification at 2.5 TeV: 0.20 × 0.75 = 0.15, observed 0.14. Consistent.

**Ordering independence:**

Systematic uncertainties are added in two orderings:
- Order 1: stats → xsec → JES → MET
- Order 2: stats → MET → JES → xsec

Final limits must agree. Intermediate values may differ.

### File structure

```
result/
├── run_limit.py              # r-value → λ₂ conversion
├── resultcard_expected.txt    # summary of r-values (expected)
├── 26.04.26-limit.md          # systematic impact report
└── plots/
    └── limit/
        ├── limit-300-log.jpeg
        └── limit-3000-log.jpeg
```
