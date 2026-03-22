#!/usr/bin/env python3
"""
main.py
-------
Usage:
  python main.py <lumi> <mx1> <lam1> <lam2> <version> <ntree> <maxdepth> [--cut CUT] [--mode asymptotic|full]

Example:
  python main.py 300 1-0 0-15 0-15 v2 2000 4 --cut 0.1300
  python main.py 300 1-0 0-15 0-15 v2 2000 4 --cut 0.1300 --mode full --ntoys 10000 --nscan 300
"""

import math
import sys
import argparse
import csv
import os
import numpy as np
import pandas as pd

from scipy import optimize
from scipy.optimize import brentq
from scipy.special import gammaln
from scipy.stats import norm

# ============================================================
# args
# ============================================================

parser = argparse.ArgumentParser()
parser.add_argument("lumi")
parser.add_argument("mx1")
parser.add_argument("lam1")
parser.add_argument("lam2")
parser.add_argument("version")
parser.add_argument("ntree")
parser.add_argument("maxdepth")
parser.add_argument("--cut",      type=float, default=None)
parser.add_argument("--mode",     choices=["asymptotic", "full"], default="asymptotic")
parser.add_argument("--ntoys",    type=int,   default=10000)
parser.add_argument("--nscan",    type=int,   default=300)
parser.add_argument("--band_toys",type=int,   default=2000,
                    help="full mode: toys for band calculation (default: 2000)")
parser.add_argument("--base_bdt", default=None)
parser.add_argument("--output",   default=None)
args = parser.parse_args()

lumi_arg     = args.lumi
mx1_arg      = args.mx1
lam1_arg     = args.lam1
lam2_arg     = args.lam2
version_arg  = args.version
ntree_arg    = args.ntree
maxdepth_arg = args.maxdepth
mode         = args.mode

# ============================================================
# paths
# ============================================================

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def cut_to_tag(cut: float) -> str:
    """0.1300 -> '0p1300',  -1.0 -> 'm1p0000'"""
    if cut < 0:
        return "m" + f"{abs(cut):.4f}".replace(".", "p")
    return f"{cut:.4f}".replace(".", "p")


if args.base_bdt is not None:
    CSV_BASE_DIR = args.base_bdt
else:
    _cut_tag = cut_to_tag(args.cut) if args.cut is not None else "NOCUT"
    CSV_BASE_DIR = os.path.join(
        _THIS_DIR, "..", "BDT_cut", "out",
        f"{version_arg}_{ntree_arg}_{maxdepth_arg}_{_cut_tag}"
    )

if args.output is not None:
    OUTPUT_CSV = args.output
else:
    results_dir = os.path.join(
        _THIS_DIR, "results",
        f"{version_arg}_{ntree_arg}_{maxdepth_arg}"
    )
    OUTPUT_CSV = os.path.join(results_dir, "limit_summary.csv")


# ============================================================
# helpers
# ============================================================

def normalize_lam_token(x: str) -> str:
    x = str(x).strip()
    if x.endswith(".0"):
        x = x[:-2]
    return x


# ============================================================
# CSV loaders
# ============================================================

def load_bkg_from_csv(base_dir, lumi, mx1) -> tuple:
    lumi_tag  = str(int(float(lumi)))
    bkg_csv   = os.path.join(base_dir, f"bkg_lumi{lumi_tag}_mx1{mx1}.csv")
    df        = pd.read_csv(bkg_csv)
    total_row = df[df["sample"] == "TOTAL"]
    if len(total_row) != 1:
        raise RuntimeError(f"TOTAL row not found in {bkg_csv}")
    b0      = float(total_row.iloc[0]["b0"])
    sigma_b = float(total_row.iloc[0]["sigmab0"])
    return b0, sigma_b, bkg_csv


