# Phase 2 experimental design

**Status:** Version 0.2, Notebooks 08 and 09 validated; Notebook 10 implementation ready for production validation

**Branch:** `phase-2-correlation-extension`

**Frozen reference:** Phase 1 release `v1.0.0`, commit `be93474ce2ab78d8002d49ae861adb641ae2741d`

## 1. Purpose

Phase 2 will quantify how within-event spatial correlation changes earthquake portfolio loss, reinsurance performance, capital, diversification, risk-adjusted return, and parametric basis risk.

The central requirement is a paired experiment. Phase 2 must change the within-event spatial dependence while holding the Phase 1 hazard, exposure, marginal ground-motion distributions, damage model, financial terms, and random-number controls fixed. This permits differences in results to be attributed to spatial correlation rather than model drift.

Phase 2 will not overwrite the Phase 1 release or its artifacts.

## 2. Frozen Phase 1 controls

The following items are experimental controls.

| Control | Frozen value or artifact |
|---|---|
| Release reference | `v1.0.0` at `be93474ce2ab78d8002d49ae861adb641ae2741d` |
| Annual event catalog | 2,000,000 years, 10,630 occurrences, 10,593 occupied years |
| Event catalog seed | `20260729` |
| Event catalog SHA-256 | `e4725a57eab466348aa263d79b8f8bcc923f9542fb5507af279fece41c121f37` |
| Ground-motion seed | `20260731` |
| Ground-motion model | Parker et al. subduction interface and slab implementations already used in Notebook 4 |
| Intensity measures | PGA and exact SA(0.4 s) |
| GMM epistemic branch | `epi-off` production branch |
| Site order SHA-256 | `fc64d53410fdadab5379f82c73c1d74ce3393911fbdd73a0dbc483f056f3d100` |
| Same-site PGA versus SA(0.4 s) correlation | `0.7321409900247263` |
| Between-event residuals | Reuse each event's Phase 1 draw |
| Raw within-event latent vectors | Regenerate the same two event/site vectors from the frozen Phase 1 seed specification |
| Structural damage uniforms | Reuse `notebook5_structural_damage_v1` |
| Nonstructural drift uniforms | Reuse `notebook5_nonstructural_drift_damage_v1` |
| Nonstructural acceleration uniforms | Reuse `notebook5_nonstructural_acceleration_damage_v1` |
| Portfolio | Same 470-building Seaside portfolio and replacement values |
| Policy | Full-coverage baseline with 10 percent per-building, per-occurrence deductible and the existing limit and coinsurance rules |
| Baseline occurrence XoL | Attachment USD 18,811,083.54014544, limit USD 61,837,983.314918146, 100 percent participation |
| Annual statistics | Include all 2,000,000 years, including zero-loss years |

The Phase 1 independent case must be reproduced before any correlated result is accepted.

## 3. Experimental cases

| Case | Role | Within-event spatial dependence |
|---|---|---|
| `I0_PHASE1_INDEPENDENT` | Frozen control | Identity spatial correlation matrix |
| `C1_ALDEA22_SUBDUCTION` | Primary correlated case | Aldea, Heresi, and Pastén (2022), with separate published PGA and SA(0.4 s) kernels |
| `C2_GODA_ATKINSON09` | Subduction benchmark sensitivity | Goda and Atkinson (2009) pooled subduction-environment kernel |

The primary case is Aldea et al. (2022) because its database contains interface and intraslab events, it uses the geometric mean of horizontal components, and it provides published PGA and SA(0.4 s) behavior. The Goda and Atkinson model is retained as a second subduction model and a sensitivity benchmark.

The two models are analog models, not Cascadia-specific calibrations. Results must therefore be described as model-conditioned estimates.

## 4. Portfolio geometry audit

The frozen site file contains:

- 470 buildings;
- 426 distinct coordinates;
- 110,215 building pairs;
- 25 groups of co-located buildings;
- 69 buildings in co-located groups;
- a largest co-located group of 17 buildings;
- median pair separation of 1.2415 km;
- maximum pair separation of 6.4244 km.

A zero-separation correlation of one creates 44 structural zero eigenmodes, equal to $470 - 426$. This is expected and is not a numerical defect. Co-located buildings receive the same ground-motion residual but retain their separate structural and nonstructural damage uniforms.

Pre-simulation geometry diagnostics are:

| Model and IM | Mean off-diagonal correlation | Correlation at maximum separation |
|---|---:|---:|
| Aldea et al. PGA | 0.7905 | 0.5373 |
| Aldea et al. SA(0.4 s) | 0.7121 | 0.4043 |
| Goda and Atkinson common kernel | 0.7247 | 0.5196 |

