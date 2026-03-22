#!/bin/bash

# 결과 저장 파일 초기화
output_file=./width_info.txt
> "$output_file"

# 1. tarball_store 디렉토리 설정
#tarball_dir_="/users/ujeon/2025-monojet/tarball_store"

#cp -r $tarball_dir_ .

tarball_dir="./tarball_store_signal"

# 2. Signal*tar* 파일들 찾고 루프
find "$tarball_dir" -type f -name "Signal*tar*" | while read file; do

    filename=$(basename "$file")
    # 2-3. 이름을 "_" 기준으로 분할
    IFS='_' read -r part1 part2 part3 part4 rest <<< "$filename"

    # 3. var0, var1, var2 생성 (_ -> . 변환)
    var0="${part2//-/.}"
    var1="${part3//-/.}"
    var2="${part4//-/.}"

    # 4. 압축 해제 (임시 디렉토리에서)
    tmp_dir=$(mktemp -d)
    tar -xf "$file" -C "$tmp_dir"

    # 5. param_card.dat 파일 경로 설정
    param_file="$tmp_dir/madevent/Cards/param_card.dat"

    if [[ -f "$param_file" ]]; then
        # 6. width 추출 (6000001과 6000002에 대한 DECAY 값)
        wmx1=$(grep -E '^DECAY[[:space:]]+6000001' "$param_file" | awk '{print $3}')
        wmx2=$(grep -E '^DECAY[[:space:]]+6000002' "$param_file" | awk '{print $3}')

        # 7. 출력 파일에 저장
        echo "${var0},${var1},${var2},${wmx1},${wmx2}" >> "$output_file"    
        echo "${filename}: ${var0},${var1},${var2},${wmx1},${wmx2}"
    else
        echo "[WARNING] param_card.dat not found in $file" >&2
    fi

    # 8. 임시 디렉토리 정리
    rm -rf "$tmp_dir"

done

echo "[Done] All widths extracted to $output_file"