def load_signal_from_csv(base_dir, lumi, mx1, lam1, lam2) -> tuple:
    lumi_tag       = str(int(float(lumi)))
    sig_csv        = os.path.join(base_dir, f"sig_lumi{lumi_tag}_mx1{mx1}.csv")
    df             = pd.read_csv(sig_csv)
    t_lam1         = normalize_lam_token(lam1)
    t_lam2         = normalize_lam_token(lam2)
    df["sig_norm"] = df["signal"].astype(str).str.strip()
    matched = []
    for _, row in df.iterrows():
        parts = row["sig_norm"].split("_")
        if len(parts) != 4:
            continue
        _, f_mx1, f_lam1, f_lam2 = parts
        if (f_mx1 == mx1
                and normalize_lam_token(f_lam1) == t_lam1
                and normalize_lam_token(f_lam2) == t_lam2):
            matched.append(row)
    if len(matched) != 1:
        raise RuntimeError(
            f"Signal not found or duplicated in {sig_csv}\n"
            f"  mx1={mx1}, lam1={lam1}, lam2={lam2}"
        )
    row    = matched[0]
    s0     = float(row["sg after"])
    s0_err = float(row["sg after err"])
    return s0, s0_err, sig_csv


# ============================================================
# counting model
# ============================================================

class CountingModel:
    """
    1-bin counting model with Gaussian background constraint.

    log L(n, b_obs | mu, b; s0)
      = log Pois(n; mu*s0 + b) - (b - b_obs)^2 / (2*sigma_b^2)

    Test statistic (one-sided upper limit):
      tilde{q}_mu = -2 log [ L(mu, b_hat_hat) / L(mu_hat, b_hat) ]
                  = 0  if mu_hat > mu
    """

    def __init__(self, sigma_b: float):
        self.sigma_b = float(sigma_b)

    def _log_pois(self, n, nu):
        if nu <= 0.0 or n < 0.0:
            return -math.inf
        return n * math.log(nu) - nu - gammaln(n + 1.0)

    def logL_full(self, n, b_obs, mu, b, s0):
        if mu < 0.0 or b < 0.0 or s0 < 0.0:
            return -math.inf
        nu = mu * s0 + b
        lp = self._log_pois(n, nu)
        if lp == -math.inf:
            return -math.inf
        if self.sigma_b > 0.0:
            lp += -0.5 * ((b - b_obs) / self.sigma_b) ** 2
        return lp

    def b_hat_hat_analytic(self, n, b_obs, mu, s0):
        """Analytic conditional MLE of b given mu."""
        if self.sigma_b <= 0.0:
            return max(0.0, b_obs)
        sig2 = self.sigma_b ** 2
        c    = mu * s0
        A    = sig2 - (c + b_obs)
        disc = A * A + 4.0 * sig2 * n
        t    = ((c + b_obs - sig2) + math.sqrt(disc)) / 2.0
        return max(0.0, t - c)

    def prof_logL(self, n, b_obs, mu, s0):
        bprof = self.b_hat_hat_analytic(n=n, b_obs=b_obs, mu=mu, s0=s0)
        return self.logL_full(n=n, b_obs=b_obs, mu=mu, b=bprof, s0=s0)

    def mu_hat(self, n, b_obs, s0, mu_upper=50.0):
        if s0 <= 0.0:
            return 0.0
        def nll(mu):
            ll = self.prof_logL(n=n, b_obs=b_obs, mu=mu, s0=s0)
            return math.inf if ll == -math.inf else -ll
        res = optimize.minimize_scalar(nll, bounds=(0.0, mu_upper), method="bounded")
        if not res.success:
            raise RuntimeError(f"mu_hat failed: {res.message}")
        return float(res.x)

    def qtilde_mu(self, n, b_obs, mu, s0, mu_upper=50.0):
        muhat = self.mu_hat(n=n, b_obs=b_obs, s0=s0, mu_upper=mu_upper)
        if muhat > mu:
            return 0.0
        ll_num = self.prof_logL(n=n, b_obs=b_obs, mu=mu,    s0=s0)
        ll_den = self.prof_logL(n=n, b_obs=b_obs, mu=muhat, s0=s0)
        if ll_num == -math.inf or ll_den == -math.inf:
            return float("inf")
        return max(0.0, -2.0 * (ll_num - ll_den))

    def q0(self, n, b_obs, s0, mu_upper=50.0):
        return self.qtilde_mu(n=n, b_obs=b_obs, mu=0.0, s0=s0, mu_upper=mu_upper)

    def Z0(self, n, b_obs, s0, mu_upper=50.0):
        return math.sqrt(max(0.0, self.q0(n=n, b_obs=b_obs, s0=s0, mu_upper=mu_upper)))


