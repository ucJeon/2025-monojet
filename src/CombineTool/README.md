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
For example, 
```bash
DC="./datacards/datacard_lumi${lumi}_mx11-0_cut${c10}_${mode}.txt"
echo "[RUN] ${DC}"
combine -M AsymptoticLimits $DC \
    -n .Lumi${lumi}.MX10.${mode} \
    -m 1000 \
    --run expected \
    | grep -E "Expected|Observed"
```
