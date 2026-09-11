# Phase 2 results and validation

Status: production artifact audit passed

This synthesis compares frozen dependence cases. It does not recalibrate the hazard, damage, financial, or parametric models.

## Executive comparisons

Money is constant 2022 USD. Changes are relative to I0. Insurance and reinsurance use the full catalog; parametric results use the held-out evaluation years.

| Case | Measure / program | Value | Change from I0 |
|---|---|---:|---:|
| I0_PHASE1_INDEPENDENT | ground_up_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 195,922 | 0 |
| C1_ALDEA22_SUBDUCTION | ground_up_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 196,625 | 702.255 |
| C2_GODA_ATKINSON09 | ground_up_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 196,518 | 595.967 |
| I0_PHASE1_INDEPENDENT | gross_insured_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 122,980 | 0 |
| C1_ALDEA22_SUBDUCTION | gross_insured_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 123,443 | 463.869 |
| C2_GODA_ATKINSON09 | gross_insured_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 123,336 | 356.117 |
| I0_PHASE1_INDEPENDENT | uninsured_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 72,942.9 | 0 |
| C1_ALDEA22_SUBDUCTION | uninsured_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 73,181.3 | 238.385 |
| C2_GODA_ATKINSON09 | uninsured_aal_2022_usd / FULL_CATALOG_2000000_YEARS | 73,182.7 | 239.85 |
| I0_PHASE1_INDEPENDENT | ceded_aal_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 0 | 0 |
| I0_PHASE1_INDEPENDENT | ceded_aal_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 63,676.6 | 0 |
| I0_PHASE1_INDEPENDENT | ceded_aal_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 63,662.6 | 0 |
| I0_PHASE1_INDEPENDENT | ceded_aal_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 74,258.8 | 0 |
| C1_ALDEA22_SUBDUCTION | ceded_aal_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 0 | 0 |
| C1_ALDEA22_SUBDUCTION | ceded_aal_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 58,654.7 | -5,021.9 |
| C1_ALDEA22_SUBDUCTION | ceded_aal_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 58,585.2 | -5,077.37 |
| C1_ALDEA22_SUBDUCTION | ceded_aal_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 77,886.5 | 3,627.7 |
| C2_GODA_ATKINSON09 | ceded_aal_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 0 | 0 |
| C2_GODA_ATKINSON09 | ceded_aal_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 58,604.1 | -5,072.45 |
| C2_GODA_ATKINSON09 | ceded_aal_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 58,537.6 | -5,124.96 |
| C2_GODA_ATKINSON09 | ceded_aal_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 77,874.1 | 3,615.36 |
| I0_PHASE1_INDEPENDENT | retained_aal_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 122,980 | 0 |
| I0_PHASE1_INDEPENDENT | retained_aal_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 59,303 | 0 |
| I0_PHASE1_INDEPENDENT | retained_aal_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 59,317 | 0 |
| I0_PHASE1_INDEPENDENT | retained_aal_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 48,720.8 | 0 |
| C1_ALDEA22_SUBDUCTION | retained_aal_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 123,443 | 463.869 |
| C1_ALDEA22_SUBDUCTION | retained_aal_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 64,788.7 | 5,485.77 |
| C1_ALDEA22_SUBDUCTION | retained_aal_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 64,858.2 | 5,541.24 |
| C1_ALDEA22_SUBDUCTION | retained_aal_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 45,557 | -3,163.83 |
| C2_GODA_ATKINSON09 | retained_aal_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 123,336 | 356.117 |
| C2_GODA_ATKINSON09 | retained_aal_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 64,731.5 | 5,428.57 |
| C2_GODA_ATKINSON09 | retained_aal_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 64,798.1 | 5,481.08 |
| C2_GODA_ATKINSON09 | retained_aal_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 45,461.5 | -3,259.24 |
| I0_PHASE1_INDEPENDENT | retained_tvar_99_5_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 2.45935e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_tvar_99_5_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.18594e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_tvar_99_5_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.18622e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_tvar_99_5_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 9.74318e+06 | 0 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_99_5_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 2.46862e+07 | 92,764.6 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_99_5_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.29565e+07 | 1.09704e+06 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_99_5_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.29704e+07 | 1.10814e+06 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_99_5_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 9.11048e+06 | -632,703 |
| C2_GODA_ATKINSON09 | retained_tvar_99_5_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 2.46647e+07 | 71,216.4 |
| C2_GODA_ATKINSON09 | retained_tvar_99_5_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.2945e+07 | 1.08561e+06 |
| C2_GODA_ATKINSON09 | retained_tvar_99_5_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.29583e+07 | 1.09611e+06 |
| C2_GODA_ATKINSON09 | retained_tvar_99_5_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 9.0914e+06 | -651,784 |
| I0_PHASE1_INDEPENDENT | retained_tvar_tail_capital_99_5_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 2.44705e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_tvar_tail_capital_99_5_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.18001e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_tvar_tail_capital_99_5_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.18029e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_tvar_tail_capital_99_5_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 9.69446e+06 | 0 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_tail_capital_99_5_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 2.45628e+07 | 92,300.7 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_tail_capital_99_5_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.28917e+07 | 1.09156e+06 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_tail_capital_99_5_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.29055e+07 | 1.1026e+06 |
| C1_ALDEA22_SUBDUCTION | retained_tvar_tail_capital_99_5_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 9.06492e+06 | -629,540 |
| C2_GODA_ATKINSON09 | retained_tvar_tail_capital_99_5_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 2.45413e+07 | 70,860.3 |
| C2_GODA_ATKINSON09 | retained_tvar_tail_capital_99_5_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.28803e+07 | 1.08018e+06 |
| C2_GODA_ATKINSON09 | retained_tvar_tail_capital_99_5_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.28935e+07 | 1.09062e+06 |
| C2_GODA_ATKINSON09 | retained_tvar_tail_capital_99_5_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 9.04594e+06 | -648,524 |
| I0_PHASE1_INDEPENDENT | retained_aep_2500yr_pml_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 8.07484e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_aep_2500yr_pml_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 1.9365e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_aep_2500yr_pml_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.89104e+07 | 0 |
| I0_PHASE1_INDEPENDENT | retained_aep_2500yr_pml_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.88111e+07 | 0 |
| C1_ALDEA22_SUBDUCTION | retained_aep_2500yr_pml_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 9.49639e+07 | 1.42155e+07 |
| C1_ALDEA22_SUBDUCTION | retained_aep_2500yr_pml_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 3.32741e+07 | 1.39091e+07 |
| C1_ALDEA22_SUBDUCTION | retained_aep_2500yr_pml_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 3.3126e+07 | 1.42155e+07 |
| C1_ALDEA22_SUBDUCTION | retained_aep_2500yr_pml_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.88111e+07 | 0 |
| C2_GODA_ATKINSON09 | retained_aep_2500yr_pml_2022_usd / NO_REINSURANCE / FULL_CATALOG_2000000_YEARS | 9.58225e+07 | 1.50741e+07 |
| C2_GODA_ATKINSON09 | retained_aep_2500yr_pml_2022_usd / FROZEN_OCCURRENCE_XOL / FULL_CATALOG_2000000_YEARS | 3.40774e+07 | 1.47124e+07 |
| C2_GODA_ATKINSON09 | retained_aep_2500yr_pml_2022_usd / STANDALONE_AGGREGATE / FULL_CATALOG_2000000_YEARS | 3.39845e+07 | 1.50741e+07 |
| C2_GODA_ATKINSON09 | retained_aep_2500yr_pml_2022_usd / STACKED_OCCURRENCE_PLUS_AGGREGATE / FULL_CATALOG_2000000_YEARS | 1.88111e+07 | 0 |
| I0_PHASE1_INDEPENDENT | required_limit_2022_usd / aep_pml / 2500.0 / FULL_CATALOG_2000000_YEARS | 6.18388e+07 | 0 |
| I0_PHASE1_INDEPENDENT | required_limit_2022_usd / aep_tvar / 0.995 / FULL_CATALOG_2000000_YEARS | 6.18388e+07 | 0 |
| C1_ALDEA22_SUBDUCTION | required_limit_2022_usd / aep_pml / 2500.0 / FULL_CATALOG_2000000_YEARS | 7.59006e+07 | 1.40618e+07 |
| C1_ALDEA22_SUBDUCTION | required_limit_2022_usd / aep_tvar / 0.995 / FULL_CATALOG_2000000_YEARS | 7.3322e+07 | 1.14831e+07 |
| C2_GODA_ATKINSON09 | required_limit_2022_usd / aep_pml / 2500.0 / FULL_CATALOG_2000000_YEARS | 7.66651e+07 | 1.48263e+07 |
| C2_GODA_ATKINSON09 | required_limit_2022_usd / aep_tvar / 0.995 / FULL_CATALOG_2000000_YEARS | 7.31917e+07 | 1.13529e+07 |
| I0_PHASE1_INDEPENDENT | payout_aal_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 67,001.5 | 0 |
| C1_ALDEA22_SUBDUCTION | payout_aal_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 67,001.5 | 0 |
| C2_GODA_ATKINSON09 | payout_aal_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 67,001.5 | 0 |
| I0_PHASE1_INDEPENDENT | target_aal_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 63,881.8 | 0 |
| C1_ALDEA22_SUBDUCTION | target_aal_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 59,634.3 | -4,247.51 |
| C2_GODA_ATKINSON09 | target_aal_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 59,660.7 | -4,221.15 |
| I0_PHASE1_INDEPENDENT | expected_protection_shortfall_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 23,098.5 | 0 |
| C1_ALDEA22_SUBDUCTION | expected_protection_shortfall_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 25,940.2 | 2,841.72 |
| C2_GODA_ATKINSON09 | expected_protection_shortfall_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 25,919.5 | 2,821 |
| I0_PHASE1_INDEPENDENT | expected_excess_payout_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 26,218.1 | 0 |
| C1_ALDEA22_SUBDUCTION | expected_excess_payout_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 33,307.4 | 7,089.23 |
| C2_GODA_ATKINSON09 | expected_excess_payout_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 33,260.3 | 7,042.15 |
| I0_PHASE1_INDEPENDENT | event_rmse_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 1.56732e+07 | 0 |
| C1_ALDEA22_SUBDUCTION | event_rmse_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 1.82335e+07 | 2.56026e+06 |
| C2_GODA_ATKINSON09 | event_rmse_2022_usd / EVALUATION_YEARS_1000001_TO_2000000 | 1.82312e+07 | 2.55795e+06 |
| I0_PHASE1_INDEPENDENT | diversification_benefit / aal / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| I0_PHASE1_INDEPENDENT | diversification_benefit / var / 0.99 / FULL_CATALOG_2000000_YEARS | undefined | undefined |
| I0_PHASE1_INDEPENDENT | diversification_benefit / tvar / 0.99 / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| I0_PHASE1_INDEPENDENT | diversification_benefit / var / 0.995 / FULL_CATALOG_2000000_YEARS | undefined | undefined |
| I0_PHASE1_INDEPENDENT | diversification_benefit / tvar / 0.995 / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| C1_ALDEA22_SUBDUCTION | diversification_benefit / aal / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| C1_ALDEA22_SUBDUCTION | diversification_benefit / var / 0.99 / FULL_CATALOG_2000000_YEARS | undefined | undefined |
| C1_ALDEA22_SUBDUCTION | diversification_benefit / tvar / 0.99 / FULL_CATALOG_2000000_YEARS | 0 | 2.22045e-16 |
| C1_ALDEA22_SUBDUCTION | diversification_benefit / var / 0.995 / FULL_CATALOG_2000000_YEARS | undefined | undefined |
| C1_ALDEA22_SUBDUCTION | diversification_benefit / tvar / 0.995 / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| C2_GODA_ATKINSON09 | diversification_benefit / aal / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| C2_GODA_ATKINSON09 | diversification_benefit / var / 0.99 / FULL_CATALOG_2000000_YEARS | undefined | undefined |
| C2_GODA_ATKINSON09 | diversification_benefit / tvar / 0.99 / FULL_CATALOG_2000000_YEARS | -2.22045e-16 | 0 |
| C2_GODA_ATKINSON09 | diversification_benefit / var / 0.995 / FULL_CATALOG_2000000_YEARS | undefined | undefined |
| C2_GODA_ATKINSON09 | diversification_benefit / tvar / 0.995 / FULL_CATALOG_2000000_YEARS | 0 | 2.22045e-16 |