# ============================================================
# asymptotic CLs
# ============================================================

def cls_asymptotic(model, mu_test, s0, n_obs, b_obs_obs, nA, b_obs_A, mu_upper=50.0):
    """
    Asymptotic CLs formula (Cowan et al. 2010):

      CLs(mu) = p_mu / (1 - p_b)
              = [1 - Phi(sqrt(q_obs))] / Phi(sqrt(q_A) - sqrt(q_obs))

    where:
      q_obs : tilde{q}_mu evaluated on observed data
      q_A   : tilde{q}_mu evaluated on Asimov data (b-only: nA=b0, b_obs_A=b0)
      Phi   : standard normal CDF
    """
    q_obs   = max(0.0, float(model.qtilde_mu(n_obs, b_obs_obs, mu_test, s0, mu_upper=mu_upper)))
    qA      = max(0.0, float(model.qtilde_mu(nA,    b_obs_A,   mu_test, s0, mu_upper=mu_upper)))
    sq_qobs = math.sqrt(q_obs)
    sq_qA   = math.sqrt(qA)
    num     = 1.0 - norm.cdf(sq_qobs)
    den     = norm.cdf(sq_qA - sq_qobs)
    return float(num / max(den, 1e-15)), (q_obs, qA)


def mu_up_asymptotic(model, s0, n_obs, b_obs_obs, b0,
                     mu_min=0.0, mu_max=20.0, mu_upper=50.0, alpha=0.05):
    """
    CLs(mu) = alpha 를 만족하는 mu_up 을 brentq 로 찾는다.
    Asimov: nA = b0, b_obs_A = b0 (b-only hypothesis)
    """
    nA = b0; b_obs_A = b0
    def f(mu):
        cls, _ = cls_asymptotic(model, mu, s0, n_obs, b_obs_obs, nA, b_obs_A,
                                mu_upper=mu_upper)
        return cls - alpha
    fmin, fmax = f(mu_min), f(mu_max)
    if fmin <= 0.0:
        return float(mu_min)
    if fmax > 0.0:
        return None
    return float(brentq(f, mu_min, mu_max))


def compute_asym_band(model, s0, b0, sigma_b,
                      mu_min=0.0, mu_max=20.0, mu_upper=50.0, alpha=0.05) -> dict:
    """
    Asymptotic ±1σ, ±2σ expected band 계산.

    아이디어:
      median  : n_obs = b0           (Asimov, b-only)
      +k*sigma: n_obs = b0 + k*sigma_b  → background fluctuation up
                                         → limit 나빠짐 (mu_up 커짐)
      -k*sigma: n_obs = b0 - k*sigma_b  → limit 좋아짐 (mu_up 작아짐)

    반환: {"med": mu_up, "m1": mu_up, "p1": mu_up, "m2": mu_up, "p2": mu_up}
    """
    shifts = {"m2": -2.0, "m1": -1.0, "med": 0.0, "p1": +1.0, "p2": +2.0}
    result = {}
    for tag, k in shifts.items():
        n_shift = max(b0 + k * sigma_b, 0.0)   # 음수 방지
        result[tag] = mu_up_asymptotic(
            model, s0, n_shift, n_shift, b0=b0,
            mu_min=mu_min, mu_max=mu_max,
            mu_upper=mu_upper, alpha=alpha
        )
    return result


