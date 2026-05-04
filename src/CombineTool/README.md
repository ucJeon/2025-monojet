# Higgs Combine Tool
this directory 

## HiggsCombine Tool Setup

`CMSSW` is needed for this tasks.
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

## 

Run `run_asymptotic_card-all.sh` to make output of AsymptoticLimits for getting upperlimit

For example, for the case of getting r value of mx1, stats only
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

where datacards for `$DC` in above codes is
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

