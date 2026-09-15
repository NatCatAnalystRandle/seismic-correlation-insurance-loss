"""Paired Phase 2 damage, ground-up loss, and policy-loss calculations.

The module preserves the Phase 1 structural, nonstructural drift, and
nonstructural acceleration damage streams.  One occurrence-site uniform per
component is reused across I0, C1, and C2, so only the SA(0.4 s) demand changes
between dependence cases.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Sequence

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray
from scipy.special import ndtr


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int8]

DAMAGE_STATES = ("None", "Slight", "Moderate", "Extensive", "Complete")
EXCEEDANCE_STATES = DAMAGE_STATES[1:]

CASE_PREFIXES = {
    "I0_PHASE1_INDEPENDENT": "i0",
    "C1_ALDEA22_SUBDUCTION": "c1",
    "C2_GODA_ATKINSON09": "c2",
}

COMPONENT_NAMESPACES = {
    "structural": "notebook5_structural_damage_v1",
    "nsd": "notebook5_nonstructural_drift_damage_v1",
    "nsa": "notebook5_nonstructural_acceleration_damage_v1",
}

GROUND_MOTION_REQUIRED_COLUMNS = [
    "catalog_year",
    "catalog_event_id",
    "occurrence_ordinal",
    "occurrence_id",
    "rupture_ordinal",
    "rupture_template_event_id",
    "rupture_id",
    "source_type",
    "magnitude",
    "site_ordinal",
    "site_id",
    "i0_sa0p4_simulated_g",
    "c1_sa0p4_simulated_g",
    "c2_sa0p4_simulated_g",
]

IDENTIFIER_COLUMNS = [
    "catalog_year",
    "catalog_event_id",
    "occurrence_ordinal",
    "occurrence_id",
    "rupture_ordinal",
    "rupture_template_event_id",
    "rupture_id",
    "source_type",
    "magnitude",
    "site_ordinal",
    "site_id",
]

POLICY_PARAMETER_COLUMNS = [
    "policy_covered",
    "covered_loss_share",
    "building_replacement_value_2022_usd",
    "deductible_amount_2022_usd",
    "policy_limit_amount_2022_usd",
    "coinsurance_share",
]

CASE_OUTPUT_SUFFIXES = [
    "structural_damage_state",
    "nsd_damage_state",
    "nsa_damage_state",
    "structural_ground_up_loss_2022_usd",
    "nsd_ground_up_loss_2022_usd",
    "nsa_ground_up_loss_2022_usd",
    "total_ground_up_loss_2022_usd",
    "deductible_absorbed_loss_2022_usd",
    "policy_limit_absorbed_loss_2022_usd",
    "coinsurance_absorbed_loss_2022_usd",
    "gross_insured_loss_2022_usd",
    "uninsured_loss_2022_usd",
]

PAIRED_LOSS_OUTPUT_COLUMNS = IDENTIFIER_COLUMNS + POLICY_PARAMETER_COLUMNS + [
    f"{prefix}_{suffix}"
    for prefix in CASE_PREFIXES.values()
    for suffix in CASE_OUTPUT_SUFFIXES
]


def fragility_columns(prefix: str) -> tuple[list[str], list[str]]:
    """Return the four median and beta columns for one damage component."""

    base = "" if prefix == "structural" else f"{prefix}_"
    medians = [
        f"{base}{state.lower()}_median_sa0p4_g" for state in EXCEEDANCE_STATES
    ]
    betas = [f"{base}{state.lower()}_beta_ln" for state in EXCEEDANCE_STATES]
    return medians, betas


def repair_ratio_columns(prefix: str) -> list[str]:
    """Return the five sampled repair-ratio columns for one component."""

    return [f"{prefix}_ratio_{state.lower()}" for state in DAMAGE_STATES]


SITE_PARAMETER_COLUMNS = [
    "site_ordinal",
    "site_id",
    *fragility_columns("structural")[0],
    *fragility_columns("structural")[1],
    *fragility_columns("nsd")[0],
    *fragility_columns("nsd")[1],
    *fragility_columns("nsa")[0],
    *fragility_columns("nsa")[1],
    *repair_ratio_columns("structural"),
    *repair_ratio_columns("nsd"),
    *repair_ratio_columns("nsa"),
    *POLICY_PARAMETER_COLUMNS,
]


@dataclass(frozen=True)
class DamageLossDiagnostics:
    """Row-level diagnostics returned for a paired batch."""

    rows: int
    occurrences: int
    site_count: int
    minimum_raw_probability: dict[str, float]
    maximum_component_reconciliation_error_2022_usd: float
    maximum_policy_reconciliation_error_2022_usd: float
    maximum_uninsured_decomposition_error_2022_usd: float
    nonfinite_output_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def deterministic_uniforms(
    occurrence_ids: Sequence[object] | pd.Series,
    site_ids: Sequence[object] | pd.Series,
    namespace: str,
) -> FloatArray:
    """Reproduce a frozen Phase 1 occurrence-site uniform stream exactly."""

    occurrence_values = np.asarray(occurrence_ids, dtype=str)
    site_values = np.asarray(site_ids, dtype=str)
    if occurrence_values.ndim != 1 or site_values.shape != occurrence_values.shape:
        raise ValueError("occurrence_ids and site_ids must be equal one-dimensional arrays.")
    if not namespace:
        raise ValueError("namespace must be a nonempty string.")

    uniforms = np.empty(len(occurrence_values), dtype=np.float64)
    denominator = float(2**64)
    for index, (occurrence_id, site_id) in enumerate(
        zip(occurrence_values, site_values, strict=True)
    ):
        digest = hashlib.sha256(
            f"{namespace}|{occurrence_id}|{site_id}".encode("utf-8")
        ).digest()
        integer = int.from_bytes(digest[:8], byteorder="big", signed=False)
        uniforms[index] = (integer + 0.5) / denominator
    return uniforms


def damage_state_probabilities(
    sa0p4_g: ArrayLike,
    medians_sa0p4_g: ArrayLike,
    betas_ln: ArrayLike,
    *,
    probability_tolerance: float = 1.0e-12,
) -> tuple[FloatArray, float]:
    """Calculate five mutually exclusive lognormal damage-state probabilities."""

    sa = np.asarray(sa0p4_g, dtype=np.float64)
    medians = np.asarray(medians_sa0p4_g, dtype=np.float64)
    betas = np.asarray(betas_ln, dtype=np.float64)
    if sa.ndim != 1 or medians.shape != (len(sa), 4) or betas.shape != medians.shape:
        raise ValueError("SA must be length n and fragility matrices must have shape (n, 4).")
    if not np.isfinite(sa).all() or np.any(sa <= 0.0):
        raise ValueError("All SA0P4 values must be finite and positive.")
    if not np.isfinite(medians).all() or np.any(medians <= 0.0):
        raise ValueError("All fragility medians must be finite and positive.")
    if not np.isfinite(betas).all() or np.any(betas <= 0.0):
        raise ValueError("All fragility betas must be finite and positive.")

    exceedance = ndtr((np.log(sa)[:, None] - np.log(medians)) / betas)
    raw = np.column_stack(
        [
            1.0 - exceedance[:, 0],
            exceedance[:, 0] - exceedance[:, 1],
            exceedance[:, 1] - exceedance[:, 2],
            exceedance[:, 2] - exceedance[:, 3],
            exceedance[:, 3],
        ]
    )
    minimum_raw = float(raw.min())
    if minimum_raw < -probability_tolerance:
        raise RuntimeError(
            "Fragility curves produced materially negative mutually exclusive "
            f"probabilities. Minimum={minimum_raw:.6e}."
        )
    probabilities = np.clip(raw, 0.0, 1.0)
    totals = probabilities.sum(axis=1)
    if np.any(totals <= 0.0):
        raise RuntimeError("At least one damage-probability row has zero total mass.")
    probabilities /= totals[:, None]
    return probabilities, minimum_raw


def sample_damage_states(probabilities: ArrayLike, uniforms: ArrayLike) -> IntArray:
    """Sample the Phase 1 inverse-categorical damage state."""

    values = np.asarray(probabilities, dtype=np.float64)
    random_values = np.asarray(uniforms, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 5:
        raise ValueError("probabilities must have shape (n, 5).")
    if random_values.shape != (values.shape[0],):
        raise ValueError("uniforms must contain one value per probability row.")
    if not np.isfinite(values).all() or np.any(values < 0.0):
        raise ValueError("probabilities must be finite and nonnegative.")
    if not np.allclose(values.sum(axis=1), 1.0, atol=2.0e-12, rtol=0.0):
        raise ValueError("Each probability row must sum to one.")
    if not np.isfinite(random_values).all() or np.any(
        (random_values <= 0.0) | (random_values >= 1.0)
    ):
        raise ValueError("uniforms must be finite and strictly between zero and one.")

    cumulative = np.cumsum(values, axis=1)
    cumulative[:, -1] = 1.0
    states = (random_values[:, None] > cumulative).sum(axis=1)
    return np.minimum(states, 4).astype(np.int8)


def apply_policy_terms(
    ground_up_loss: ArrayLike,
    policy_covered: ArrayLike,
    covered_loss_share: ArrayLike,
    deductible_amount: ArrayLike,
    policy_limit_amount: ArrayLike,
    coinsurance_share: ArrayLike,
) -> dict[str, FloatArray]:
    """Apply the exact Phase 1 building-level policy waterfall."""

    ground_up = np.asarray(ground_up_loss, dtype=np.float64)
    covered = np.asarray(policy_covered, dtype=bool)
    covered_share = np.asarray(covered_loss_share, dtype=np.float64)
    deductible = np.asarray(deductible_amount, dtype=np.float64)
    policy_limit = np.asarray(policy_limit_amount, dtype=np.float64)
    coinsurance = np.asarray(coinsurance_share, dtype=np.float64)
    shapes = {
        ground_up.shape,
        covered.shape,
        covered_share.shape,
        deductible.shape,
        policy_limit.shape,
        coinsurance.shape,
    }
    if ground_up.ndim != 1 or len(shapes) != 1:
        raise ValueError("All policy inputs must be equal one-dimensional arrays.")
    numeric = np.column_stack(
        [ground_up, covered_share, deductible, policy_limit, coinsurance]
    )
    if not np.isfinite(numeric).all():
        raise ValueError("Policy inputs must be finite.")
    if np.any(ground_up < 0.0) or np.any(deductible < 0.0) or np.any(policy_limit < 0.0):
        raise ValueError("Loss, deductible, and limit amounts must be nonnegative.")
    if np.any((covered_share < 0.0) | (covered_share > 1.0)) or np.any(
        (coinsurance < 0.0) | (coinsurance > 1.0)
    ):
        raise ValueError("Coverage and coinsurance shares must lie in [0, 1].")

    eligible = np.where(covered, ground_up * covered_share, 0.0)
    uncovered = ground_up - eligible
    deductible_absorbed = np.minimum(eligible, deductible)
    after_deductible = np.maximum(eligible - deductible, 0.0)
    limited = np.minimum(after_deductible, policy_limit)
    limit_absorbed = np.maximum(after_deductible - policy_limit, 0.0)
    gross = limited * coinsurance
    coinsurance_absorbed = limited * (1.0 - coinsurance)
    uninsured = ground_up - gross
    decomposed_uninsured = (
        uncovered + deductible_absorbed + limit_absorbed + coinsurance_absorbed
    )
    return {
        "eligible_ground_up_loss_2022_usd": eligible,
        "uncovered_ground_up_loss_2022_usd": uncovered,
        "deductible_absorbed_loss_2022_usd": deductible_absorbed,
        "loss_after_deductible_2022_usd": after_deductible,
        "limited_loss_2022_usd": limited,
        "policy_limit_absorbed_loss_2022_usd": limit_absorbed,
        "coinsurance_absorbed_loss_2022_usd": coinsurance_absorbed,
        "gross_insured_loss_2022_usd": gross,
        "uninsured_loss_2022_usd": uninsured,
        "decomposed_uninsured_loss_2022_usd": decomposed_uninsured,
    }


def build_site_parameter_table(
    structural_fragility: pd.DataFrame,
    nonstructural_fragility: pd.DataFrame,
    structural_values: pd.DataFrame,
    nonstructural_values: pd.DataFrame,
    policy_terms: pd.DataFrame,
    *,
    expected_site_ids: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Join and validate all frozen Phase 1 site-level model parameters."""

    sources = {
        "structural_fragility": structural_fragility.copy(),
        "nonstructural_fragility": nonstructural_fragility.copy(),
        "structural_values": structural_values.copy(),
        "nonstructural_values": nonstructural_values.copy(),
        "policy_terms": policy_terms.copy(),
    }
    for label, frame in sources.items():
        if "site_id" not in frame:
            raise KeyError(f"{label} is missing site_id.")
        frame["site_id"] = frame["site_id"].astype(str).str.strip()
        if frame["site_id"].duplicated().any():
            raise ValueError(f"{label} contains duplicate site_id values.")

    structural_medians, structural_betas = fragility_columns("structural")
    nsd_medians, nsd_betas = fragility_columns("nsd")
    nsa_medians, nsa_betas = fragility_columns("nsa")
    selections = {
        "structural_fragility": ["site_id", *structural_medians, *structural_betas],
        "nonstructural_fragility": [
            "site_id",
            *nsd_medians,
            *nsd_betas,
            *nsa_medians,
            *nsa_betas,
        ],
        "structural_values": [
            "site_id",
            *repair_ratio_columns("structural"),
        ],
        "nonstructural_values": [
            "site_id",
            *repair_ratio_columns("nsd"),
            *repair_ratio_columns("nsa"),
        ],
        "policy_terms": ["site_id", "site_ordinal", *POLICY_PARAMETER_COLUMNS],
    }
    for label, columns in selections.items():
        missing = [column for column in columns if column not in sources[label]]
        if missing:
            raise KeyError(f"{label} is missing columns: {missing}")

    table = sources["policy_terms"][selections["policy_terms"]].copy()
    for label in (
        "structural_fragility",
        "nonstructural_fragility",
        "structural_values",
        "nonstructural_values",
    ):
        table = table.merge(
            sources[label][selections[label]],
            on="site_id",
            how="left",
            validate="one_to_one",
        )

    table["site_ordinal"] = pd.to_numeric(table["site_ordinal"], errors="raise").astype(int)
    table = table.sort_values("site_ordinal").reset_index(drop=True)
    if not np.array_equal(table["site_ordinal"].to_numpy(), np.arange(len(table))):
        raise ValueError("Policy site_ordinal values must be consecutive from zero.")
    if expected_site_ids is not None:
        expected = np.asarray(expected_site_ids, dtype=str)
        if len(expected) != len(table) or not np.array_equal(
            table["site_id"].to_numpy(dtype=str), expected
        ):
            raise ValueError("Site parameters do not match the frozen Notebook 08 site order.")

    numeric_columns = [
        column
        for column in SITE_PARAMETER_COLUMNS
        if column not in {"site_id", "policy_covered"}
    ]
    table[numeric_columns] = table[numeric_columns].apply(
        pd.to_numeric, errors="raise"
    )
    if not np.isfinite(table[numeric_columns].to_numpy(dtype=np.float64)).all():
        raise ValueError("Site parameters contain nonfinite numeric values.")
    covered_values = table["policy_covered"]
    if pd.api.types.is_bool_dtype(covered_values):
        table["policy_covered"] = covered_values.astype(bool)
    else:
        normalized = covered_values.astype("string").str.strip().str.lower()
        valid_tokens = {"true", "false", "1", "0", "yes", "no", "y", "n"}
        invalid = sorted(set(normalized.dropna()).difference(valid_tokens))
        if invalid or normalized.isna().any():
            raise ValueError(f"policy_covered contains invalid values: {invalid}")
        table["policy_covered"] = normalized.isin({"true", "1", "yes", "y"})

    for component in COMPONENT_NAMESPACES:
        medians, betas = fragility_columns(component)
        ratios = repair_ratio_columns(component)
        if np.any(table[medians].to_numpy(dtype=float) <= 0.0):
            raise ValueError(f"{component} fragility medians must be positive.")
        if np.any(table[betas].to_numpy(dtype=float) <= 0.0):
            raise ValueError(f"{component} fragility betas must be positive.")
        ratio_matrix = table[ratios].to_numpy(dtype=float)
        if np.any((ratio_matrix < 0.0) | (ratio_matrix > 1.0)):
            raise ValueError(f"{component} repair ratios must lie in [0, 1].")
        if np.any(np.diff(ratio_matrix, axis=1) < -1.0e-12):
            raise ValueError(f"{component} repair ratios must be nondecreasing.")

    complete = sum(
        table[f"{component}_ratio_complete"].to_numpy(dtype=float)
        for component in COMPONENT_NAMESPACES
    )
    if not np.allclose(complete, 1.0, atol=1.0e-12, rtol=0.0):
        raise ValueError("Complete-state component repair ratios must sum to one.")
    replacement = table["building_replacement_value_2022_usd"].to_numpy(dtype=float)
    deductible = table["deductible_amount_2022_usd"].to_numpy(dtype=float)
    policy_limit = table["policy_limit_amount_2022_usd"].to_numpy(dtype=float)
    covered_share = table["covered_loss_share"].to_numpy(dtype=float)
    coinsurance = table["coinsurance_share"].to_numpy(dtype=float)
    if np.any(replacement <= 0.0):
        raise ValueError("Building replacement values must be positive.")
    if np.any(deductible < 0.0) or np.any(policy_limit < 0.0):
        raise ValueError("Deductible and policy-limit amounts must be nonnegative.")
    if np.any((covered_share < 0.0) | (covered_share > 1.0)):
        raise ValueError("Covered-loss shares must lie in [0, 1].")
    if np.any((coinsurance < 0.0) | (coinsurance > 1.0)):
        raise ValueError("Coinsurance shares must lie in [0, 1].")
    return table[SITE_PARAMETER_COLUMNS]


