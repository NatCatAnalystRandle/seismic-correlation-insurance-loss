"""Frozen magnitude-distance triggers and paired parametric basis-risk metrics.

The trigger uses source information only. Calibration accepts I0 training
recoveries; prediction never accesses losses. Dollars are constant 2022 USD.
"""

from __future__ import annotations

from itertools import product
from typing import Mapping

import numpy as np
import pandas as pd

from tools.reinsurance_capital import CASE_PREFIXES, empirical_pml, empirical_var_tvar

SOURCES = ("INTERFACE", "SLAB")
TRAIN_END = 1_000_000
CATALOG_YEARS = 2_000_000
LOSS_TOLERANCE = 2.0e-6
DISTANCE_SCALE_KM = 50.0
PAYOUT_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
ATTACHMENT_GRID = tuple(float(x) / 4 for x in range(20, 38))
DECAY_GRID = (0.5, 1.0, 1.5, 2.0)
STEP_GRID = (0.25, 0.5, 0.75, 1.0)


def vector(values, name: str, *, nonnegative: bool = True) -> np.ndarray:
    out = np.asarray(values, dtype=np.float64)
    if out.ndim != 1 or not np.isfinite(out).all():
        raise ValueError(f"{name} must be a finite one-dimensional array.")
    if nonnegative and np.any(out < 0):
        raise ValueError(f"{name} must be nonnegative.")
    return out


def year_indices(values, declared_years: int) -> np.ndarray:
    a = vector(values, "catalog_year")
    if declared_years <= 0 or int(declared_years) != declared_years:
        raise ValueError("declared_years must be a positive integer.")
    if np.any(a != np.floor(a)) or np.any(a < 1) or np.any(a > declared_years):
        raise ValueError("Catalog years must be integers within the declared duration.")
    return a.astype(np.int64) - 1


def portfolio_distances(distances: pd.DataFrame, site_ids) -> pd.DataFrame:
    """Reduce authoritative rupture/site distances using the nearest portfolio site."""
    required = {"rupture_id", "site_id", "r_rup_km"}
    if not required.issubset(distances.columns) or distances.empty:
        raise ValueError("Missing authoritative rupture/site distances.")
    if distances[list(required)].isna().any().any():
        raise ValueError("Distance identifiers and values cannot be missing.")
    if distances.duplicated(["rupture_id", "site_id"]).any():
        raise ValueError("Duplicate rupture/site distance row.")
    expected = set(site_ids)
    if not expected or set(distances.site_id) != expected:
        raise ValueError("Distance sites do not match the frozen portfolio.")
    vector(distances.r_rup_km, "r_rup_km")
    grouped = distances.groupby("rupture_id", observed=True, sort=True)
    if not grouped.size().eq(len(expected)).all():
        raise ValueError("Every rupture must contain every frozen portfolio site.")
    return grouped.r_rup_km.agg(
        portfolio_distance_km="min", maximum_site_distance_km="max"
    ).reset_index()


def validate_features(events: pd.DataFrame, declared_years: int = CATALOG_YEARS):
    required = {"occurrence_id", "catalog_year", "source_type", "magnitude", "portfolio_distance_km"}
    if not required.issubset(events.columns) or events.empty:
        raise ValueError("Missing or empty event features.")
    if events[list(required)].isna().any().any() or events.occurrence_id.duplicated().any():
        raise ValueError("Event features require unique, nonmissing occurrence identifiers.")
    if not set(events.source_type).issubset(SOURCES):
        raise ValueError("Unknown source type.")
    year_indices(events.catalog_year, declared_years)
    if np.any(vector(events.magnitude, "magnitude") <= 0):
        raise ValueError("Magnitude must be positive.")
    vector(events.portfolio_distance_km, "portfolio_distance_km")