# ============================================================
# full toy CLs
# ============================================================

def generate_toy(rng, mu_true, s0, b0, sigma_b):
    b_obs_toy = rng.normal(loc=b0, scale=sigma_b)
    n_toy     = rng.poisson(mu_true * s0 + b0)
    return float(n_toy), float(b_obs_toy)


def cls_for_mu(model, mu_test, s0, n_obs, b_obs_obs, sigma_b,
               ntoys=2000, mu_upper=50.0, seed=1234):
    rng   = np.random.default_rng(seed)
    q_obs = model.qtilde_mu(n_obs, b_obs_obs, mu_test, s0, mu_upper=mu_upper)
    b0_mu = model.b_hat_hat_analytic(n_obs, b_obs_obs, mu_test, s0)
    b0_0  = model.b_hat_hat_analytic(n_obs, b_obs_obs, 0.0,     s0)
    q_mu  = np.empty(ntoys)
    q_b   = np.empty(ntoys)
    for i in range(ntoys):
        n_t, bobs_t = generate_toy(rng, mu_true=mu_test, s0=s0, b0=b0_mu, sigma_b=sigma_b)
        q_mu[i] = model.qtilde_mu(n_t, bobs_t, mu_test, s0, mu_upper=mu_upper)
        n_t, bobs_t = generate_toy(rng, mu_true=0.0, s0=s0, b0=b0_0, sigma_b=sigma_b)
        q_b[i]  = model.qtilde_mu(n_t, bobs_t, mu_test, s0, mu_upper=mu_upper)
    p_mu = float(np.mean(q_mu >= q_obs))
    p_b  = float(np.mean(q_b  >= q_obs))
    cls  = p_mu / max(1.0 - p_b, 1e-12)
    return cls, q_obs, (p_mu, p_b), (q_mu, q_b)


def mu_up_scan(model, s0, n_obs, b_obs_obs, sigma_b,
               mu_min=0.0, mu_max=5.0, nscan=40,
               ntoys=2000, mu_upper=50.0, seed0=1234, alpha=0.05):
    mus      = np.linspace(mu_min, mu_max, nscan)
    cls_vals = []
    for k, mu in enumerate(mus):
        cls, *_ = cls_for_mu(
            model, mu, s0, n_obs, b_obs_obs, sigma_b,
            ntoys=ntoys, mu_upper=mu_upper, seed=seed0 + k
        )
        cls_vals.append(cls)
    cls_vals = np.array(cls_vals, dtype=float)
    idx = np.where(cls_vals <= alpha)[0]
    if len(idx) == 0:
        return None, mus, cls_vals
    i = idx[0]
    if i == 0:
        return float(mus[0]), mus, cls_vals
    x0, x1 = mus[i - 1], mus[i]
    y0, y1 = cls_vals[i - 1], cls_vals[i]
    mu_up   = x0 + (alpha - y0) * (x1 - x0) / (y1 - y0 + 1e-12)
    return float(mu_up), mus, cls_vals