The equal-weight linear effective-site-count diagnostics are 1.26, 1.40, and 1.38, respectively. These values demonstrate that the portfolio is compact relative to the published correlation ranges. They are diagnostics only, not forecasts of insured-loss diversification.

## 5. Spatial-correlation mathematics

Let $d_{st}$ be the great-circle separation in km between sites $s$ and $t$. Let $\rho_T=0.7321409900247263$ be the frozen same-site cross-IMT correlation. Let $z_1$ and $z_2$ be the two independent standard-normal site vectors regenerated from the existing Phase 1 event/site seed.

### 5.1 Primary Aldea et al. case

For intensity measure $j$,

$$
C_j(d)=\exp\left[-\left(\frac{d}{\beta_j}\right)^{0.59}\right],
$$

with:

- $\beta_{\mathrm{PGA}}=14.40$ km;
- $\beta_{\mathrm{SA}(0.4)}=7.60$ km.

Define

$$
V=\frac{C_{\mathrm{SA}(0.4)}-\rho_T^2 C_{\mathrm{PGA}}}{1-\rho_T^2}.
$$

For the frozen 470-site layout, $C_{\mathrm{PGA}}$, $C_{\mathrm{SA}(0.4)}$, and $V$ are positive semidefinite to numerical precision. Their small negative eigenvalues are approximately $10^{-15}$, with no eigenvalue below $-10^{-10}$.

Generate

$$
\epsilon_{\mathrm{PGA}}=C_{\mathrm{PGA}}^{1/2}z_1,
$$

$$
\epsilon_{\mathrm{SA}(0.4)}
=\rho_T\epsilon_{\mathrm{PGA}}
+\sqrt{1-\rho_T^2}\,V^{1/2}z_2.
$$

This construction preserves:

- unit marginal normal distributions;
- the published PGA spatial correlation;
- the published SA(0.4 s) spatial correlation;
- the frozen same-site cross-IMT correlation;
- the two frozen raw random vectors used for paired comparison.

It implies a cross-site, cross-IMT covariance of $\rho_T C_{\mathrm{PGA}}$. This assumption must be documented in all model metadata.

### 5.2 Goda and Atkinson benchmark

Use

$$
C(d)=\max\left[1.389\exp\left(-0.207d^{0.386}\right)-1.389+1,\ 0\right].
$$

Generate

$$
\epsilon_{\mathrm{PGA}}=C^{1/2}z_1,
$$

$$
\epsilon_{\mathrm{SA}(0.4)}
=\rho_T\epsilon_{\mathrm{PGA}}
+\sqrt{1-\rho_T^2}\,C^{1/2}z_2.
$$

This produces the same spatial kernel for both IMTs and cross-site, cross-IMT covariance $\rho_T C$.

### 5.3 Numerical factorization

Use a symmetric spectral square root, not an ordinary Cholesky factor, because co-located buildings make the matrices singular.

For every matrix:

1. enforce numerical symmetry;
2. compute all eigenvalues and eigenvectors;
3. reject the case if the minimum eigenvalue is below $-10^{-10}$;
4. define the numerical-rank threshold as the larger of $10^{-10}$ and the matrix-size-scaled floating-point threshold, then set eigenvalues at or below that threshold to zero;
5. construct the symmetric positive-semidefinite spectral square root from the retained modes;
6. detect exact duplicate rows in the symmetrized target correlation matrix and project both axes of the square root onto each duplicate-row subspace;
7. rebuild the covariance from the projected square root and record the minimum eigenvalue, zero-mode and negative-eigenvalue counts, Frobenius correction, rank, reconstruction error, duplicate-row diagnostics, and square-root symmetry error;
8. verify the reconstructed unit diagonal and exact equality of simulated residuals at co-located coordinates.

If $L$ is the spectral square root and $P$ averages coordinates within each exact duplicate-row group, the projection is

$$
L \leftarrow P L P.
$$

For exact duplicate correlation rows, this projection is mathematically neutral. It preserves the target covariance apart from floating-point roundoff, keeps the factor symmetric, and makes every co-located residual numerically identical across supported platforms. The full 470-element frozen latent vectors remain in use, so the paired random-number design is unchanged.

The pre-simulation audit found no material negative eigenvalues for either selected model.

## 6. Ground-motion and loss propagation

For every event occurrence and site,

$$
\ln(IM_{e,s})=\mu_{e,s}+\tau_{e,s}\eta_e+\phi_{e,s}\epsilon_{e,s}.
$$

Only $\epsilon_{e,s}$ changes across I0, C1, and C2. The following remain identical:

