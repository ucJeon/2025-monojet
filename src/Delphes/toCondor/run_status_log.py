#!/usr/bin/env python3
# ==============================================================
# run_status_log.py
# Case 2,4,5,6,7,8 (및 12,14,15,16,17,18) - 로그만
# ==============================================================

import argparse


MESSAGES = {
    2:  ("[SKIP]  ", "입력 정상, 출력 정상 → 완료된 파일, 스킵"),
    4:  ("[ERROR] ", "입력 이상, 출력 없음 → 입력 파일 깨짐"),
    5:  ("[WARN]  ", "입력 이상, 출력 있음 → 입력 깨졌지만 출력 존재"),
    6:  ("[ERROR] ", "입력 없음, 출력 없음 → 입력 파일 자체 없음"),
    7:  ("[WARN]  ", "입력 없음, 출력 있음 → orphan output"),
    8:  ("[WARN]  ", "입력 없음, 출력 이상 → orphan + 출력 깨짐"),
    12: ("[SKIP]  ", "RF=2 입력, 출력 정상 → recopy 완료, 스킵"),
    14: ("[ERROR] ", "RF=2 입력 이상, 출력 없음 → 입력 파일 깨짐"),
    15: ("[WARN]  ", "RF=2 입력 이상, 출력 있음 → 입력 깨졌지만 출력 존재"),
    16: ("[ERROR] ", "RF=2 입력 없음, 출력 없음 → 입력 파일 자체 없음"),
    17: ("[WARN]  ", "RF=2 입력 없음, 출력 있음 → orphan output"),
    18: ("[WARN]  ", "RF=2 입력 없음, 출력 이상 → orphan + 출력 깨짐"),
}


def parse_args():
    parser = argparse.ArgumentParser(description="로그 전용 케이스 처리")
    parser.add_argument("--case",        required=True, type=int)
    parser.add_argument("--input_file",  required=True)
    parser.add_argument("--output_file", required=True)
    parser.add_argument("--process",     required=True, type=int)
    parser.add_argument("--full_target", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.case not in MESSAGES:
        print(f"[ERROR] 알 수 없는 case: {args.case}")
        raise SystemExit(1)

    level, msg = MESSAGES[args.case]
    print(f"{level} case={args.case} | {args.full_target}.{args.process}")
    print(f"         {msg}")
    print(f"         input : {args.input_file}")
    print(f"         output: {args.output_file}")
