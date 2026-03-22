#!/usr/bin/env python3
# txt_to_sorted_csv.py

import csv
import sys
from pathlib import Path

def fix_lam2(lam2_raw: str) -> str:
    s = lam2_raw.strip()
    parts = s.split(".")
    if len(parts) >= 3:
        s2 = ".".join(parts[:-1])
        return s2 if s2 else s
    return s

def to_float_safe(x: str) -> float:
    return float(x.strip())

def fmt_num(x: float) -> str:
    # "1.0", "0.03" 같은 형태를 최대한 자연스럽게
    return f"{x:.15g}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 txt_to_sorted_csv.py input.txt [output.csv]")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else in_path.with_suffix(".csv")

    rows = []
    with in_path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 5:
                raise ValueError(f"[line {ln}] Expected 5 comma-separated fields, got {len(parts)}: {line}")

            mx1_s, lam1_s, lam2_raw, width_s, widtherr_s = parts
            lam2_s = fix_lam2(lam2_raw)

            mx1 = to_float_safe(mx1_s)
            lam1 = to_float_safe(lam1_s)
            lam2 = to_float_safe(lam2_s)

            rows.append({
                "mx1": mx1, "lam1": lam1, "lam2": lam2,
                "width_s": width_s, "widtherr_s": widtherr_s,
            })

    # 정렬: mx1mass -> lam1 -> lam2
    rows.sort(key=lambda r: (r["mx1"], r["lam1"], r["lam2"]))

    with out_path.open("w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(["mx1mass", "lam1", "lam2", "width", "width_err"])
        for r in rows:
            w.writerow([
                fmt_num(r["mx1"]),
                fmt_num(r["lam1"]),
                fmt_num(r["lam2"]),
                r["width_s"],
                r["widtherr_s"],
            ])

    print(f"Wrote: {out_path}")

if __name__ == "__main__":
    main()