## Attachment identification

| Case | Tied designs | Attachment range (2022 USD) | Selection |
|---|---:|---:|---|
| I0_PHASE1_INDEPENDENT | 15 | 0.00 to 47,812,543.51 | no_unique_selection |
| C1_ALDEA22_SUBDUCTION | 15 | 0.00 to 47,812,543.51 | no_unique_selection |
| C2_GODA_ATKINSON09 | 15 | 0.00 to 47,812,543.51 | no_unique_selection |

## RAROC assumption range

Ranges span the tested price and expense assumptions, not statistical confidence intervals. Use the detailed paired scenario table for matching assumptions.

| Case | Program | Minimum RAROC | Maximum RAROC |
|---|---|---:|---:|
| I0_PHASE1_INDEPENDENT | NO_REINSURANCE | -0.1256% | 0.7036% |
| I0_PHASE1_INDEPENDENT | FROZEN_OCCURRENCE_XOL | -0.8002% | 1.4591% |
| I0_PHASE1_INDEPENDENT | STANDALONE_AGGREGATE | -0.7999% | 1.4587% |
| I0_PHASE1_INDEPENDENT | STACKED_OCCURRENCE_PLUS_AGGREGATE | -1.0831% | 1.7760% |
| C1_ALDEA22_SUBDUCTION | NO_REINSURANCE | -0.1256% | 0.7036% |
| C1_ALDEA22_SUBDUCTION | FROZEN_OCCURRENCE_XOL | -0.6944% | 1.3406% |
| C1_ALDEA22_SUBDUCTION | STANDALONE_AGGREGATE | -0.6931% | 1.3391% |
| C1_ALDEA22_SUBDUCTION | STACKED_OCCURRENCE_PLUS_AGGREGATE | -1.1996% | 1.9065% |
| C2_GODA_ATKINSON09 | NO_REINSURANCE | -0.1256% | 0.7036% |
| C2_GODA_ATKINSON09 | FROZEN_OCCURRENCE_XOL | -0.6944% | 1.3406% |
| C2_GODA_ATKINSON09 | STANDALONE_AGGREGATE | -0.6932% | 1.3392% |
| C2_GODA_ATKINSON09 | STACKED_OCCURRENCE_PLUS_AGGREGATE | -1.2017% | 1.9088% |

