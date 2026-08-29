"""Paired Phase 2 ground-motion construction.

This module regenerates the frozen Phase 1 latent streams and applies the
validated Notebook 08 spatial factors without changing the event catalog,
between-event residuals, GMM medians, tau, phi, or site ordering.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from tools.spatial_correlation import CASE_C1, CASE_C2, CASE_I0


FloatArray = NDArray[np.float64]

BASE_RANDOM_SEED = 20260731
SEED_CELL_LABEL = "cell19"
EXPECTED_SITE_COUNT = 470

CASE_PREFIXES = {
    CASE_I0: "i0",
    CASE_C1: "c1",
    CASE_C2: "c2",
}

BASELINE_REQUIRED_COLUMNS = [
    "catalog_year",
    "catalog_event_id",
    "occurrence_ordinal",
    "occurrence_id",
    "rupture_ordinal",
    "rupture_template_event_id",
    "rupture_id",
    "source_type",
    "gmm_name",
    "magnitude",
    "site_ordinal",
    "site_id",
    "site_longitude",
    "site_latitude",
    "r_rup_km",
    "vs30_mps",
    "period_s",
    "cross_imt_rho",
    "eta_pga",
    "epsilon_pga",
    "pga_epi_off_mean_ln_g",
    "pga_tau_ln",
    "pga_phi_ln",
    "pga_simulated_ln_g",
    "pga_simulated_g",
    "eta_sa0p4",
    "epsilon_sa0p4",
    "sa0p4_epi_off_mean_ln_g",
    "sa0p4_tau_ln",
    "sa0p4_phi_ln",
    "sa0p4_simulated_ln_g",
    "sa0p4_simulated_g",
]

COMMON_OUTPUT_COLUMNS = [
    "catalog_year",
    "catalog_event_id",
    "occurrence_ordinal",
    "occurrence_id",
    "rupture_ordinal",
    "rupture_template_event_id",
    "rupture_id",
    "source_type",
    "gmm_name",
    "magnitude",
    "site_ordinal",
    "site_id",
    "site_longitude",
    "site_latitude",
    "r_rup_km",
    "vs30_mps",
    "period_s",
    "cross_imt_rho",
    "eta_pga",
    "eta_sa0p4",
]

CASE_OUTPUT_SUFFIXES = [
    "epsilon_pga",
    "epsilon_sa0p4",
    "pga_simulated_ln_g",
    "pga_simulated_g",
    "sa0p4_simulated_ln_g",
    "sa0p4_simulated_g",
]

PAIRED_OUTPUT_COLUMNS = COMMON_OUTPUT_COLUMNS + [
    f"{prefix}_{suffix}"
    for prefix in CASE_PREFIXES.values()
    for suffix in CASE_OUTPUT_SUFFIXES
]


@dataclass(frozen=True)
class CaseFactors:
    """Spatial roots required by one dependence case."""

    pga_square_root: FloatArray
    conditional_square_root: FloatArray


@dataclass(frozen=True)
class BatchDiagnostics:
    """Exact validation diagnostics for one paired event-site batch."""

    rows: int
    occurrences: int
    site_count: int
    maximum_i0_epsilon_pga_error: float
    maximum_i0_epsilon_sa0p4_error: float
    maximum_i0_pga_ln_error: float
    maximum_i0_sa0p4_ln_error: float
    maximum_repeated_eta_pga_error: float
    maximum_repeated_eta_sa0p4_error: float
    nonfinite_output_count: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def stable_seed(*parts: object) -> tuple[int, str]:
    """Reproduce the frozen Notebook 04 128-bit seed derivation."""

    payload = "|".join(str(part) for part in parts).encode("utf-8")
    raw = hashlib.sha256(payload).digest()[:16]
    return int.from_bytes(raw, byteorder="little", signed=False), raw.hex()


def seed_from_hex(seed_hex: str) -> int:
    """Recover the little-endian integer used to initialize PCG64DXSM."""

    if not isinstance(seed_hex, str) or len(seed_hex) != 32:
        raise ValueError("A frozen seed must be a 32-character hexadecimal string.")
    try:
        raw = bytes.fromhex(seed_hex)
    except ValueError as exc:
        raise ValueError("The frozen seed contains non-hexadecimal characters.") from exc
    return int.from_bytes(raw, byteorder="little", signed=False)


def rng_from_seed(seed: int) -> np.random.Generator:
    """Return the exact Phase 1 random-number generator."""

    return np.random.Generator(np.random.PCG64DXSM(int(seed)))


def site_seed_for_occurrence(
    occurrence_id: str,
    rupture_id: str,
    *,
    base_random_seed: int = BASE_RANDOM_SEED,
) -> tuple[int, str]:
    """Derive an occurrence's frozen site-stream seed."""

    return stable_seed(
        int(base_random_seed),
        SEED_CELL_LABEL,
        str(occurrence_id),
        str(rupture_id),
        "site",
    )


