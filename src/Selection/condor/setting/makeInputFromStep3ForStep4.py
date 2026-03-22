import os
import sys

# parent_folder 내의 유일한 폴더 찾기
parent_folder = "/users/ujeon/2025-monojet/condor/3.DelphesStep/outputs/v1_store"
subfolders = [f.path for f in os.scandir(parent_folder) if f.is_dir()]

print("###################################################################")
print("#              GenHisto 작업을 위한 Input 파일 생성                    #")
print("#-----------------------------------------------------------------#")
print("# 이 스크립트는 GenSample의 output 정보를 바탕으로                        #")
print("# GenHisto 작업을 위한 Input 파일들을 자동으로 생성합니다.                  #")
print("# 실행 전에 관련 디렉토리가 올바르게 설정되어 있는지 확인하세요.                 #")
print("#                                                                 #")
print("#  ⚠️ 주의: 필수 입력 파일이 누락되지 않았는지 반드시 점검하세요!               #")
print("###################################################################")

for target_folder in subfolders:  # 예: monotop.wjets_lv.EventGenerate.173685
    try:
        parts = target_folder.split(".")
        if len(parts) < 4:
            print(f"⚠️ 경고: 폴더 이름이 예상과 다릅니다. ({target_folder}) → 건너뜀")
            continue  # 다음 폴더로 넘어감

        target1 = parts[2]  # wjets_lv
        target2 = parts[3]  # EventGenerate 같은 값
        target = f"{target1}.{target2}"

        files = os.listdir(target_folder)
        if not files:
            print(f"⚠️ 경고: {target_folder} 안에 파일이 없습니다. → 건너뜀")
            continue

        data_list = []
        for i, var in enumerate(files):
            parts = var.split(".")
            if len(parts) < 4:
                print(f"⚠️ 파일명 오류: {var} → 건너뜀")
                continue

            job = parts[3]  # GenHisto_95
            if "_" not in job:
                print(f"⚠️ 경고: 예상과 다른 파일명 ({var}) → 건너뜀")
                continue

            idx = job.split("_")[1]  # 95

            file_path = os.path.join(target_folder, var)
            if not os.path.exists(file_path):
                print(f"⚠️ 파일 없음: {file_path} → 건너뜀")
                continue

            with open(file_path, "r", encoding="utf-8") as file:
                line = file.read().strip()
                values = line.split(",")  # 쉼표 기준 분할
                filtered_values1 = [value for value in values[1:] if "kcms" in value]
                filtered_values2 = [value for value in values[1:] if "dn" in value]
                if len(filtered_values1) < len(filtered_values2):
                    filtered_values = filtered_values2
                elif len(filtered_values1) > len(filtered_values2):
                    filtered_values = filtered_values1

                values = [values[0]] + filtered_values

                if len(values) < 2:
                    print(f"⚠️ 파일 형식 오류: {file_path} → 건너뜀")
                    continue

                target_file_name = values[0]  # 예: ttbar.1.0.root
                target_idx = target_file_name.split(".")[2]

                values.insert(0, int(target_idx))
                data_list.append(values)

        if not data_list:
            print(f"⚠️ {target_folder}에서 유효한 데이터가 없습니다. → 건너뜀")
            continue

        # 첫 번째 요소(숫자)를 기준으로 정렬
        data_list.sort(key=lambda x: x[0])
        data_list = [[var[1], var[2]] for var in data_list]

        # 정렬된 데이터를 파일로 저장
        output_file = os.path.join("/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/inputs", f"inputs.monojetSelectionDiet.{target}.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            for row in data_list:
                f.write(",".join(map(str, row)) + "\n")
        print(f"✅ 파일 저장 완료: {output_file}")

    except Exception as e:
        print(f"❌ 오류 발생: {e} → {target_folder} 건너뜀")