def validate_occurrence_site_order(
    frame: pd.DataFrame,
    *,
    expected_site_ids: Sequence[str],
) -> int:
    """Validate complete contiguous occurrences in the frozen site order."""

    missing = [column for column in GROUND_MOTION_REQUIRED_COLUMNS if column not in frame]
    if missing:
        raise ValueError(f"Ground-motion batch is missing columns: {missing}")
    site_ids = np.asarray(expected_site_ids, dtype=str)
    site_count = len(site_ids)
    if site_count == 0 or len(frame) == 0 or len(frame) % site_count:
        raise ValueError("A batch must contain complete nonempty occurrence-site groups.")
    occurrences = len(frame) // site_count
    observed_ordinals = frame["site_ordinal"].to_numpy(dtype=int)
    if not np.array_equal(observed_ordinals, np.tile(np.arange(site_count), occurrences)):
        raise ValueError("Rows are not in canonical site_ordinal order.")
    if not np.array_equal(
        frame["site_id"].astype(str).to_numpy(), np.tile(site_ids, occurrences)
    ):
        raise ValueError("Rows do not match the frozen site_id order.")
    occurrence_matrix = frame["occurrence_id"].astype(str).to_numpy().reshape(
        occurrences, site_count
    )
    if not all(np.all(row == row[0]) for row in occurrence_matrix):
        raise ValueError("An occurrence group contains multiple occurrence_id values.")
    return occurrences