def regenerate_site_latent_batch(
    site_seed_hexes: Sequence[str],
    *,
    site_count: int = EXPECTED_SITE_COUNT,
) -> tuple[FloatArray, FloatArray]:
    """Regenerate the two frozen site-normal vectors for many occurrences."""

    if site_count <= 0:
        raise ValueError("site_count must be positive.")
    z1 = np.empty((len(site_seed_hexes), site_count), dtype=np.float64)
    z2 = np.empty_like(z1)
    for index, seed_hex in enumerate(site_seed_hexes):
        generator = rng_from_seed(seed_from_hex(seed_hex))
        z1[index] = generator.standard_normal(site_count)
        z2[index] = generator.standard_normal(site_count)
    return z1, z2


def transform_latent_batch(
    z1: ArrayLike,
    z2: ArrayLike,
    factors: CaseFactors,
    *,
    cross_imt_rho: float,
) -> tuple[FloatArray, FloatArray]:
    """Apply one case's spatial and cross-IMT transforms to row-wise events."""

    first = np.asarray(z1, dtype=np.float64)
    second = np.asarray(z2, dtype=np.float64)
    if first.ndim != 2 or second.shape != first.shape:
        raise ValueError("z1 and z2 must be equal two-dimensional arrays.")
    pga_root = np.asarray(factors.pga_square_root, dtype=np.float64)
    conditional_root = np.asarray(
        factors.conditional_square_root, dtype=np.float64
    )
    expected_shape = (first.shape[1], first.shape[1])
    if pga_root.shape != expected_shape or conditional_root.shape != expected_shape:
        raise ValueError(
            "Each spatial square root must be square and match the site count."
        )
    if not -1.0 <= cross_imt_rho <= 1.0:
        raise ValueError("cross_imt_rho must lie in [-1, 1].")

    if np.array_equal(pga_root, np.eye(first.shape[1])):
        epsilon_pga = first.copy()
    else:
        epsilon_pga = first @ pga_root.T
    if np.array_equal(conditional_root, np.eye(first.shape[1])):
        conditional = second.copy()
    else:
        conditional = second @ conditional_root.T
    epsilon_sa0p4 = (
        cross_imt_rho * epsilon_pga
        + np.sqrt(1.0 - cross_imt_rho**2) * conditional
    )
    return epsilon_pga, epsilon_sa0p4


def simulate_log_ground_motion(
    mean_ln: ArrayLike,
    tau_ln: ArrayLike,
    phi_ln: ArrayLike,
    eta: ArrayLike,
    epsilon: ArrayLike,
) -> tuple[FloatArray, FloatArray]:
    """Evaluate mu + tau*eta + phi*epsilon and its exponential."""

    mean = np.asarray(mean_ln, dtype=np.float64)
    tau = np.asarray(tau_ln, dtype=np.float64)
    phi = np.asarray(phi_ln, dtype=np.float64)
    residual = np.asarray(epsilon, dtype=np.float64)
    event = np.asarray(eta, dtype=np.float64)
    if mean.ndim != 2 or tau.shape != mean.shape or phi.shape != mean.shape:
        raise ValueError("mean_ln, tau_ln, and phi_ln must have one common 2D shape.")
    if residual.shape != mean.shape:
        raise ValueError("epsilon must match the event-by-site ground-motion shape.")
    if event.shape != (mean.shape[0],):
        raise ValueError("eta must contain one value per event occurrence.")
    simulated_ln = mean + tau * event[:, None] + phi * residual
    return simulated_ln, np.exp(simulated_ln)


def load_case_factors(
    path: str | Path,
    *,
    expected_site_count: int = EXPECTED_SITE_COUNT,
) -> dict[str, CaseFactors]:
    """Load and validate Notebook 08's frozen spatial-factor artifact."""

    factor_path = Path(path)
    if not factor_path.is_file():
        raise FileNotFoundError(f"Missing Notebook 08 factor artifact: {factor_path}")
    prefixes = CASE_PREFIXES
    cases: dict[str, CaseFactors] = {}
    with np.load(factor_path, allow_pickle=False) as payload:
        for case_name, prefix in prefixes.items():
            pga_key = f"{prefix}_pga_square_root"
            conditional_key = f"{prefix}_conditional_square_root"
            if pga_key not in payload or conditional_key not in payload:
                raise KeyError(
                    f"Factor artifact is missing {pga_key} or {conditional_key}."
                )
            pga = np.asarray(payload[pga_key], dtype=np.float64)
            conditional = np.asarray(payload[conditional_key], dtype=np.float64)
            expected_shape = (expected_site_count, expected_site_count)
            if pga.shape != expected_shape or conditional.shape != expected_shape:
                raise ValueError(
                    f"{case_name} factors do not have shape {expected_shape}."
                )
            if not np.isfinite(pga).all() or not np.isfinite(conditional).all():
                raise ValueError(f"{case_name} factors contain nonfinite values.")
            cases[case_name] = CaseFactors(pga, conditional)
    return cases


