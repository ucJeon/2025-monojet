import pandas as pd


# ============================================================
# helpers
# ============================================================

def normalize_lam_token(x: str) -> str:
    """'0-03.0' → '0-03', '1.0' → '1' 등 trailing .0 제거."""
    x = str(x).strip()
    if x.endswith(".0"):
        x = x[:-2]
    return x


# ============================================================
# loaders
# ============================================================

def load_bkg_from_csv(version, lumi, mx1, ntree, maxdepth, base_dir) -> tuple:
    """
    BDT_cut/out/bkg_<version>_lumi<lumi>_mx1<mx1>_ntree<ntree>_maxdepth<maxdepth>.csv
    에서 TOTAL 행의 b0, sigma_b 를 읽어온다.

    Returns
    -------
    b0, sigma_b, bkg_csv_path
    """
    lumi_tag = str(float(lumi))
    bkg_csv  = (
        f"{base_dir}/bkg_{version}_lumi{lumi_tag}_mx1{mx1}_"
        f"ntree{ntree}_maxdepth{maxdepth}.csv"
    )

    df        = pd.read_csv(bkg_csv)
    total_row = df[df["sample"] == "TOTAL"]

    if len(total_row) != 1:
        raise RuntimeError(f"TOTAL row not found or duplicated in {bkg_csv}")

    b0      = float(total_row.iloc[0]["b0"])
    sigma_b = float(total_row.iloc[0]["sigmab0"])

    return b0, sigma_b, bkg_csv


def load_signal_from_csv(version, lumi, mx1, ntree, maxdepth,
                         lam1, lam2, base_dir) -> tuple:
    """
    BDT_cut/out/sig_<version>_lumi<lumi>_mx1<mx1>_ntree<ntree>_maxdepth<maxdepth>.csv
    에서 해당 (mx1, lam1, lam2) 시그널 행을 찾아 s0, s0_err 를 읽어온다.

    Returns
    -------
    s0, s0_err, sig_csv_path
    """
    lumi_tag = str(float(lumi))
    sig_csv  = (
        f"{base_dir}/sig_{version}_lumi{lumi_tag}_mx1{mx1}_"
        f"ntree{ntree}_maxdepth{maxdepth}.csv"
    )

    df            = pd.read_csv(sig_csv)
    target_lam1   = normalize_lam_token(lam1)
    target_lam2   = normalize_lam_token(lam2)
    df["sig_norm"] = df["signal"].astype(str).str.strip()

    matched = []
    for _, row in df.iterrows():
        parts = row["sig_norm"].split("_")
        if len(parts) != 4:
            continue
        _, f_mx1, f_lam1, f_lam2 = parts
        f_lam1 = normalize_lam_token(f_lam1)
        f_lam2 = normalize_lam_token(f_lam2)
        if f_mx1 == mx1 and f_lam1 == target_lam1 and f_lam2 == target_lam2:
            matched.append(row)

    if len(matched) != 1:
        raise RuntimeError(
            f"Signal not found or duplicated in {sig_csv}\n"
            f"  requested: mx1={mx1}, lam1={lam1}, lam2={lam2}"
        )

    row    = matched[0]
    s0     = float(row["sg after"])
    s0_err = float(row["sg after err"])

    return s0, s0_err, sig_csv


def load_full_sig_csv(version, lumi, mx1, ntree, maxdepth, base_dir) -> pd.DataFrame:
    """
    sig CSV 전체를 DataFrame으로 반환한다.
    plot/build_plane.py 에서 lam1×lam2 plane을 만들 때 사용한다.
    """
    lumi_tag = str(float(lumi))
    sig_csv  = (
        f"{base_dir}/sig_{version}_lumi{lumi_tag}_mx1{mx1}_"
        f"ntree{ntree}_maxdepth{maxdepth}.csv"
    )
    return pd.read_csv(sig_csv), sig_csv
