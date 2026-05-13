# Cross-section used in exclusion condition (`plot_contour_fitbased.py`)

## Question

A coupling point (λ₁, λ₂) is excluded at 95% CL when its theoretical signal yield exceeds N_exc:

> Is the cross-section used here the **xs plane value** (analytic fitted surface), or the **xs point value** (raw discrete simulation points)?

---

## Answer: xs plane value (analytic fitted surface)

The cross-section is evaluated from a continuous analytic surface, not the raw discrete simulation points.

---

## How it works

### Step 1 — Fit A from discrete simulation points

`fit_A_per_mx1()` reads `cross_section_SG.csv` (discrete MadGraph xs values at grid points)
and fits a single parameter **A** per MX1 using the analytic formula:

$$\sigma(\lambda_1, \lambda_2) = A \cdot \frac{\lambda_1^2 \,\lambda_2^2}{4\lambda_1^2 + \lambda_2^2}$$

An iterative outlier-rejection loop removes points with >10% relative deviation before finalizing A.

### Step 2 — Evaluate xs on a dense continuous grid

`_xs_model((L1, L2), A)` evaluates the fitted formula at **any** (λ₁, λ₂), producing a smooth 2D surface (500×500 grid).

### Step 3 — Compute signal yield

```python
xs_grid  = _xs_model((L1, L2), A)               # xs plane  [pb]
eff_grid = np.clip(eff_sp(L1_GRID, L2_GRID).T, 0, 1)   # eff plane (RectBivariateSpline)
N_sig    = xs_grid * lumi * 1000 * eff_grid      # event yield
```

The efficiency is also a continuous interpolated surface (`RectBivariateSpline` from `efficiency.csv`).

### Step 4 — Draw exclusion contour

The contour drawn on the (λ₁, λ₂) plane is the level set:

$$N_{\rm sig}(\lambda_1, \lambda_2) = N_{\rm exc}$$

i.e., the curve where the signal yield equals the median expected excluded yield from the CLs fit.

---

## Summary

| Quantity | Source |
|---|---|
| xs | Analytic formula, A fitted from discrete sim points |
| eff | `RectBivariateSpline` interpolated from `efficiency.csv` |
| N_sig | `xs_plane × lumi × 1000 × eff_plane` |
| Contour | `N_sig(λ₁, λ₂) = N_exc` level set on dense grid |

The contour is fully continuous — the discrete simulation points are only used to determine the single fitting parameter A (per MX1).