def _reshape_column(
    frame: pd.DataFrame,
    column: str,
    occurrences: int,
    site_count: int,
    *,
    dtype: object = np.float64,
) -> NDArray:
    return frame[column].to_numpy(dtype=dtype).reshape(occurrences, site_count)


def validate_occurrence_site_order(
    frame: pd.DataFrame,
    *,
    site_count: int,
    expected_site_ids: Sequence[str] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Validate contiguous occurrence groups in canonical site order."""

    missing = [column for column in BASELINE_REQUIRED_COLUMNS if column not in frame]
    if missing:
        raise ValueError(f"Baseline field batch is missing columns: {missing}")
    if len(frame) == 0 or len(frame) % site_count != 0:
        raise ValueError("A baseline batch must contain complete occurrence-site groups.")
    occurrences = len(frame) // site_count
    expected_ordinals = np.tile(np.arange(site_count), occurrences)
    observed_ordinals = frame["site_ordinal"].to_numpy(dtype=int)
    if not np.array_equal(observed_ordinals, expected_ordinals):
        raise ValueError("Baseline rows are not in canonical site_ordinal order.")

    occurrence_matrix = frame["occurrence_id"].astype(str).to_numpy().reshape(
        occurrences, site_count
    )
    rupture_matrix = frame["rupture_id"].astype(str).to_numpy().reshape(
        occurrences, site_count
    )
    if not all(np.all(row == row[0]) for row in occurrence_matrix):
        raise ValueError("An occurrence group contains multiple occurrence_id values.")
    if not all(np.all(row == row[0]) for row in rupture_matrix):
        raise ValueError("An occurrence group contains multiple rupture_id values.")

    if expected_site_ids is not None:
        if len(expected_site_ids) != site_count:
            raise ValueError(
                "expected_site_ids must contain exactly one identifier per site."
            )
        expected = np.tile(np.asarray(expected_site_ids, dtype=str), occurrences)
        observed = frame["site_id"].astype(str).to_numpy()
        if not np.array_equal(observed, expected):
            raise ValueError("Baseline site_id values do not match Notebook 08 order.")

    return (
        occurrences,
        occurrence_matrix[:, 0].tolist(),
        rupture_matrix[:, 0].tolist(),
    )


def build_paired_field_batch(
    baseline: pd.DataFrame,
    factors: Mapping[str, CaseFactors],
    *,
    expected_site_ids: Sequence[str] | None = None,
    site_count: int = EXPECTED_SITE_COUNT,
    baseline_tolerance: float = 3.0e-12,
) -> tuple[pd.DataFrame, BatchDiagnostics]:
    """Create paired I0, C1, and C2 fields from a complete Phase 1 batch."""

    required_cases = set(CASE_PREFIXES)
    if set(factors) != required_cases:
        raise ValueError(
            f"factors must contain exactly {sorted(required_cases)}."
        )
    occurrences, occurrence_ids, rupture_ids = validate_occurrence_site_order(
        baseline,
        site_count=site_count,
        expected_site_ids=expected_site_ids,
    )

    rho_values = baseline["cross_imt_rho"].to_numpy(dtype=np.float64)
    rho = float(rho_values[0])
    if not np.all(rho_values == rho):
        raise ValueError("cross_imt_rho is not constant within the baseline batch.")
    if not np.isfinite(rho) or not -1.0 <= rho <= 1.0:
        raise ValueError("cross_imt_rho must be finite and lie in [-1, 1].")

    seed_hexes = [
        site_seed_for_occurrence(occurrence_id, rupture_id)[1]
        for occurrence_id, rupture_id in zip(occurrence_ids, rupture_ids)
    ]
    z1, z2 = regenerate_site_latent_batch(seed_hexes, site_count=site_count)
    expected_i0_sa = rho * z1 + np.sqrt(1.0 - rho**2) * z2
    baseline_epsilon_pga = _reshape_column(
        baseline, "epsilon_pga", occurrences, site_count
    )
    baseline_epsilon_sa = _reshape_column(
        baseline, "epsilon_sa0p4", occurrences, site_count
    )
    pga_epsilon_error = float(np.max(np.abs(z1 - baseline_epsilon_pga)))
    sa_epsilon_error = float(np.max(np.abs(expected_i0_sa - baseline_epsilon_sa)))
    if pga_epsilon_error > baseline_tolerance or sa_epsilon_error > baseline_tolerance:
        raise ValueError(
            "Frozen site streams do not reproduce the Phase 1 epsilon columns: "
            f"PGA error={pga_epsilon_error:.6e}, "
            f"SA0P4 error={sa_epsilon_error:.6e}."
        )

    eta_pga_matrix = _reshape_column(
        baseline, "eta_pga", occurrences, site_count
    )
    eta_sa_matrix = _reshape_column(
        baseline, "eta_sa0p4", occurrences, site_count
    )
    eta_pga = eta_pga_matrix[:, 0]
    eta_sa = eta_sa_matrix[:, 0]
    eta_pga_error = float(np.max(np.abs(eta_pga_matrix - eta_pga[:, None])))
    eta_sa_error = float(np.max(np.abs(eta_sa_matrix - eta_sa[:, None])))
    if eta_pga_error != 0.0 or eta_sa_error != 0.0:
        raise ValueError("Between-event residuals are not repeated exactly by occurrence.")

    pga_mean = _reshape_column(
        baseline, "pga_epi_off_mean_ln_g", occurrences, site_count
    )
    pga_tau = _reshape_column(baseline, "pga_tau_ln", occurrences, site_count)
    pga_phi = _reshape_column(baseline, "pga_phi_ln", occurrences, site_count)
    sa_mean = _reshape_column(
        baseline, "sa0p4_epi_off_mean_ln_g", occurrences, site_count
    )
    sa_tau = _reshape_column(baseline, "sa0p4_tau_ln", occurrences, site_count)
    sa_phi = _reshape_column(baseline, "sa0p4_phi_ln", occurrences, site_count)

    regenerated_i0_pga_ln, _ = simulate_log_ground_motion(
        pga_mean, pga_tau, pga_phi, eta_pga, z1
    )
    regenerated_i0_sa_ln, _ = simulate_log_ground_motion(
        sa_mean, sa_tau, sa_phi, eta_sa, expected_i0_sa
    )
    baseline_pga_ln = _reshape_column(
        baseline, "pga_simulated_ln_g", occurrences, site_count
    )
    baseline_sa_ln = _reshape_column(
        baseline, "sa0p4_simulated_ln_g", occurrences, site_count
    )
    pga_ln_error = float(np.max(np.abs(regenerated_i0_pga_ln - baseline_pga_ln)))
    sa_ln_error = float(np.max(np.abs(regenerated_i0_sa_ln - baseline_sa_ln)))
    if pga_ln_error > baseline_tolerance or sa_ln_error > baseline_tolerance:
        raise ValueError(
            "Frozen Phase 1 log ground motions were not reproduced within tolerance."
        )

    output = baseline[COMMON_OUTPUT_COLUMNS].copy()
    case_outputs: list[FloatArray] = []
    for case_name, prefix in CASE_PREFIXES.items():
        if case_name == CASE_I0:
            epsilon_pga = baseline_epsilon_pga
            epsilon_sa = baseline_epsilon_sa
            pga_ln = baseline_pga_ln
            pga_g = _reshape_column(
                baseline, "pga_simulated_g", occurrences, site_count
            )
            sa_ln = baseline_sa_ln
            sa_g = _reshape_column(
                baseline, "sa0p4_simulated_g", occurrences, site_count
            )
        else:
            epsilon_pga, epsilon_sa = transform_latent_batch(
                z1,
                z2,
                factors[case_name],
                cross_imt_rho=rho,
            )
            pga_ln, pga_g = simulate_log_ground_motion(
                pga_mean, pga_tau, pga_phi, eta_pga, epsilon_pga
            )
            sa_ln, sa_g = simulate_log_ground_motion(
                sa_mean, sa_tau, sa_phi, eta_sa, epsilon_sa
            )
        values = [epsilon_pga, epsilon_sa, pga_ln, pga_g, sa_ln, sa_g]
        case_outputs.extend(values)
        for suffix, value in zip(CASE_OUTPUT_SUFFIXES, values):
            output[f"{prefix}_{suffix}"] = value.reshape(-1)

    numeric_output = np.column_stack(
        [value.reshape(-1) for value in case_outputs]
    )
    diagnostics = BatchDiagnostics(
        rows=int(len(baseline)),
        occurrences=int(occurrences),
        site_count=int(site_count),
        maximum_i0_epsilon_pga_error=pga_epsilon_error,
        maximum_i0_epsilon_sa0p4_error=sa_epsilon_error,
        maximum_i0_pga_ln_error=pga_ln_error,
        maximum_i0_sa0p4_ln_error=sa_ln_error,
        maximum_repeated_eta_pga_error=eta_pga_error,
        maximum_repeated_eta_sa0p4_error=eta_sa_error,
        nonfinite_output_count=int(np.count_nonzero(~np.isfinite(numeric_output))),
    )
    return output[PAIRED_OUTPUT_COLUMNS], diagnostics