def compute_full_band(model, s0, b0, sigma_b,
                      mu_up_median,
                      band_toys=2000, mu_upper=50.0,
                      alpha=0.05, seed=42) -> dict:
    """
    Full toy MC ±1σ, ±2σ expected band.

    b-only toy (n, b_obs) 를 band_toys 개 생성하고
    각 toy에 대해 asymptotic mu_up 을 계산한 뒤 분위수를 취한다.

    (toy마다 full CLs scan 대신 asymptotic을 쓰는 이유:
     band_toys × nscan × ntoys 는 너무 느리기 때문.
     band는 asymptotic으로, central value만 full scan으로 하는 것이 표준적.)
    """
    rng        = np.random.default_rng(seed)
    mu_up_list = []

    for _ in range(band_toys):
        b_obs_toy = float(rng.normal(loc=b0, scale=sigma_b))
        n_toy     = float(rng.poisson(b0))         # b-only
        b_obs_toy = max(b_obs_toy, 0.0)

        mu_window = mu_up_median * 3.0 if mu_up_median else 20.0
        mu_toy = mu_up_asymptotic(
            model, s0, n_toy, b_obs_toy, b0=b0,
            mu_min=0.0, mu_max=max(mu_window, 20.0),
            mu_upper=mu_upper, alpha=alpha
        )
        if mu_toy is not None:
            mu_up_list.append(mu_toy)

    if not mu_up_list:
        return {t: None for t in ["m2", "m1", "med", "p1", "p2"]}

    arr = np.array(mu_up_list)
    return {
        "m2":  float(np.percentile(arr,  2.5)),
        "m1":  float(np.percentile(arr, 16.0)),
        "med": float(np.percentile(arr, 50.0)),
        "p1":  float(np.percentile(arr, 84.0)),
        "p2":  float(np.percentile(arr, 97.5)),
    }


# ============================================================
# output logger
# ============================================================

FIELDNAMES = [
    "mode", "version", "ntree", "maxdepth", "cut",
    "lumi", "mx1", "lam1", "lam2",
    "b0", "sigma_b", "s0", "s0_err",
    # central value
    "mu_up",    "s_up",
    # ±1σ, ±2σ band (mu scale)
    "mu_up_m2", "mu_up_m1", "mu_up_p1", "mu_up_p2",
    # ±1σ, ±2σ band (signal yield scale)
    "s_up_m2",  "s_up_m1",  "s_up_p1",  "s_up_p2",
]


def append_result(output_path: str, row: dict):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    file_exists = os.path.isfile(output_path) and os.path.getsize(output_path) > 0
    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        # 없는 컬럼은 빈 문자열로
        full_row = {k: row.get(k, "") for k in FIELDNAMES}
        writer.writerow(full_row)


# ============================================================
# main
# ============================================================

print("==== CONFIG ====")
print(f"  version   = {version_arg}")
print(f"  ntree     = {ntree_arg}")
print(f"  maxdepth  = {maxdepth_arg}")
print(f"  cut       = {args.cut}")
print(f"  lumi      = {lumi_arg}")
print(f"  mx1       = {mx1_arg}")
print(f"  lam1      = {lam1_arg}")
print(f"  lam2      = {lam2_arg}")
print(f"  mode      = {mode}")
print(f"  csv_dir   = {CSV_BASE_DIR}")
print(f"  output    = {OUTPUT_CSV}")

b0, sigma_b, bkg_csv = load_bkg_from_csv(CSV_BASE_DIR, lumi_arg, mx1_arg)
s0, s0_err, sig_csv  = load_signal_from_csv(CSV_BASE_DIR, lumi_arg, mx1_arg,
                                             lam1_arg, lam2_arg)

print("\n==== INPUT ====")
print(f"  bkg csv = {bkg_csv}")
print(f"  sig csv = {sig_csv}")
print(f"  b0      = {b0}")
print(f"  sigma_b = {sigma_b}")
print(f"  s0      = {s0}")
print(f"  s0_err  = {s0_err}")

n_obs     = float(b0)
b_obs_obs = float(b0)
model     = CountingModel(sigma_b=sigma_b)

# ---- asymptotic central value ----
mu_up_asym = mu_up_asymptotic(
    model, s0, n_obs, b_obs_obs, b0=b0,
    mu_min=0.0, mu_max=20.0, mu_upper=50.0, alpha=0.05
)
s_up_asym = (s0 * mu_up_asym) if mu_up_asym is not None else None

print("\n==== ASYMPTOTIC ====")
print(f"  mu_up(median) = {mu_up_asym}")
print(f"  s_up(median)  = {s_up_asym}")

