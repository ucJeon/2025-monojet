#!/bin/bash

sample_list=(
  1-0
  1-5
  2-0
  2-5
)

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "Usage: $0 <nTree> <Depth> <version> [flag]"
  exit 1
fi

nTree=$1
Depth=$2
version=$3
flag=${4:-none}

mkdir -p ./subs

for target in "${sample_list[@]}"
do
    mkdir -p ./logs/out/${target}
    mkdir -p ./logs/log/${target}
    mkdir -p ./logs/err/${target}

    cat > "./subs/submission.sub" <<EOL
universe = vanilla
getenv = True

transfer_input_files = exe.sh,interface.py,main

executable = exe.sh

output    = ./logs/out/${target}/\$(ClusterId).\$(ProcId)
error     = ./logs/err/${target}/\$(ClusterId).\$(ProcId)
log       = ./logs/log/${target}/\$(ClusterId).\$(ProcId)

should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_output_files   = ""

request_cpus   = 1
request_memory = 10G
request_disk   = 5G

+JobBatchName = "monojet_BDTtraining"

arguments = \$(ClusterId) \$(ProcId) $target $version $nTree $Depth $flag
Requirements = (OpSysAndVer == "AlmaLinux9")
queue 1
EOL

    condor_submit "./subs/submission.sub"
done