def tier_payout(magnitude, distance, *, attachment: float, decay: float,
                step: float, principal: float) -> np.ndarray:
    m = vector(magnitude, "magnitude")
    r = vector(distance, "distance")
    if len(m) != len(r):
        raise ValueError("Magnitude and distance arrays must align.")
    terms = np.array([attachment, decay, step, principal], dtype=float)
    if not np.isfinite(terms).all() or decay < 0 or step <= 0 or principal <= 0:
        raise ValueError("Invalid trigger terms.")
    score = m - decay * np.log10(1.0 + r / DISTANCE_SCALE_KM)
    # A threshold equality enters the higher tier, including attachment.
    tier = np.searchsorted(attachment + step * np.arange(4), score, side="right")
    return np.asarray(PAYOUT_FRACTIONS)[tier] * principal


def calibrate_trigger(events: pd.DataFrame, target_column: str, principal: float,
                      *, train_end: int = TRAIN_END, declared_years: int = CATALOG_YEARS,
                      attachment_grid=ATTACHMENT_GRID, decay_grid=DECAY_GRID,
                      step_grid=STEP_GRID) -> tuple[dict, pd.DataFrame]:
    """Select source-specific tiers using I0 training-event squared basis error.

    Only rows in years 1..train_end are accessed for fitting. The objective is
    nominal event payout before annual collateral depletion. Validation/test
    losses do not choose features, thresholds, tiers, or the candidate grid.
    """
    if int(train_end) != train_end or not 1 <= train_end < declared_years:
        raise ValueError("Training split must be inside the catalog duration.")
    year_indices(events.catalog_year, declared_years)
    training = events.loc[events.catalog_year <= train_end].copy()
    validate_features(training, train_end)
    candidates = list(product(attachment_grid, decay_grid, step_grid))
    if not candidates:
        raise ValueError("Candidate grid cannot be empty.")
    selected, rows = {}, []
    for source in SOURCES:
        frame = training.loc[training.source_type.eq(source)]
        if frame.empty:
            raise ValueError(f"No training occurrences for source {source}.")
        target = vector(frame[target_column], "training target")
        if np.any(target > principal + LOSS_TOLERANCE):
            raise ValueError("Training target exceeds frozen occurrence limit.")
        best = None
        for number, (attachment, decay, step) in enumerate(candidates, start=1):
            payout = tier_payout(frame.magnitude, frame.portfolio_distance_km,
                                 attachment=attachment, decay=decay, step=step, principal=principal)
            mse = float(np.mean(((target - payout) / principal) ** 2))
            row = dict(source_type=source, candidate_id=number,
                       attachment_index=float(attachment), distance_decay=float(decay),
                       tier_step=float(step), normalized_training_mse=mse,
                       training_occurrences=len(frame))
            rows.append(row)
            if best is None or mse < best["normalized_training_mse"]:
                best = row.copy()
        selected[source] = best
    spec = dict(schema_version="notebook12_frozen_trigger_v1", train_end=train_end,
                declared_years=declared_years, principal_2022_usd=float(principal),
                distance_definition="minimum authoritative r_rup_km over frozen portfolio sites",
                distance_scale_km=DISTANCE_SCALE_KM, payout_fractions=list(PAYOUT_FRACTIONS),
                index_formula="magnitude - distance_decay * log10(1 + distance_km / 50)",
                objective="I0 training-event mean squared nominal basis error / principal^2",
                tie_break="first candidate in declared attachment, decay, step grid order",
                selected_by_source=selected)
    search = pd.DataFrame(rows)
    search["selected"] = [r.candidate_id == selected[r.source_type]["candidate_id"]
                          for r in search.itertuples()]
    return spec, search


def predict_payout(events: pd.DataFrame, specification: Mapping) -> np.ndarray:
    """Apply frozen terms without reading any indemnity or ground-motion column."""
    validate_features(events, int(specification["declared_years"]))
    if specification["distance_scale_km"] != DISTANCE_SCALE_KM or tuple(specification["payout_fractions"]) != PAYOUT_FRACTIONS:
        raise ValueError("Unsupported frozen trigger definition.")
    out = np.empty(len(events), dtype=float)
    for source in SOURCES:
        mask = events.source_type.eq(source).to_numpy()
        terms = specification["selected_by_source"][source]
        out[mask] = tier_payout(events.loc[mask, "magnitude"], events.loc[mask, "portfolio_distance_km"],
                               attachment=terms["attachment_index"], decay=terms["distance_decay"],
                               step=terms["tier_step"], principal=specification["principal_2022_usd"])
    return out


