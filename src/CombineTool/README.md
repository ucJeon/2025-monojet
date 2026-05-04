Project-CLs/
├── data/                 # 분석용 CSV 파일 (sig_*.csv, bkg_*.csv)
├── lib/                  # CountingModel, csv_loader (이미 보유하신 코드)
├── datacards/            # 생성된 .txt 데이터카드 저장 폴더
├── outputs/              # Combine 결과물 (.root) 및 계산된 리밋 값 (.csv)
├── scripts/
│   ├── make_datacards.py # 1. CSV -> Datacard 변환기
│   ├── run_combine.py    # 2. Combine 명령어 자동 실행기
│   └── plot_limits.py    # 3. 결과 시각화 (Brazilian Band)
└── main.py               # 전체 프로세스 통합 실행 파일
