import numpy as np
import glob
import os

def files_from_dir(base_dir, pattern):
    """
    base_dir 디렉토리 내에서 주어진 패턴에 매칭되는 모든 파일 경로를 리스트로 반환합니다.
    예: pattern = "Signal*.txt"
    """
    search_path = os.path.join(base_dir, pattern)
    files = glob.glob(search_path)
    return files

def info_from_line(line):
    temp_1 = line.strip().split()
    if len(temp_1) < 8:
        return None, None, None  # 혹은 continue 처리
    xsec_mb = float(temp_1[5])
    xsec_err = float(temp_1[7])
    sample_name = temp_1[1].rstrip(':')
    return sample_name, xsec_mb, xsec_err

def line_from_file(file):
    with open(file, "r") as file_: 
        lines = file_.readlines()
    return lines

def complete_from_info(file):
    lines = line_from_file(file)
    xsecs = []
    xsecsErr = []
    sample_info = None

    for line in lines:
        sample_name, xsec, xsec_err = info_from_line(line)
        if sample_info == None:
            sample_info = sample_name
        xsecs.append(xsec)
        xsecsErr.append(xsec_err)
    xsecs=np.array(xsecs)
    xsecsErr=np.array(xsecsErr)

    weights = 1/xsecsErr**2
    xsec_weighted = np.sum(weights * xsecs) / np.sum(weights)
    xsecErr_weighted = np.sqrt(1 / np.sum(weights))

    return sample_info, xsec_weighted, xsecErr_weighted

def complete_from_info(filepath):
    xsecs = []
    xsecsErr = []
    sample_info = None

    with open(filepath, 'r') as f:
        for line in f:
            if "Inclusive cross section" not in line:
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
                continue

    if not xsecs or not xsecsErr:
        raise ValueError(f"No valid cross section info found in {filepath}")

    import numpy as np
    weights = 1 / np.square(xsecsErr)
    xsec_weighted = np.average(xsecs, weights=weights)
    xsecErr_weighted = (1 / np.sqrt(np.sum(weights)))

    return sample_info, xsec_weighted, xsecErr_weighted

output_csv = "cross_sections.csv"
with open(output_csv, "w") as f:
    f.write("sample, xsec [pb], xsec_err [pb]\n")

base_dir="/users/ujeon/2025-monojet/condor/2.StoreHepMC"
for file in files_from_dir(base_dir, "*xSecs.txt"):
    sample_info, xsec_weighted, xsecErr_weighted = complete_from_info(file)
    pb_xsec   = xsec_weighted    * 10e+9
    pb_xsecErr= xsecErr_weighted * 10e+9
    output_csv = "cross_sections.csv"

    # 1. 파일 새로 만들고 헤더 작성 (처음 한 번만 실행)
    with open(output_csv, "a") as f:
        f.write(f"{sample_info}, {pb_xsec}, {pb_xsecErr}\n")