def apply_annual_collateral(events: pd.DataFrame, nominal_payout, principal: float,
                            *, declared_years: int = CATALOG_YEARS) -> np.ndarray:
    """One-year principal, no reinstatement; process frozen within-year event times.

    Each catalog year is a separate one-year issuance. Equal-time ties use
    occurrence_id. Output is aligned to input rows, independent of row order.
    """
    p = vector(nominal_payout, "nominal payout")
    years = year_indices(events.catalog_year, declared_years)
    time = vector(events.time_within_year, "time_within_year")
    if not (len(p) == len(time) == len(years)) or np.any(time >= 1):
        raise ValueError("Payouts must align and event times must lie in [0, 1).")
    if not np.isfinite(principal) or principal <= 0 or np.any(p > principal):
        raise ValueError("Nominal payout must obey positive principal.")
    if events.occurrence_id.isna().any() or events.occurrence_id.duplicated().any():
        raise ValueError("Collateral allocation needs unique occurrence identifiers.")
    order = np.lexsort((events.occurrence_id.astype(str).to_numpy(), time, years))
    out = np.zeros(len(p))
    previous, used = -1, 0.0
    for i in order:
        if years[i] != previous:
            previous, used = years[i], 0.0
        out[i] = min(p[i], max(principal - used, 0.0))
        used = min(used + out[i], principal)
    return out


def annual_basis_series(events: pd.DataFrame, payouts: Mapping[str, np.ndarray],
                         *, declared_years: int = CATALOG_YEARS) -> pd.DataFrame:
    """Include zero years; distinguish signed cash net loss from unfunded loss."""
    idx = year_indices(events.catalog_year, declared_years)
    annual = pd.DataFrame({"catalog_year": np.arange(1, declared_years + 1),
                           "catalog_occurrence_count": np.bincount(idx, minlength=declared_years)})
    def total(a):
        a = vector(a, "event amounts", nonnegative=False)
        if len(a) != len(idx):
            raise ValueError("Event amounts must align with years.")
        return np.bincount(idx, weights=a, minlength=declared_years)
    for name, p in payouts.items():
        vector(p, "payout")
        annual[f"{name}_payout_aep_2022_usd"] = total(p)
    for prefix in CASE_PREFIXES.values():
        gross = vector(events[f"{prefix}_gross_insured_loss_2022_usd"], "gross")
        target = vector(events[f"{prefix}_frozen_occurrence_ceded_loss_2022_usd"], "target")
        if np.any(target > gross + LOSS_TOLERANCE):
            raise ValueError("Indemnity target exceeds gross loss.")
        annual[f"{prefix}_gross_aep_2022_usd"] = total(gross)
        annual[f"{prefix}_target_aep_2022_usd"] = total(target)
        annual[f"{prefix}_benchmark_retained_aep_2022_usd"] = total(np.maximum(gross - target, 0.0))
        # Event shortfall is summed, so excess payout at another event cannot hide it.
        p = payouts["collateralized"]
        annual[f"{prefix}_shortfall_sum_2022_usd"] = total(np.maximum(target - p, 0.0))
        annual[f"{prefix}_excess_sum_2022_usd"] = total(np.maximum(p - target, 0.0))
        net = annual[f"{prefix}_gross_aep_2022_usd"] - annual["collateralized_payout_aep_2022_usd"]
        annual[f"{prefix}_cash_net_aep_2022_usd"] = net
        annual[f"{prefix}_unfunded_aep_2022_usd"] = np.maximum(net, 0.0)
        annual[f"{prefix}_surplus_aep_2022_usd"] = np.maximum(-net, 0.0)
    return annual


