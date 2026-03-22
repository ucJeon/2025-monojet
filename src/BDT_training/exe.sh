#!/bin/sh
export exe_name=$0
export cluster=$1
export process=$2
export target_input=$3
export version=$4
export nTree=$5
export Depth=$6
export flag=$7

export resultDir="/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/BDT_training/results/"
if [ "$flag" = "none" ]; then
  export storeDir="${resultDir}MX1${target_input}_nTree${nTree}_maxDepth${Depth}_${version}/"
else
  export storeDir="${resultDir}MX1${target_input}_nTree${nTree}_maxDepth${Depth}_${flag}_${version}/"
fi
mkdir -p $storeDir

echo " ================= step: 0 ================= "
echo " =========================================== "
mkdir -p outputs

current_dir=$PWD
echo $current_dir
echo "target_input = $target_input"
echo "version      = $version"
echo "nTree        = $nTree"
echo "Depth        = $Depth"
echo "flag         = $flag"
echo "storeDir     = $storeDir"

python3 interface.py $target_input $version $nTree $Depth $flag $storeDir

cp TMVA_output.root $storeDir 2>/dev/null
cp -r ./dataset $storeDir 2>/dev/null
cp -r ./_condor_stdout $storeDir 2>/dev/null
cp -r ./_condor_stderr $storeDir 2>/dev/null