def build_paired_damage_loss_batch(
    ground_motion: pd.DataFrame,
    site_parameters: pd.DataFrame,
    *,
    probability_tolerance: float = 1.0e-12,
) -> tuple[pd.DataFrame, DamageLossDiagnostics]:
    """Calculate paired sampled damage and financial loss for complete events."""

    missing_parameters = [
        column for column in SITE_PARAMETER_COLUMNS if column not in site_parameters
    ]
    if missing_parameters:
        raise ValueError(f"Site parameter table is missing columns: {missing_parameters}")
    parameters = site_parameters.sort_values("site_ordinal").reset_index(drop=True)
    expected_site_ids = parameters["site_id"].astype(str).tolist()
    occurrences = validate_occurrence_site_order(
        ground_motion, expected_site_ids=expected_site_ids
    )
    row_ordinals = ground_motion["site_ordinal"].to_numpy(dtype=int)
    if np.any((row_ordinals < 0) | (row_ordinals >= len(parameters))):
        raise ValueError("Ground-motion site_ordinal values are out of range.")

    occurrence_ids = ground_motion["occurrence_id"].astype(str).to_numpy()
    site_ids = ground_motion["site_id"].astype(str).to_numpy()
    uniforms = {
        component: deterministic_uniforms(occurrence_ids, site_ids, namespace)
        for component, namespace in COMPONENT_NAMESPACES.items()
    }

    output = ground_motion[IDENTIFIER_COLUMNS].copy()
    for column in POLICY_PARAMETER_COLUMNS:
        output[column] = parameters[column].to_numpy()[row_ordinals]

    replacement = output["building_replacement_value_2022_usd"].to_numpy(
        dtype=np.float64
    )
    minimum_raw: dict[str, float] = {}
    maximum_component_error = 0.0
    maximum_policy_error = 0.0
    maximum_uninsured_error = 0.0
    numeric_outputs: list[FloatArray] = []

    for case_name, case_prefix in CASE_PREFIXES.items():
        sa = ground_motion[f"{case_prefix}_sa0p4_simulated_g"].to_numpy(
            dtype=np.float64
        )
        component_losses: dict[str, FloatArray] = {}
        for component in COMPONENT_NAMESPACES:
            median_columns, beta_columns = fragility_columns(component)
            medians = parameters[median_columns].to_numpy(dtype=np.float64)[row_ordinals]
            betas = parameters[beta_columns].to_numpy(dtype=np.float64)[row_ordinals]
            probabilities, minimum = damage_state_probabilities(
                sa,
                medians,
                betas,
                probability_tolerance=probability_tolerance,
            )
            minimum_raw[f"{case_prefix}_{component}"] = minimum
            states = sample_damage_states(probabilities, uniforms[component])
            ratio_matrix = parameters[repair_ratio_columns(component)].to_numpy(
                dtype=np.float64
            )[row_ordinals]
            sampled_ratios = np.take_along_axis(
                ratio_matrix, states[:, None], axis=1
            )[:, 0]
            losses = replacement * sampled_ratios
            output[f"{case_prefix}_{component}_damage_state"] = states
            output[f"{case_prefix}_{component}_ground_up_loss_2022_usd"] = losses
            component_losses[component] = losses
            numeric_outputs.append(losses)

        ground_up = sum(component_losses.values())
        component_error = np.abs(
            ground_up
            - component_losses["structural"]
            - component_losses["nsd"]
            - component_losses["nsa"]
        )
        maximum_component_error = max(
            maximum_component_error, float(component_error.max(initial=0.0))
        )
        if np.any(ground_up > replacement + 1.0e-6):
            raise RuntimeError(f"{case_name} ground-up loss exceeds replacement value.")

        policy = apply_policy_terms(
            ground_up,
            output["policy_covered"].to_numpy(dtype=bool),
            output["covered_loss_share"].to_numpy(dtype=float),
            output["deductible_amount_2022_usd"].to_numpy(dtype=float),
            output["policy_limit_amount_2022_usd"].to_numpy(dtype=float),
            output["coinsurance_share"].to_numpy(dtype=float),
        )
        output[f"{case_prefix}_total_ground_up_loss_2022_usd"] = ground_up
        for suffix in (
            "deductible_absorbed_loss_2022_usd",
            "policy_limit_absorbed_loss_2022_usd",
            "coinsurance_absorbed_loss_2022_usd",
            "gross_insured_loss_2022_usd",
            "uninsured_loss_2022_usd",
        ):
            output[f"{case_prefix}_{suffix}"] = policy[suffix]
            numeric_outputs.append(policy[suffix])

        policy_error = np.abs(
            ground_up
            - policy["gross_insured_loss_2022_usd"]
            - policy["uninsured_loss_2022_usd"]
        )
        uninsured_error = np.abs(
            policy["uninsured_loss_2022_usd"]
            - policy["decomposed_uninsured_loss_2022_usd"]
        )
        maximum_policy_error = max(
            maximum_policy_error, float(policy_error.max(initial=0.0))
        )
        maximum_uninsured_error = max(
            maximum_uninsured_error, float(uninsured_error.max(initial=0.0))
        )
        numeric_outputs.append(ground_up)

    numeric_matrix = np.column_stack(numeric_outputs)
    diagnostics = DamageLossDiagnostics(
        rows=int(len(output)),
        occurrences=int(occurrences),
        site_count=int(len(parameters)),
        minimum_raw_probability=minimum_raw,
        maximum_component_reconciliation_error_2022_usd=maximum_component_error,
        maximum_policy_reconciliation_error_2022_usd=maximum_policy_error,
        maximum_uninsured_decomposition_error_2022_usd=maximum_uninsured_error,
        nonfinite_output_count=int(np.count_nonzero(~np.isfinite(numeric_matrix))),
    )
    return output[PAIRED_LOSS_OUTPUT_COLUMNS], diagnostics


