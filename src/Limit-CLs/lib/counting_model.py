import math
from scipy import optimize
from scipy.special import gammaln


class CountingModel:
    """
    RooStats-style 1-bin counting with Gaussian background constraint:
      log L(n, b_obs | mu, b; s0)
        = log Pois(n; mu*s0 + b) - (b - b_obs)^2 / (2*sigma_b^2)
    Constraints: mu >= 0, b >= 0
    """

    def __init__(self, sigma_b: float):
        self.sigma_b = float(sigma_b)

    # ------------------------------------------------------------------
    def _log_pois(self, n: float, nu: float) -> float:
        if nu <= 0.0 or n < 0.0:
            return -math.inf
        return n * math.log(nu) - nu - gammaln(n + 1.0)

    def logL_full(self, n, b_obs, mu, b, s0) -> float:
        if mu < 0.0 or b < 0.0 or s0 < 0.0:
            return -math.inf
        nu = mu * s0 + b
        lp = self._log_pois(n, nu)
        if lp == -math.inf:
            return -math.inf
        if self.sigma_b > 0.0:
            lp += -0.5 * ((b - b_obs) / self.sigma_b) ** 2
        return lp

    # ------------------------------------------------------------------
    def b_hat_hat_analytic(self, n, b_obs, mu, s0) -> float:
        """Analytic conditional MLE b_hat_hat(mu)."""
        if self.sigma_b <= 0.0:
            return max(0.0, b_obs)
        sig2 = self.sigma_b ** 2
        c    = mu * s0
        A    = sig2 - (c + b_obs)
        disc = A * A + 4.0 * sig2 * n
        t    = ((c + b_obs - sig2) + math.sqrt(disc)) / 2.0
        return max(0.0, t - c)

    def prof_logL(self, n, b_obs, mu, s0) -> float:
        bprof = self.b_hat_hat_analytic(n=n, b_obs=b_obs, mu=mu, s0=s0)
        return self.logL_full(n=n, b_obs=b_obs, mu=mu, b=bprof, s0=s0)

    # ------------------------------------------------------------------
    def mu_hat(self, n, b_obs, s0, mu_upper=50.0) -> float:
        if s0 <= 0.0:
            return 0.0
        def nll(mu):
            ll = self.prof_logL(n=n, b_obs=b_obs, mu=mu, s0=s0)
            return math.inf if ll == -math.inf else -ll
        res = optimize.minimize_scalar(nll, bounds=(0.0, mu_upper), method="bounded")
        if not res.success:
            raise RuntimeError(f"mu_hat failed: {res.message}")
        return float(res.x)

    def qtilde_mu(self, n, b_obs, mu, s0, mu_upper=50.0) -> float:
        """One-sided test statistic tilde{q}_mu for upper limits."""
        muhat = self.mu_hat(n=n, b_obs=b_obs, s0=s0, mu_upper=mu_upper)
        if muhat > mu:
            return 0.0
        ll_num = self.prof_logL(n=n, b_obs=b_obs, mu=mu,    s0=s0)
        ll_den = self.prof_logL(n=n, b_obs=b_obs, mu=muhat, s0=s0)
        if ll_num == -math.inf or ll_den == -math.inf:
            return float("inf")
        return max(0.0, -2.0 * (ll_num - ll_den))

    def q0(self, n, b_obs, s0, mu_upper=50.0) -> float:
        """Discovery test statistic q0."""
        return self.qtilde_mu(n=n, b_obs=b_obs, mu=0.0, s0=s0, mu_upper=mu_upper)

    def Z0(self, n, b_obs, s0, mu_upper=50.0) -> float:
        """Asymptotic discovery significance Z0 = sqrt(q0)."""
        return math.sqrt(max(0.0, self.q0(n=n, b_obs=b_obs, s0=s0, mu_upper=mu_upper)))

    def Z0_asimov(self, b0, s0, sigma_b=None, mu_upper=50.0) -> float:
        if sigma_b is not None:
            self.sigma_b = float(sigma_b)
        return self.Z0(n=b0 + s0, b_obs=b0, s0=s0, mu_upper=mu_upper)
