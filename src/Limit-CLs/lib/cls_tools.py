import math
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from lib.counting_model import CountingModel


# ============================================================
# toy generator
# ============================================================

def generate_toy(rng, mu_true, s0, b0, sigma_b):
    """
    Observable (n, b_obs) 를 toy MC로 생성한다.
      b_obs ~ Normal(b0, sigma_b)
      n     ~ Poisson(mu_true * s0 + b0)
    """
    b_obs_toy = rng.normal(loc=b0, scale=sigma_b)
    n_toy     = rng.poisson(mu_true * s0 + b0)
    return float(n_toy), float(b_obs_toy)


# ============================================================
# asymptotic CLs
# ============================================================

def cls_asymptotic(model: CountingModel,
                   mu_test, s0,
                   n_obs, b_obs_obs,
                   nA, b_obs_A,
                   mu_upper=50.0):
    """
    Asymptotic CLs:
      CLs = (1 - Phi(sqrt(q_obs))) / Phi(sqrt(qA) - sqrt(q_obs))
    """
    q_obs   = max(0.0, float(model.qtilde_mu(n_obs, b_obs_obs, mu_test, s0, mu_upper=mu_upper)))
    qA      = max(0.0, float(model.qtilde_mu(nA,    b_obs_A,   mu_test, s0, mu_upper=mu_upper)))
    sq_qobs = math.sqrt(q_obs)
    sq_qA   = math.sqrt(qA)
    num     = 1.0 - norm.cdf(sq_qobs)
    den     = norm.cdf(sq_qA - sq_qobs)
    return float(num / max(den, 1e-15)), (q_obs, qA)


def mu_up_asymptotic(model: CountingModel,
                     s0, n_obs, b_obs_obs, b0,
                     mu_min=0.0, mu_max=20.0,
                     mu_upper=50.0, alpha=0.05):
    """
    brentq로 CLs(mu) = alpha 를 풀어 95% CL upper limit mu_up 을 반환한다.
    Asimov: nA = b0, b_obs_A = b0 (b-only)
    반환값이 None이면 mu_max 까지 가도 CLs > alpha (mu_max 늘려야 함).
    """
    nA = b0
    b_obs_A = b0

    def f(mu):
        cls, _ = cls_asymptotic(
            model, mu, s0, n_obs, b_obs_obs, nA, b_obs_A, mu_upper=mu_upper
        )
        return cls - alpha

    fmin, fmax = f(mu_min), f(mu_max)
    if fmin <= 0.0:
        return float(mu_min)
    if fmax > 0.0:
        return None
    return float(brentq(f, mu_min, mu_max))


# ============================================================
# full toy CLs
# ============================================================

def cls_for_mu(model: CountingModel,
               mu_test, s0, n_obs, b_obs_obs, sigma_b,
               ntoys=2000, mu_upper=50.0, seed=1234):
    """
    toy MC로 CLs(mu_test) 를 계산한다.
    """
    rng   = np.random.default_rng(seed)
    q_obs = model.qtilde_mu(n_obs, b_obs_obs, mu_test, s0, mu_upper=mu_upper)

    b0_mu = model.b_hat_hat_analytic(n_obs, b_obs_obs, mu_test, s0)
    b0_0  = model.b_hat_hat_analytic(n_obs, b_obs_obs, 0.0,     s0)

    q_mu = np.empty(ntoys)
    q_b  = np.empty(ntoys)

    for i in range(ntoys):
        n_t, bobs_t = generate_toy(rng, mu_true=mu_test, s0=s0, b0=b0_mu, sigma_b=sigma_b)
        q_mu[i] = model.qtilde_mu(n_t, bobs_t, mu_test, s0, mu_upper=mu_upper)

        n_t, bobs_t = generate_toy(rng, mu_true=0.0, s0=s0, b0=b0_0, sigma_b=sigma_b)
        q_b[i]  = model.qtilde_mu(n_t, bobs_t, mu_test, s0, mu_upper=mu_upper)

    p_mu = float(np.mean(q_mu >= q_obs))
    p_b  = float(np.mean(q_b  >= q_obs))
    cls  = p_mu / max(1.0 - p_b, 1e-12)

    return cls, q_obs, (p_mu, p_b), (q_mu, q_b)


def mu_up_scan(model: CountingModel,
               s0, n_obs, b_obs_obs, sigma_b,
               mu_min=0.0, mu_max=5.0, nscan=40,
               ntoys=2000, mu_upper=50.0, seed0=1234, alpha=0.05):
    """
    mu 구간을 선형으로 나눠 CLs scan 후 선형보간으로 mu_up 을 반환한다.
    반환값이 None이면 구간 내에서 CLs <= alpha 가 없음.
    """
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
