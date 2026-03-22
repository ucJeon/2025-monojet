import numpy as np
import glob
import os

def files_from_dir(base_dir, pattern):
    """ base_dir 디렉토리 내에서 주어진 패턴에 매칭되는 모든 파일 경로를 리스트로 반환합니다. """
    search_path = os.path.join(base_dir, pattern)
    files = glob.glob(search_path)
    return files

def info_from_line(line):
    temp_1 = line.strip().split()
    if len(temp_1) < 8:
        return None, None, None  # 너무 짧은 줄은 무시
    xsec_mb = float(temp_1[5])
    xsec_err = float(temp_1[7])
    sample_name = temp_1[1].rstrip(':')
    return sample_name, xsec_mb, xsec_err

def line_from_file(file):
    with open(file, "r") as file_:
        lines = file_.readlines()
    return lines

# 문제의 라인을 저장할 리스트
invalid_lines_all = []

def complete_from_info(file):
    lines = line_from_file(file)
    xsecs = []
    xsecsErr = []
    sample_info = None
    invalid_lines = []

    for line in lines:
        if "Inclusive cross section" not in line:
            continue

        temp_1 = line.strip().split()
        if len(temp_1) < 8:
            invalid_lines.append(line.strip())
            continue

        try:
            sample_name, xsec, xsec_err = info_from_line(line)
            if sample_info is None:
                sample_info = sample_name
            if xsec is not None and xsec_err is not None:
                xsecs.append(xsec)
                xsecsErr.append(xsec_err)
        except Exception as e:
            print(f"⚠️  Parsing error on line: {line.strip()} — {e}")
            invalid_lines.append(line.strip())

    # 전역 리스트에 문제 라인 추가
    invalid_lines_all.extend([f"{file}: {l}" for l in invalid_lines])

    if not xsecs or not xsecsErr:
        raise ValueError(f"No valid cross section info found in {file}")

    weights = 1 / np.square(xsecsErr)
    xsec_weighted = np.average(xsecs, weights=weights)
    xsecErr_weighted = 1 / np.sqrt(np.sum(weights))

    return sample_info, xsec_weighted, xsecErr_weighted

# 결과 CSV 초기화
output_csv = "cross_sections.csv"
with open(output_csv, "w") as f:
    f.write("sample, xsec [pb], xsec_err [pb]\n")

#base_dir = "/users/ujeon/2025-monojet/condor/2.StoreHepMC"
import sys
base_dir = sys.argv[1]
for file in files_from_dir(base_dir, "*xSecs.txt"):
    try:
        sample_info, xsec_weighted, xsecErr_weighted = complete_from_info(file)
        pb_xsec = xsec_weighted * 1e9  # mb → pb
        pb_xsecErr = xsecErr_weighted * 1e9
        with open(output_csv, "a") as f:
            f.write(f"{sample_info}, {pb_xsec}, {pb_xsecErr}\n")
    except Exception as e:
        print(f"❌ Error processing {file}: {e}")

# 문제 있는 라인들을 따로 저장
if invalid_lines_all:
    with open("invalid_lines.txt", "w") as f:
        f.write("다음 라인들은 필드가 부족하여 무시되었습니다:\n\n")
        for line in invalid_lines_all:
            f.write(f"{line}\n")

print("✅ 작업 완료. 잘못된 라인은 invalid_lines.txt에 저장되었습니다.")