# ---- asymptotic band ----
asym_band = compute_asym_band(
    model, s0, b0, sigma_b,
    mu_min=0.0, mu_max=20.0, mu_upper=50.0, alpha=0.05
)
print(f"  mu_up(-2s) = {asym_band['m2']}")
print(f"  mu_up(-1s) = {asym_band['m1']}")
print(f"  mu_up(+1s) = {asym_band['p1']}")
print(f"  mu_up(+2s) = {asym_band['p2']}")

# ---- full toy scan ----
mu_up_full = None
s_up_full  = None
full_band  = {t: None for t in ["m2", "m1", "med", "p1", "p2"]}

if mode == "full":
    if mu_up_asym is None:
        print("[ERROR] asymptotic failed, cannot set scan window. Exiting.")
        sys.exit(1)
    mu_lo = max(0.0, mu_up_asym - 0.25)
    mu_hi = mu_up_asym + 0.25
    print(f"\n==== FULL SCAN (ntoys={args.ntoys}, nscan={args.nscan}) ====")
    print(f"  window = [{mu_lo:.4f}, {mu_hi:.4f}]")
    mu_up_full, mus, cls_vals = mu_up_scan(
        model, s0, n_obs, b_obs_obs, sigma_b,
        mu_min=mu_lo, mu_max=mu_hi, nscan=args.nscan,
        ntoys=args.ntoys, seed0=1234, alpha=0.05
    )
    s_up_full = (s0 * mu_up_full) if mu_up_full is not None else None
    print(f"  mu_up(full) = {mu_up_full}")
    print(f"  s_up(full)  = {s_up_full}")

    print(f"\n==== FULL BAND (band_toys={args.band_toys}) ====")
    full_band = compute_full_band(
        model, s0, b0, sigma_b,
        mu_up_median=mu_up_full,
        band_toys=args.band_toys,
        mu_upper=50.0, alpha=0.05
    )
    print(f"  mu_up(-2s) = {full_band['m2']}")
    print(f"  mu_up(-1s) = {full_band['m1']}")
    print(f"  mu_up(med) = {full_band['med']}")
    print(f"  mu_up(+1s) = {full_band['p1']}")
    print(f"  mu_up(+2s) = {full_band['p2']}")

# ---- 최종 결과 결정 ----
if mode == "full" and mu_up_full is not None:
    mu_up_final = mu_up_full
    s_up_final  = s_up_full
    band        = full_band
else:
    mu_up_final = mu_up_asym
    s_up_final  = s_up_asym
    band        = asym_band

def _s(mu):
    return (s0 * mu) if (mu is not None) else None

print("\n==== RESULT ====")
print(f"  mode   = {mode}")
print(f"  mu_up  = {mu_up_final}")
print(f"  s_up   = {s_up_final}")

append_result(OUTPUT_CSV, {
    "mode":     mode,
    "version":  version_arg,
    "ntree":    ntree_arg,
    "maxdepth": maxdepth_arg,
    "cut":      args.cut if args.cut is not None else "",
    "lumi":     lumi_arg,
    "mx1":      mx1_arg,
    "lam1":     lam1_arg,
    "lam2":     lam2_arg,
    "b0":       b0,
    "sigma_b":  sigma_b,
    "s0":       s0,
    "s0_err":   s0_err,
    "mu_up":    mu_up_final,
    "s_up":     s_up_final,
    "mu_up_m2": band.get("m2"),  "s_up_m2": _s(band.get("m2")),
    "mu_up_m1": band.get("m1"),  "s_up_m1": _s(band.get("m1")),
    "mu_up_p1": band.get("p1"),  "s_up_p1": _s(band.get("p1")),
    "mu_up_p2": band.get("p2"),  "s_up_p2": _s(band.get("p2")),
})
print(f"\n[LOG] appended → {OUTPUT_CSV}")



