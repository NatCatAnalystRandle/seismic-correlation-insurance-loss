"""Reinsurance, tail-risk, and capital utilities for Phase 2 Notebook 11.

The functions in this module are deliberately independent of notebook state.
They apply transparent occurrence and annual aggregate excess-of-loss terms,
construct complete annual loss series, calculate fixed-count empirical VaR and
TVaR, and support paired catalog-year bootstrap comparisons.

All financial arrays are expressed in constant 2022 U.S. dollars.  No premium,
expense, or regulatory-capital assumptions are embedded in this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

CASE_PREFIXES = {
    "I0_PHASE1_INDEPENDENT": "i0",
    "C1_ALDEA22_SUBDUCTION": "c1",
    "C2_GODA_ATKINSON09": "c2",
}

RETURN_PERIODS = (
    50,
    100,
    200,
    250,
    500,
    1_000,
    2_000,
    2_500,
    5_000,
    10_000,
    20_000,
    50_000,
    100_000,
    200_000,
    500_000,
    1_000_000,
    2_000_000,
)

CONFIDENCE_LEVELS = (0.99, 0.995)


@dataclass(frozen=True)
class RequiredLimitResult:
    """Result of a monotone minimum occurrence-limit search."""

    feasible: bool
    required_limit_2022_usd: float
    achieved_metric_2022_usd: float
    target_metric_2022_usd: float
    attachment_2022_usd: float
    maximum_tested_limit_2022_usd: float
    iterations: int
    limit_tolerance_2022_usd: float
    target_kind: str
    target_parameter: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _float_array(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains nonfinite values.")
    return array


def _validate_layer_terms(
    attachment: float,
    limit: float,
    participation: float,
) -> tuple[float, float, float]:
    values = np.asarray([attachment, limit, participation], dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("Layer terms must be finite.")
    attachment = float(attachment)
    limit = float(limit)
    participation = float(participation)
    if attachment < 0.0 or limit < 0.0:
        raise ValueError("Attachment and limit must be nonnegative.")
    if not 0.0 <= participation <= 1.0:
        raise ValueError("Participation must lie between zero and one.")
    return attachment, limit, participation


def apply_occurrence_xol(
    subject_loss: ArrayLike,
    attachment: float,
    limit: float,
    participation: float = 1.0,
    *,
    classification_tolerance: float = 0.0,
) -> dict[str, FloatArray | NDArray[np.bool_]]:
    """Apply an occurrence excess-of-loss layer elementwise.

    The participated recovery is

    ``participation * min(max(subject - attachment, 0), limit)``.
    """

    subject = _float_array(subject_loss, name="subject_loss")
    attachment, limit, participation = _validate_layer_terms(
        attachment, limit, participation
    )
    classification_tolerance = float(classification_tolerance)
    if (
        not np.isfinite(classification_tolerance)
        or classification_tolerance < 0.0
    ):
        raise ValueError(
            "classification_tolerance must be finite and nonnegative."
        )
    if np.any(subject < 0.0):
        raise ValueError("Subject losses must be nonnegative.")

    layer_before_participation = np.minimum(
        np.maximum(subject - attachment, 0.0), limit
    )
    ceded = participation * layer_before_participation
    retained = subject - ceded
    triggered = subject > attachment
    exhausted = (limit > 0.0) & (
        subject >= attachment + limit - classification_tolerance
    )
    return {
        "layer_loss_before_participation_2022_usd": layer_before_participation,
        "ceded_loss_2022_usd": ceded,
        "retained_loss_2022_usd": retained,
        "triggered": triggered,
        "exhausted": exhausted,
    }


def apply_aggregate_stop_loss(
    annual_subject_loss: ArrayLike,
    attachment: float,
    limit: float,
    participation: float = 1.0,
    *,
    classification_tolerance: float = 0.0,
) -> dict[str, FloatArray | NDArray[np.bool_]]:
    """Apply an annual aggregate stop-loss to one loss value per year."""

    return apply_occurrence_xol(
        annual_subject_loss,
        attachment,
        limit,
        participation,
        classification_tolerance=classification_tolerance,
    )


def annualize_occurrence_program(
    catalog_year: ArrayLike,
    gross_occurrence_loss: ArrayLike,
    ceded_occurrence_loss: ArrayLike,
    declared_years: int,
) -> dict[str, NDArray[np.generic]]:
    """Aggregate event-level gross, ceded, and retained losses by catalog year."""

    years = np.asarray(catalog_year, dtype=np.int64)
    gross = _float_array(gross_occurrence_loss, name="gross_occurrence_loss")
    ceded = _float_array(ceded_occurrence_loss, name="ceded_occurrence_loss")
    if years.ndim != 1 or len(years) != len(gross) or len(gross) != len(ceded):
        raise ValueError("Catalog-year and occurrence-loss arrays must align.")
    if declared_years <= 0:
        raise ValueError("declared_years must be positive.")
    if len(years) and (years.min() < 1 or years.max() > declared_years):
        raise ValueError("Catalog years lie outside the declared duration.")
    if np.any(gross < 0.0) or np.any(ceded < 0.0):
        raise ValueError("Occurrence losses must be nonnegative.")
    if np.any(ceded - gross > 1.0e-8):
        raise ValueError("Ceded occurrence loss cannot exceed gross loss.")

    retained = gross - ceded
    indices = years - 1
    occurrence_count = np.bincount(
        indices, minlength=declared_years
    ).astype(np.int16, copy=False)

    def annual_sum(values: FloatArray) -> FloatArray:
        return np.bincount(
            indices,
            weights=values,
            minlength=declared_years,
        ).astype(np.float64, copy=False)

    def annual_maximum(values: FloatArray) -> FloatArray:
        output = np.zeros(declared_years, dtype=np.float64)
        np.maximum.at(output, indices, values)
        return output

    return {
        "catalog_occurrence_count": occurrence_count,
        "gross_aep_2022_usd": annual_sum(gross),
        "gross_oep_2022_usd": annual_maximum(gross),
        "ceded_aep_2022_usd": annual_sum(ceded),
        "ceded_oep_2022_usd": annual_maximum(ceded),
        "retained_aep_2022_usd": annual_sum(retained),
        "retained_oep_2022_usd": annual_maximum(retained),
    }


def empirical_pml(losses: ArrayLike, return_period: int) -> tuple[float, int]:
    """Return the descending empirical order statistic used for a PML."""

    values = _float_array(losses, name="losses")
    if len(values) == 0:
        raise ValueError("At least one loss is required.")
    if return_period <= 0:
        raise ValueError("return_period must be positive.")
    rank = int(math.ceil(len(values) / return_period))
    rank = max(rank, 1)
    index = len(values) - rank
    value = float(np.partition(values, index)[index])
    return value, rank


def empirical_var_tvar(
    losses: ArrayLike,
    confidence: float,
) -> tuple[float, float, int]:
    """Calculate fixed-count empirical VaR and TVaR.

    For ``N`` annual losses and confidence ``q``, the tail contains exactly
    ``ceil(N * (1-q))`` largest observations.  VaR is the smallest value in
    that fixed-count tail and TVaR is its arithmetic mean.  Boundary ties are
    therefore included only to the extent required by the fixed tail count.
    """

    values = _float_array(losses, name="losses")
    if len(values) == 0:
        raise ValueError("At least one loss is required.")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one.")
    tail_count = max(1, int(math.ceil(len(values) * (1.0 - confidence))))
    index = len(values) - tail_count
    tail = np.partition(values, index)[index:]
    return float(tail.min()), float(tail.mean()), tail_count


def sparse_var_tvar(
    explicit_annual_losses: ArrayLike,
    declared_years: int,
    confidence: float,
) -> tuple[float, float, int]:
    """Calculate fixed-count VaR/TVaR with implicit zero-loss years."""

    values = _float_array(
        explicit_annual_losses, name="explicit_annual_losses"
    )
    if declared_years < len(values) or declared_years <= 0:
        raise ValueError("declared_years must include all explicit rows.")
    if np.any(values < 0.0):
        raise ValueError("Annual losses must be nonnegative.")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one.")
    tail_count = max(1, int(math.ceil(declared_years * (1.0 - confidence))))
    selected_count = min(tail_count, len(values))
    if selected_count == 0:
        return 0.0, 0.0, tail_count
    index = len(values) - selected_count
    tail = np.partition(values, index)[index:]
    var = float(tail.min()) if selected_count == tail_count else 0.0
    tvar = float(tail.sum(dtype=np.float64) / tail_count)
    return var, tvar, tail_count


def annual_program_metrics(
    gross_aep: ArrayLike,
    ceded_aep: ArrayLike,
    retained_aep: ArrayLike,
    *,
    confidences: Sequence[float] = CONFIDENCE_LEVELS,
) -> dict[str, float | int | bool]:
    """Calculate expected loss, volatility, VaR, TVaR, and capital metrics."""

    gross = _float_array(gross_aep, name="gross_aep")
    ceded = _float_array(ceded_aep, name="ceded_aep")
    retained = _float_array(retained_aep, name="retained_aep")
    if not (len(gross) == len(ceded) == len(retained)) or len(gross) == 0:
        raise ValueError("Annual program arrays must have equal positive length.")
    if np.any(gross < 0.0) or np.any(ceded < 0.0) or np.any(retained < 0.0):
        raise ValueError("Annual losses must be nonnegative.")
    if np.max(np.abs(gross - ceded - retained), initial=0.0) > 1.0e-6:
        raise ValueError("Gross, ceded, and retained annual losses do not reconcile.")

    gross_aal = float(gross.mean(dtype=np.float64))
    ceded_aal = float(ceded.mean(dtype=np.float64))
    retained_aal = float(retained.mean(dtype=np.float64))
    output: dict[str, float | int | bool] = {
        "catalog_years": int(len(gross)),
        "gross_aal_2022_usd": gross_aal,
        "ceded_aal_2022_usd": ceded_aal,
        "retained_aal_2022_usd": retained_aal,
        "gross_annual_standard_deviation_2022_usd": float(np.std(gross)),
        "ceded_annual_standard_deviation_2022_usd": float(np.std(ceded)),
        "retained_annual_standard_deviation_2022_usd": float(np.std(retained)),
        "maximum_gross_aep_2022_usd": float(gross.max(initial=0.0)),
        "maximum_ceded_aep_2022_usd": float(ceded.max(initial=0.0)),
        "maximum_retained_aep_2022_usd": float(retained.max(initial=0.0)),
        "ceded_share_of_gross_aal": ceded_aal / gross_aal if gross_aal else 0.0,
    }
    for confidence in confidences:
        label = f"{confidence * 100.0:g}".replace(".", "_")
        gross_var, gross_tvar, tail_count = empirical_var_tvar(gross, confidence)
        ceded_var, ceded_tvar, _ = empirical_var_tvar(ceded, confidence)
        retained_var, retained_tvar, _ = empirical_var_tvar(retained, confidence)
        gross_var_capital = gross_var - gross_aal
        retained_var_capital = retained_var - retained_aal
        gross_tail_capital = gross_tvar - gross_aal
        retained_tail_capital = retained_tvar - retained_aal
        output.update(
            {
                f"tail_count_{label}": tail_count,
                f"gross_var_{label}_2022_usd": gross_var,
                f"ceded_var_{label}_2022_usd": ceded_var,
                f"retained_var_{label}_2022_usd": retained_var,
                f"gross_tvar_{label}_2022_usd": gross_tvar,
                f"ceded_tvar_{label}_2022_usd": ceded_tvar,
                f"retained_tvar_{label}_2022_usd": retained_tvar,
                f"gross_var_economic_capital_{label}_2022_usd": gross_var_capital,
                f"retained_var_economic_capital_{label}_2022_usd": retained_var_capital,
                f"gross_var_economic_capital_floored_{label}_2022_usd": max(
                    gross_var_capital, 0.0
                ),
                f"retained_var_economic_capital_floored_{label}_2022_usd": max(
                    retained_var_capital, 0.0
                ),
                f"gross_tvar_tail_capital_{label}_2022_usd": gross_tail_capital,
                f"retained_tvar_tail_capital_{label}_2022_usd": retained_tail_capital,
                f"var_capital_relief_{label}_2022_usd": (
                    gross_var_capital - retained_var_capital
                ),
                f"tvar_capital_relief_{label}_2022_usd": (
                    gross_tail_capital - retained_tail_capital
                ),
                f"var_capital_informative_{label}": gross_var > 0.0,
            }
        )
    return output


def diversification_from_sparse_units(
    frame: pd.DataFrame,
    *,
    unit_column: str,
    year_column: str,
    loss_column: str,
    portfolio_annual_losses: ArrayLike,
    declared_years: int,
    confidences: Sequence[float] = CONFIDENCE_LEVELS,
) -> pd.DataFrame:
    """Calculate AAL, VaR, and TVaR diversification across portfolio units."""

    required = {unit_column, year_column, loss_column}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Sparse unit frame is missing columns: {missing}")
    portfolio = _float_array(
        portfolio_annual_losses, name="portfolio_annual_losses"
    )
    if len(portfolio) != declared_years:
        raise ValueError("Portfolio annual series length does not match declared_years.")

    grouped = (
        frame.groupby([unit_column, year_column], sort=False, observed=True)[
            loss_column
        ]
        .sum()
        .reset_index()
    )
    unit_aals: list[float] = []
    unit_vars: dict[float, list[float]] = {q: [] for q in confidences}
    unit_tvars: dict[float, list[float]] = {q: [] for q in confidences}
    for _, group in grouped.groupby(unit_column, sort=False, observed=True):
        losses = group[loss_column].to_numpy(dtype=np.float64)
        unit_aals.append(float(losses.sum(dtype=np.float64) / declared_years))
        for confidence in confidences:
            var, tvar, _ = sparse_var_tvar(losses, declared_years, confidence)
            unit_vars[confidence].append(var)
            unit_tvars[confidence].append(tvar)

    rows: list[dict[str, object]] = []
    portfolio_aal = float(portfolio.mean(dtype=np.float64))
    sum_unit_aal = float(np.sum(unit_aals, dtype=np.float64))
    rows.append(
        {
            "risk_measure": "aal",
            "confidence": np.nan,
            "portfolio_risk_2022_usd": portfolio_aal,
            "sum_standalone_risk_2022_usd": sum_unit_aal,
            "diversification_benefit": (
                1.0 - portfolio_aal / sum_unit_aal if sum_unit_aal else np.nan
            ),
            "units": int(grouped[unit_column].nunique()),
        }
    )
    for confidence in confidences:
        portfolio_var, portfolio_tvar, _ = empirical_var_tvar(
            portfolio, confidence
        )
        for risk_measure, portfolio_risk, unit_risks in [
            ("var", portfolio_var, unit_vars[confidence]),
            ("tvar", portfolio_tvar, unit_tvars[confidence]),
        ]:
            sum_units = float(np.sum(unit_risks, dtype=np.float64))
            rows.append(
                {
                    "risk_measure": risk_measure,
                    "confidence": confidence,
                    "portfolio_risk_2022_usd": portfolio_risk,
                    "sum_standalone_risk_2022_usd": sum_units,
                    "diversification_benefit": (
                        1.0 - portfolio_risk / sum_units if sum_units else np.nan
                    ),
                    "units": int(grouped[unit_column].nunique()),
                }
            )
    return pd.DataFrame(rows)


def _weighted_tail_statistic(
    sorted_losses_descending: FloatArray,
    sorted_weights: IntArray,
    tail_count: int,
) -> tuple[float, float]:
    if tail_count <= 0:
        raise ValueError("tail_count must be positive.")
    cumulative = np.cumsum(sorted_weights, dtype=np.int64)
    boundary = int(np.searchsorted(cumulative, tail_count, side="left"))
    if boundary >= len(sorted_losses_descending):
        raise ValueError("Bootstrap weights do not contain the requested tail count.")
    count_before = int(cumulative[boundary - 1]) if boundary else 0
    weighted_sum = float(
        np.dot(
            sorted_losses_descending[:boundary],
            sorted_weights[:boundary].astype(np.float64),
        )
    )
    boundary_count = tail_count - count_before
    boundary_value = float(sorted_losses_descending[boundary])
    weighted_sum += boundary_value * boundary_count
    return boundary_value, weighted_sum / tail_count


def paired_bootstrap_differences(
    annual_series: Mapping[str, ArrayLike],
    comparisons: Sequence[tuple[str, str]],
    metric_specs: Sequence[Mapping[str, object]],
    *,
    replicates: int = 300,
    seed: int = 11_2026,
) -> pd.DataFrame:
    """Bootstrap paired catalog-year differences using a sparse multinomial.

    Years that are zero for every supplied series are collapsed into one zero
    category.  Each replicate draws exactly the declared number of catalog
    years, and the same category weights are reused across every case so the
    paired experimental design is preserved.
    """

    if not annual_series:
        raise ValueError("annual_series cannot be empty.")
    if replicates < 2:
        raise ValueError("At least two bootstrap replicates are required.")
    labels = list(annual_series)
    arrays = [_float_array(annual_series[label], name=label) for label in labels]
    declared_years = len(arrays[0])
    if declared_years == 0 or any(len(array) != declared_years for array in arrays):
        raise ValueError("All annual series must have the same positive length.")
    if any(np.any(array < 0.0) for array in arrays):
        raise ValueError("Annual loss series must be nonnegative.")
    label_index = {label: index for index, label in enumerate(labels)}
    for case_label, baseline_label in comparisons:
        if case_label not in label_index or baseline_label not in label_index:
            raise ValueError("Bootstrap comparison references an unknown series.")

    matrix = np.column_stack(arrays)
    explicit_mask = np.any(matrix != 0.0, axis=1)
    explicit = matrix[explicit_mask]
    explicit_rows = len(explicit)
    zero_years = declared_years - explicit_rows
    categories = np.vstack([explicit, np.zeros((1, len(labels)), dtype=float)])
    probabilities = np.concatenate(
        [
            np.full(explicit_rows, 1.0 / declared_years, dtype=float),
            np.array([zero_years / declared_years], dtype=float),
        ]
    )
    original_weights = np.concatenate(
        [np.ones(explicit_rows, dtype=np.int64), np.array([zero_years], dtype=np.int64)]
    )
    sort_orders = [np.argsort(categories[:, index])[::-1] for index in range(len(labels))]

    def evaluate(weights: IntArray) -> dict[tuple[str, str], float]:
        values: dict[tuple[str, str], float] = {}
        for label, column_index in label_index.items():
            column = categories[:, column_index]
            order = sort_orders[column_index]
            sorted_values = column[order]
            sorted_weights = weights[order]
            for specification in metric_specs:
                name = str(specification["name"])
                kind = str(specification["kind"])
                if kind == "mean":
                    metric = float(
                        np.dot(column, weights.astype(np.float64)) / declared_years
                    )
                elif kind == "pml":
                    return_period = int(specification["return_period"])
                    tail_count = max(1, int(math.ceil(declared_years / return_period)))
                    metric, _ = _weighted_tail_statistic(
                        sorted_values, sorted_weights, tail_count
                    )
                elif kind in {"var", "tvar"}:
                    confidence = float(specification["confidence"])
                    tail_count = max(
                        1,
                        int(math.ceil(declared_years * (1.0 - confidence))),
                    )
                    var, tvar = _weighted_tail_statistic(
                        sorted_values, sorted_weights, tail_count
                    )
                    metric = var if kind == "var" else tvar
                else:
                    raise ValueError(f"Unsupported bootstrap metric kind: {kind}")
                values[(label, name)] = metric
        return values

    original = evaluate(original_weights)
    replicate_differences: dict[tuple[str, str, str], list[float]] = {
        (case, baseline, str(specification["name"])): []
        for case, baseline in comparisons
        for specification in metric_specs
    }
    rng = np.random.default_rng(seed)
    for _ in range(replicates):
        weights = rng.multinomial(declared_years, probabilities).astype(np.int64)
        evaluated = evaluate(weights)
        for case, baseline in comparisons:
            for specification in metric_specs:
                name = str(specification["name"])
                replicate_differences[(case, baseline, name)].append(
                    evaluated[(case, name)] - evaluated[(baseline, name)]
                )

    rows: list[dict[str, object]] = []
    specs_by_name = {str(item["name"]): item for item in metric_specs}
    for (case, baseline, name), samples in replicate_differences.items():
        case_value = original[(case, name)]
        baseline_value = original[(baseline, name)]
        sample_array = np.asarray(samples, dtype=np.float64)
        specification = specs_by_name[name]
        rows.append(
            {
                "case_series": case,
                "baseline_series": baseline,
                "metric_name": name,
                "metric_kind": str(specification["kind"]),
                "case_value_2022_usd": case_value,
                "baseline_value_2022_usd": baseline_value,
                "absolute_change_2022_usd": case_value - baseline_value,
                "percent_change": (
                    100.0 * (case_value / baseline_value - 1.0)
                    if baseline_value != 0.0
                    else np.nan
                ),
                "bootstrap_standard_error_2022_usd": float(
                    sample_array.std(ddof=1)
                ),
                "bootstrap_ci_lower_2022_usd": float(
                    np.quantile(sample_array, 0.025)
                ),
                "bootstrap_ci_upper_2022_usd": float(
                    np.quantile(sample_array, 0.975)
                ),
                "bootstrap_replicates": replicates,
                "bootstrap_seed": seed,
                "bootstrap_method": (
                    "paired multinomial resampling of catalog years with one "
                    "collapsed all-zero category"
                ),
            }
        )
    return pd.DataFrame(rows)


def minimum_occurrence_limit_for_target(
    catalog_year: ArrayLike,
    gross_occurrence_loss: ArrayLike,
    *,
    declared_years: int,
    attachment: float,
    target_kind: str,
    target_parameter: float,
    target_metric_2022_usd: float,
    limit_tolerance_2022_usd: float = 1_000.0,
    maximum_iterations: int = 80,
) -> RequiredLimitResult:
    """Find the minimum full-participation limit meeting a retained-risk target."""

    years = np.asarray(catalog_year, dtype=np.int64)
    gross = _float_array(gross_occurrence_loss, name="gross_occurrence_loss")
    if years.ndim != 1 or len(years) != len(gross):
        raise ValueError("Catalog years and gross losses must align.")
    if declared_years <= 0 or (len(years) and (years.min() < 1 or years.max() > declared_years)):
        raise ValueError("Catalog years lie outside the declared duration.")
    attachment, _, _ = _validate_layer_terms(attachment, 0.0, 1.0)
    if target_metric_2022_usd < 0.0 or not np.isfinite(target_metric_2022_usd):
        raise ValueError("Target metric must be finite and nonnegative.")
    if limit_tolerance_2022_usd <= 0.0:
        raise ValueError("Limit tolerance must be positive.")
    if target_kind not in {"aep_pml", "aep_tvar"}:
        raise ValueError("target_kind must be 'aep_pml' or 'aep_tvar'.")

    indices = years - 1

    def evaluate(limit: float) -> float:
        result = apply_occurrence_xol(gross, attachment, limit, 1.0)
        retained = np.asarray(result["retained_loss_2022_usd"], dtype=np.float64)
        annual = np.bincount(
            indices,
            weights=retained,
            minlength=declared_years,
        ).astype(np.float64, copy=False)
        if target_kind == "aep_pml":
            value, _ = empirical_pml(annual, int(target_parameter))
            return value
        _, value, _ = empirical_var_tvar(annual, float(target_parameter))
        return value

    maximum_limit = float(max(gross.max(initial=0.0) - attachment, 0.0))
    no_cover_metric = evaluate(0.0)
    if no_cover_metric <= target_metric_2022_usd:
        return RequiredLimitResult(
            feasible=True,
            required_limit_2022_usd=0.0,
            achieved_metric_2022_usd=no_cover_metric,
            target_metric_2022_usd=float(target_metric_2022_usd),
            attachment_2022_usd=attachment,
            maximum_tested_limit_2022_usd=maximum_limit,
            iterations=0,
            limit_tolerance_2022_usd=float(limit_tolerance_2022_usd),
            target_kind=target_kind,
            target_parameter=float(target_parameter),
        )

    best_metric = evaluate(maximum_limit)
    if best_metric > target_metric_2022_usd:
        return RequiredLimitResult(
            feasible=False,
            required_limit_2022_usd=float("nan"),
            achieved_metric_2022_usd=best_metric,
            target_metric_2022_usd=float(target_metric_2022_usd),
            attachment_2022_usd=attachment,
            maximum_tested_limit_2022_usd=maximum_limit,
            iterations=0,
            limit_tolerance_2022_usd=float(limit_tolerance_2022_usd),
            target_kind=target_kind,
            target_parameter=float(target_parameter),
        )

    lower = 0.0
    upper = maximum_limit
    iterations = 0
    while upper - lower > limit_tolerance_2022_usd and iterations < maximum_iterations:
        midpoint = 0.5 * (lower + upper)
        metric = evaluate(midpoint)
        if metric <= target_metric_2022_usd:
            upper = midpoint
            best_metric = metric
        else:
            lower = midpoint
        iterations += 1

    best_metric = evaluate(upper)
    return RequiredLimitResult(
        feasible=True,
        required_limit_2022_usd=upper,
        achieved_metric_2022_usd=best_metric,
        target_metric_2022_usd=float(target_metric_2022_usd),
        attachment_2022_usd=attachment,
        maximum_tested_limit_2022_usd=maximum_limit,
        iterations=iterations,
        limit_tolerance_2022_usd=float(limit_tolerance_2022_usd),
        target_kind=target_kind,
        target_parameter=float(target_parameter),
    )