- event occurrence and event time;
- rupture and source type;
- median ground motion;
- between-event residual;
- $\tau$ and $\phi$;
- marginal standard-normal distribution of each within-event residual;
- damage-state uniforms;
- replacement costs;
- policy calculations;
- reinsurance formulas.

The first production comparison must run the existing structural, nonstructural drift, and nonstructural acceleration components separately and reconcile them to ground-up loss before insurance terms are applied.

## 7. Reinsurance experiments

### 7.1 Frozen occurrence benchmark

Apply the Phase 1 occurrence XoL unchanged to all three dependence cases. This isolates the effect of spatial correlation on expected ceded loss, exhaustion frequency, retained loss, and tail capital.

### 7.2 Occurrence design grid

Evaluate candidate attachments and limits on a common grid. At minimum, attachments should span gross insured OEP return periods from 100 to 1,000 years, and exhaustion points should span 1,000 to 10,000 years.

For each dependence case, report:

- expected ceded loss;
- ceded standard deviation;
- attachment probability;
- exhaustion probability;
- occurrence recovery AEP and OEP;
- retained AEP and OEP;
- retained VaR and TVaR;
- capital relief per dollar of expected ceded loss;
- minimum limit required to meet each stated retained-loss or capital target.

### 7.3 Annual aggregate cover

Evaluate both:

1. a standalone annual aggregate stop-loss on gross insured annual aggregate loss; and
2. a stacked annual aggregate stop-loss on annual net loss after the occurrence layer.

For annual loss $N_y$, attachment $A_{\mathrm{agg}}$, and limit $L_{\mathrm{agg}}$,

$$
C_{\mathrm{agg},y}
=\min\left[\max(N_y-A_{\mathrm{agg}},0),L_{\mathrm{agg}}\right].
$$

All program comparisons must state the order in which occurrence and aggregate covers are applied.

## 8. Risk and decision metrics

| Measure | Phase 2 definition |
|---|---|
| AAL | Arithmetic mean over all 2,000,000 annual losses, including zero years |
| OEP | Return-period curve from the annual maximum occurrence loss |
| AEP | Return-period curve from annual aggregate loss |
| PML | Labeled explicitly as OEP PML or AEP PML at the stated return period |
| TVaR | Empirical conditional tail mean at 99.0 percent and 99.5 percent, with the estimator documented |
| Economic capital | Primary: retained AEP VaR(99.5 percent) minus retained AAL. Supplemental tail capital: retained AEP TVaR(99.5 percent) minus retained AAL |
| Required occurrence limit | Minimum limit, at a stated attachment, that satisfies a stated retained PML or capital target |
| Attachment selection | Technical view: maximize capital relief per dollar of expected ceded loss subject to the risk appetite. Economic view: maximize RAROC after a ceded-price assumption is supplied |
| Expected ceded loss | Mean annual ceded loss, separately for occurrence, aggregate, and stacked structures |
| Diversification benefit | $1-\mathrm{Risk}(\mathrm{portfolio})/\sum_i\mathrm{Risk}(i)$, reported for AAL, VaR, and TVaR as applicable |
| Risk-adjusted return | $\mathrm{RAROC}=(P-E-\mathrm{AAL}_{\mathrm{ret}}-RP)/EC$, where $P$ is earned premium, $E$ is expenses, $RP$ is reinsurance premium, and $EC$ is economic capital |

Premium, expense, and reinsurance pricing assumptions are not present in Phase 1. Phase 2 must not invent them. Until approved inputs are supplied, report break-even required premium, capital efficiency, and RAROC over a transparent assumption grid.

Every executive comparison must give the independent value, correlated value, absolute change, and percentage change.

## 9. Parametric catastrophe-bond extension

The first extension will be a fully collateralized, event-level magnitude-distance trigger based only on source parameters available before indemnity loss is known.

The trigger index will use:

- source type;
- moment magnitude;
- authoritative rupture-to-portfolio distance;
- fixed payout tiers and a fixed maximum payout.

Calibration rules:

1. use catalog years 1 through 1,000,000 for trigger calibration;
2. freeze all trigger thresholds and payout tiers;
3. use years 1,000,001 through 2,000,000 for out-of-sample basis-risk evaluation;
4. do not recalibrate the trigger separately for the independent and correlated cases;
5. compare the same parametric payouts against the different indemnity losses produced by `I0`, `C1`, and `C2`.

Basis-risk outputs must include:

- payout AAL;
- correlation between payout and target indemnity recovery;
- false-negative probability;
- false-positive probability;
- expected protection shortfall;
- expected excess payout;
- mean absolute and root-mean-square basis error;
- residual retained VaR and TVaR;
- conditional shortfall for events above the target indemnity attachment.

