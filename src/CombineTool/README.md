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
- (2) and make root file names `higgsCombine.Lumi300.MX10.stats.AsymptoticLimits.mH1000.root`
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
Following procedure, the root file is used for getting r-value

If use `observed` run mode instead of `expected` run mode, you can see the observed r value as
```
Observed Limit: r < 0.3749
```
with `run_asymptotic_w-observed_card-all.sh` run script

## Analysis
It is performed in the `./result` folder.

