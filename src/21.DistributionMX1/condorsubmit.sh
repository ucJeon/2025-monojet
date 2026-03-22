#!/bin/bash

# 폴더 리스트
list=(
    /hdfs/user/ujeon/monojet/mc/v1.0.0/
  )

# 리스트 출력
echo "Input folders information: "
for folder in "${list[@]}"; do
  echo "$folder"
done

read -p "Do you put the jobs for the inputs? (y/n): " answer

# 입력값에 따라 처리
if [[ "$answer" == "y" ]]; then
    echo "Job submitting..."
    # 여기에 잡을 던지는 명령어를 추가
elif [[ "$answer" == "n" ]]; then
    echo "Cancel submitting jobs."
else
    echo "Not valid input, try again."
fi

# 폴더별 파일 리스트 저장
declare -A file_lists

for folder in "${list[@]}"
do
    # 해당 폴더에 있는 파일 목록 중 Signal_로 시작하는 파일만 저장
    files=$(ls "$folder" | grep '^Signal_')
    file_lists["$folder"]="$files"
done

for folder in "${!file_lists[@]}" # 어차피 하나임
do
    # 1. file_lists[$folder] 에서 Signal_ 이 포함된 파일만 필터링하여 files_array에 저장
    filtered_files=""
    for file in ${file_lists["$folder"]}; do
        if [[ "$file" == Signal_* ]]; then
            filtered_files+="$file "
        fi
    done

    # 2. IFS를 이용해 배열로 변환
    IFS=' ' read -r -a files_array <<< "$filtered_files"

    # 3. JOB_NAME 정의 (예시: 폴더 이름에서 마지막 디렉토리만 사용)
    JOB_NAME="MonojetDistributionMX1"

    # 4. .sub 파일 생성
    mkdir -p "./logs/out/${JOB_NAME}" "./logs/err/${JOB_NAME}" "./logs/log/${JOB_NAME}"

    cat > "${JOB_NAME}.sub" <<EOL
universe = vanilla

getenv = True

transfer_input_files = toCondor/

executable = exe.sh

output    = ./logs/out/${JOB_NAME}/\$(ClusterId).\$(ProcId)
error     = ./logs/err/${JOB_NAME}/\$(ClusterId).\$(ProcId)
log       = ./logs/log/${JOB_NAME}/\$(ClusterId).\$(ProcId)

should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_output_files   = ""

request_cpus   = 1
request_memory = 5G
request_disk   = 10G

+JobBatchName = "$JOB_NAME"
EOL
    for index in "${!files_array[@]}"
    do
        # 파일명만 추출 (경로 제거)
        file="${files_array[index]}"
        name="${file##*/}"
                # 파일명 파싱: Signal_1-5_0-1_0-1.0.1.root 이때 가운데 0은 항상 0
        if [[ $name =~ ^Signal_([^_]+)_([^_]+)_([^.]+)\.0\.([^.]+)\.root$ ]]; then
          mx1="${BASH_REMATCH[1]}"
          lam1="${BASH_REMATCH[2]}"
          lam2="${BASH_REMATCH[3]}"
          prc="${BASH_REMATCH[4]}"
          echo $file $mx1 $lam1 $lam2 $prc
        else
          # 컨벤션에 맞지 않으면 스킵
          continue
        fi

        # lam1 / lam2 허용값 필터
        #if [[ ! "$lam1" =~ ^(0-08|0-1|0-5|1-0|2-0)$ ]]; then
        #if [[ ! "$lam1" =~ ^(0-08|0-1|0-3|0-5|0-6|0-7|0-8|0-9|1-0|2-0)$ ]]; then
        if [[ ! "$lam1" =~ ^(0-3)$ ]]; then
          continue
        fi
        #if [[ ! "$lam2" =~ ^(0-08|0-1|0-3|0-5|0-6|0-7|0-8|0-9|1-0|2-0)$ ]]; then
        if [[ ! "$lam2" =~ ^(2-0)$ ]]; then
        #if [[ ! "$lam2" =~ ^(0-08|0-1|0-5|1-0|2-0)$ ]]; then
          continue
        fi

        # prc 숫자 비교: 숫자(정수/소수)만 허용, 5보다 크면 스킵
        if [[ "$prc" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
          awk -v a="$prc" 'BEGIN{exit (a<=5?0:1)}' || continue
        else
          # 숫자가 아니면 스킵 (원하면 여기서 허용해도 됨)
          continue
        fi
        echo "passed"
        cat >> "${JOB_NAME}.sub" <<EOL
arguments = \$(ClusterId) \$(ProcId) $file
Requirements = (OpSysAndVer == "AlmaLinux9")
queue 1
EOL
    done
    condor_submit "${JOB_NAME}.sub"
done