def basis_metrics(target, payout, gross, *, declared_years: int,
                  tolerance: float = LOSS_TOLERANCE) -> dict:
    target, payout, gross = (vector(a, n) for a, n in [(target, "target"), (payout, "payout"), (gross, "gross")])
    if not len(target) == len(payout) == len(gross) or not len(target) or declared_years <= 0 or int(declared_years) != declared_years:
        raise ValueError("Metric inputs must align and have positive duration.")
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid classification tolerance.")
    if np.any(target > gross + tolerance):
        raise ValueError("Target exceeds gross loss.")
    basis = target - payout
    shortfall, excess = np.maximum(basis, 0.0), np.maximum(-basis, 0.0)
    loss_event, pay_event = target > tolerance, payout > tolerance
    fn, fp = loss_event & ~pay_event, ~loss_event & pay_event
    ratio = lambda numerator, denominator: float(numerator / denominator) if denominator else np.nan
    correlation = float(np.corrcoef(target, payout)[0, 1]) if np.std(target) > 0 and np.std(payout) > 0 else np.nan
    return dict(occurrences=len(target), declared_years=declared_years,
                payout_aal_2022_usd=float(payout.sum() / declared_years),
                target_aal_2022_usd=float(target.sum() / declared_years),
                signed_basis_aal_2022_usd=float(basis.sum() / declared_years),
                expected_protection_shortfall_2022_usd=float(shortfall.sum() / declared_years),
                expected_excess_payout_2022_usd=float(excess.sum() / declared_years),
                event_mae_2022_usd=float(np.mean(np.abs(basis))),
                event_rmse_2022_usd=float(np.sqrt(np.mean(basis ** 2))),
                event_payout_target_correlation=correlation,
                false_negative_occurrences=int(fn.sum()), false_positive_occurrences=int(fp.sum()),
                false_negative_probability_per_occurrence=float(fn.mean()),
                false_positive_probability_per_occurrence=float(fp.mean()),
                false_negative_probability_given_target=ratio(fn.sum(), loss_event.sum()),
                false_positive_probability_given_payout=ratio(fp.sum(), pay_event.sum()),
                false_negative_annual_occurrence_rate=float(fn.sum() / declared_years),
                false_positive_annual_occurrence_rate=float(fp.sum() / declared_years),
                conditional_mean_shortfall_given_target_2022_usd=ratio(shortfall[loss_event].sum(), loss_event.sum()),
                target_positive_occurrences=int(loss_event.sum()), payout_positive_occurrences=int(pay_event.sum()))


def tail_rows(annual: pd.DataFrame, *, return_periods=(100, 250, 500, 1000, 2500, 5000, 10000, 50000, 100000, 1000000)) -> pd.DataFrame:
    """Return empirical tail statistics for one specified training/test/full period."""
    rows = []
    for prefix in CASE_PREFIXES.values():
        for kind in ("gross", "benchmark_retained", "cash_net", "unfunded"):
            a = vector(annual[f"{prefix}_{kind}_aep_2022_usd"], kind, nonnegative=kind != "cash_net")
            for rp in return_periods:
                if rp > len(a):
                    continue
                value, rank = empirical_pml(a, rp)
                rows.append(dict(case_prefix=prefix, loss_basis=kind, metric="aep_pml", parameter=rp,
                                 value_2022_usd=value, tail_count=rank, headline_supported=rank >= 20))
            for confidence in (0.99, 0.995):
                var, tvar, count = empirical_var_tvar(a, confidence)
                for name, value in [("var", var), ("tvar", tvar), ("tvar_minus_mean", tvar - float(a.mean()))]:
                    rows.append(dict(case_prefix=prefix, loss_basis=kind, metric=name, parameter=confidence,
                                     value_2022_usd=value, tail_count=count, headline_supported=count >= 20))
    return pd.DataFrame(rows)