## Interpretation

A change in spatial dependence need not increase every loss metric. Read the paired differences together with their sampling intervals, using the same program and period.

The attachment-selection diagnostic does not identify a unique best design under the stored TVaR efficiency criterion. The scenario tables preserve RAROC assumptions and absolute earned premiums rather than treating them as observed pricing.

## Limitations

- **tail_support:** Return-period estimates with order-statistic rank below 20 are diagnostics, not headline estimates.
- **sparse_VaR:** Gross annual VaR at 99% and 99.5% is zero. The corresponding VaR capital and diversification ratios are non-informative.
- **attachment_identification:** The TVaR capital-relief-per-ceded-dollar score ties across the tested attachment grid. No unique best attachment is identified.
- **diversification:** AAL is additive. At the selected TVaR confidence levels the sparse annual loss support also produces additivity; this does not establish absence of diversification at other quantiles.
- **pricing:** RAROC and break-even premiums are assumption grids, not market quotes or central estimates. Matching premium multiples implies different absolute earned premiums across cases.
- **uncertainty:** Paired bootstrap intervals quantify catalog sampling variation under frozen models. Notebook 12 intervals condition on the fitted trigger and omit calibration uncertainty.
- **trigger_grid:** Both selected distance-decay parameters lie at the candidate grid's upper boundary. Optimality outside that grid is not established.
- **parametric_cash:** A source-only payout is identical across cases. Excess payouts and unfunded losses are separate; signed cash-net losses may be negative.
- **comparison_period:** Insurance/reinsurance results use all two million years. Parametric headline results use only the held-out final million years.
- **model_scope:** Results are conditional on the frozen catalog, portfolio, vulnerability, policy terms, and dependence models. They are a research comparison, not a calibrated capital or placement recommendation.
- **legacy_bytes:** Notebook 08 inventory text uses explicit CRLF reconstruction for its original Windows-byte hashes. Notebook 08 and 09 handoffs are pinned to their published LF byte views. Both modes are exposed in the audit; no frozen input is rewritten.

## Evidence

The input audit records every upstream inventory item. The executive, design, uncertainty, and diagnostic CSV tables preserve source references. Figures are supplied as PNG and SVG. The final JSON inventory records output byte sizes and SHA-256 hashes.

Passing Notebook 13 does not create a Git tag, merge a pull request, or publish a release. Those are separate reviewed repository actions.