def summarize_occurrences(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate one or more complete paired batches to occurrence level."""

    required = set(PAIRED_LOSS_OUTPUT_COLUMNS)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Paired loss frame is missing columns: {missing}")
    group_columns = [
        "catalog_year",
        "catalog_event_id",
        "occurrence_ordinal",
        "occurrence_id",
        "rupture_ordinal",
        "rupture_template_event_id",
        "rupture_id",
        "source_type",
        "magnitude",
    ]
    grouped = frame.groupby(group_columns, sort=False, observed=True)
    summary = grouped.size().rename("sites").reset_index()
    for case_prefix in CASE_PREFIXES.values():
        loss_columns = [
            f"{case_prefix}_{suffix}"
            for suffix in CASE_OUTPUT_SUFFIXES
            if suffix.endswith("loss_2022_usd")
        ]
        loss_summary = grouped[loss_columns].sum().reset_index()
        summary = summary.merge(
            loss_summary, on=group_columns, how="left", validate="one_to_one"
        )
        for component in COMPONENT_NAMESPACES:
            state_column = f"{case_prefix}_{component}_damage_state"
            damaged = (
                frame.assign(_damaged=frame[state_column].to_numpy(dtype=int) > 0)
                .groupby(group_columns, sort=False, observed=True)["_damaged"]
                .sum()
                .rename(f"{case_prefix}_{component}_damaged_buildings")
                .reset_index()
            )
            summary = summary.merge(
                damaged, on=group_columns, how="left", validate="one_to_one"
            )
    return summary.sort_values("occurrence_ordinal").reset_index(drop=True)