A positive basis value will be defined as indemnity recovery minus parametric payout, so positive values represent protection shortfall.

## 10. Validation gates

A production run is accepted only if all gates pass.

### Reproducibility

- correct branch and frozen commit reference;
- exact event catalog hash;
- exact site order hash;
- exact random-stream specifications;
- deterministic rerun hashes for every new artifact.
- repository-relative POSIX paths in all public metadata and handoff files;
- exclusion of run-time timestamps from hash-tracked artifacts.

### Marginals

For each case and IMT:

- residual mean and standard deviation within documented tolerance;
- quantile agreement with a standard normal;
- marginal ground-motion quantiles consistent with Phase 1 sampling uncertainty;
- unchanged event, rupture, median, $\tau$, and $\phi$ fields.

### Dependence

- empirical site-pair correlations reproduce target distance-bin correlations;
- same-site PGA versus SA(0.4 s) correlation reproduces $\rho_T$;
- co-located residuals agree within tolerance;
- matrix rank, eigenvalue, and reconstruction diagnostics pass.

### Damage and finance

- structural plus nonstructural components reconcile to ground-up loss;
- uninsured plus insured loss reconciles to ground-up loss;
- retained plus ceded loss reconciles to insured loss;
- occurrence and aggregate recoveries obey attachment and limit bounds;
- all annual statistics include zero years.

### Statistical stability

- report order-statistic support at every headline return period;
- retain the Phase 1 warning for return periods with fewer than 20 supporting tail observations;
- quantify Monte Carlo uncertainty for AAL, PML, and TVaR comparisons;
- use paired differences wherever common random numbers permit.

## 11. Planned Phase 2 notebooks

| Notebook | Purpose |
|---|---|
| `08_spatial_correlation_model_and_validation.ipynb` | Site geometry, correlation matrices, joint PGA and SA construction, PSD and empirical validation |
| `09_generate_correlated_ground_motion_fields.ipynb` | Full-catalog `I0`, `C1`, and `C2` ground-motion fields |
| `10_correlated_damage_and_loss.ipynb` | Structural and nonstructural damage, ground-up and insured loss |
| `11_reinsurance_sensitivity_and_capital.ipynb` | Occurrence and aggregate structures, retained and ceded distributions, capital, TVaR, diversification, and RAROC |
| `12_parametric_cat_bond_basis_risk.ipynb` | Trigger calibration, out-of-sample payout, and basis-risk analysis |
| `13_phase_2_results_and_validation.ipynb` | Final validation, executive tables, figures, and release handoff |

New outputs will be stored under Phase 2-specific paths. Phase 1 artifacts will remain unchanged.

## 12. Phase 2 release acceptance criteria

The Phase 2 release must demonstrate:

- the full stochastic annual earthquake event catalog;
- structural and nonstructural damage;
- ground-up and insured losses;
- deductibles, limits, and coinsurance;
- occurrence and aggregate reinsurance;
- AAL, OEP, AEP, PML, and TVaR;
- independent versus correlated losses;
- retained and ceded loss distributions;
- sensitivity of reinsurance recoveries to correlation;
- a parametric catastrophe-bond extension;
- out-of-sample basis-risk analysis;
- clear executive interpretation.

The final executive table must quantify how correlation changes:

- required reinsurance limits;
- selected attachments;
- expected ceded loss;
- capital requirements;
- tail-value-at-risk;
- portfolio diversification;
- risk-adjusted return.

A statement such as "correlation increases tail loss" is not an acceptable conclusion without these quantified decision impacts.

## 13. Primary references

- Aldea, S., Heresi, P., and Pastén, C. (2022). "Within-event spatial correlation of peak ground acceleration and spectral pseudo-acceleration ordinates in the Chilean subduction zone." *Earthquake Engineering & Structural Dynamics*, 51, 2575-2590. [DOI 10.1002/eqe.3674](https://doi.org/10.1002/eqe.3674).
- Goda, K., and Atkinson, G. M. (2009). "Probabilistic characterization of spatially correlated response spectra for earthquakes in Japan." *Bulletin of the Seismological Society of America*, 99(5), 3003-3020. [DOI 10.1785/0120090007](https://doi.org/10.1785/0120090007).
- Baker, J. W., and Jayaram, N. (2008). "Correlation of spectral acceleration values from NGA ground motion models." *Earthquake Spectra*, 24(1), 299-317. [DOI 10.1193/1.2857544](https://doi.org/10.1193/1.2857544).
