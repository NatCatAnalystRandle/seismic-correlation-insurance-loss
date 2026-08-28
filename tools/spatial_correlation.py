"""Within-event spatial-correlation utilities for Phase 2.

The module implements the three dependence cases frozen in
``docs/PHASE_2_EXPERIMENTAL_DESIGN.md``:

``I0_PHASE1_INDEPENDENT``
    Phase 1 control with independent within-event residuals across sites.
``C1_ALDEA22_SUBDUCTION``
    Aldea, Heresi, and Pasten (2022) period-specific subduction kernels.
``C2_GODA_ATKINSON09``
    Goda and Atkinson (2009) subduction-environment benchmark kernel.

The functions operate on normalized residuals. They do not change event
occurrences, median ground motions, between-event residuals, GMM dispersions,
damage draws, exposure, or financial terms.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]

EARTH_RADIUS_KM: Final[float] = 6371.0088
DEFAULT_CROSS_IMT_RHO: Final[float] = 0.7321409900247263
DEFAULT_NEGATIVE_EIGENVALUE_TOLERANCE: Final[float] = 1.0e-10
DEFAULT_RANK_TOLERANCE: Final[float] = 1.0e-10

CASE_I0: Final[str] = "I0_PHASE1_INDEPENDENT"
CASE_C1: Final[str] = "C1_ALDEA22_SUBDUCTION"
CASE_C2: Final[str] = "C2_GODA_ATKINSON09"
SUPPORTED_CASES: Final[tuple[str, ...]] = (CASE_I0, CASE_C1, CASE_C2)

ALDEA_ALPHA: Final[float] = 0.59
ALDEA_PGA_BETA_KM: Final[float] = 14.40
ALDEA_SA0P4_BETA_KM: Final[float] = 7.60

GODA_ALPHA: Final[float] = 0.207
GODA_BETA: Final[float] = 0.386
GODA_GAMMA: Final[float] = 1.389


@dataclass(frozen=True)
class MatrixDiagnostics:
    """Numerical diagnostics for a correlation matrix and its square root."""

    matrix_name: str
    size: int
    minimum_eigenvalue: float
    maximum_eigenvalue: float
    numerical_rank: int
    zero_mode_count: int
    clipped_numerical_zero_eigenvalue_count: int
    clipped_negative_eigenvalue_count: int
    material_negative_eigenvalue_count: int
    rank_threshold: float
    symmetry_error_max_abs: float
    input_diagonal_error_max_abs: float
    correction_frobenius_norm: float
    reconstruction_error_max_abs: float
    reconstructed_diagonal_error_max_abs: float

    def to_dict(self) -> dict[str, int | float | str]:
        """Return JSON-serializable diagnostics."""

        return asdict(self)


@dataclass(frozen=True)
class CorrelationCase:
    """Matrices and deterministic square roots for one dependence case."""

    case_name: str
    cross_imt_rho: float
    pga_correlation: FloatArray
    sa0p4_correlation: FloatArray
    conditional_correlation: FloatArray
    pga_square_root: FloatArray
    conditional_square_root: FloatArray
    diagnostics: tuple[MatrixDiagnostics, ...]

    @property
    def site_count(self) -> int:
        return int(self.pga_correlation.shape[0])

    @property
    def is_independent(self) -> bool:
        return self.case_name == CASE_I0

    def metadata(self) -> dict[str, object]:
        """Return the case definition without serializing dense matrices."""

        return {
            "case_name": self.case_name,
            "cross_imt_rho": self.cross_imt_rho,
            "site_count": self.site_count,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


def _as_nonnegative_distance_array(distance_km: ArrayLike) -> FloatArray:
    values = np.asarray(distance_km, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("Distances must be finite.")
    if np.any(values < 0.0):
        raise ValueError("Distances must be nonnegative.")
    return values


def haversine_distance_matrix(
    longitude_deg: ArrayLike,
    latitude_deg: ArrayLike,
) -> FloatArray:
    """Return the symmetric great-circle site-distance matrix in km."""

    longitude = np.asarray(longitude_deg, dtype=np.float64)
    latitude = np.asarray(latitude_deg, dtype=np.float64)
    if longitude.ndim != 1 or latitude.ndim != 1:
        raise ValueError("Longitude and latitude must be one-dimensional.")
    if longitude.shape != latitude.shape:
        raise ValueError("Longitude and latitude must have the same length.")
    if longitude.size == 0:
        raise ValueError("At least one site is required.")
    if not np.all(np.isfinite(longitude)) or not np.all(np.isfinite(latitude)):
        raise ValueError("Longitude and latitude must be finite.")
    if np.any((longitude < -180.0) | (longitude > 180.0)):
        raise ValueError("Longitude must lie in [-180, 180] degrees.")
    if np.any((latitude < -90.0) | (latitude > 90.0)):
        raise ValueError("Latitude must lie in [-90, 90] degrees.")

    lon_rad = np.radians(longitude)
    lat_rad = np.radians(latitude)
    delta_lon = lon_rad[:, None] - lon_rad[None, :]
    delta_lat = lat_rad[:, None] - lat_rad[None, :]
    haversine = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(lat_rad[:, None])
        * np.cos(lat_rad[None, :])
        * np.sin(delta_lon / 2.0) ** 2
    )
    distance = 2.0 * EARTH_RADIUS_KM * np.arcsin(
        np.minimum(1.0, np.sqrt(np.maximum(haversine, 0.0)))
    )
    distance = 0.5 * (distance + distance.T)
    np.fill_diagonal(distance, 0.0)
    return distance


def aldea_sa_beta_km(period_s: float) -> float:
    """Return the smoothed Aldea et al. beta parameter for SA(T)."""

    period = float(period_s)
    if not np.isfinite(period) or period <= 0.0 or period > 10.0:
        raise ValueError("Aldea SA period must be in (0, 10] seconds.")
    if period <= 0.40:
        return 14.400 - 17.000 * period
    if period <= 0.75:
        return 14.743 + 7.795 * float(np.log(period))
    if period <= 3.00:
        return 12.500
    return 5.063 + 6.769 * float(np.log(period))


def aldea_correlation(
    distance_km: ArrayLike,
    *,
    imt: str,
    period_s: float | None = None,
) -> FloatArray:
    """Evaluate the Aldea et al. (2022) within-event correlation."""

    distance = _as_nonnegative_distance_array(distance_km)
    normalized_imt = imt.strip().upper().replace(" ", "")
    if normalized_imt == "PGA":
        if period_s is not None:
            raise ValueError("period_s must be omitted for PGA.")
        beta_km = ALDEA_PGA_BETA_KM
    elif normalized_imt in {"SA", "SA0P4", "SA(0.4)", "SA0.4"}:
        if normalized_imt in {"SA0P4", "SA(0.4)", "SA0.4"}:
            resolved_period = 0.4 if period_s is None else float(period_s)
            if not np.isclose(resolved_period, 0.4, atol=0.0, rtol=0.0):
                raise ValueError("SA0P4 aliases require period_s=0.4.")
        else:
            if period_s is None:
                raise ValueError("period_s is required when imt='SA'.")
            resolved_period = float(period_s)
        beta_km = aldea_sa_beta_km(resolved_period)
    else:
        raise ValueError(f"Unsupported Aldea intensity measure: {imt!r}")
    return np.exp(-np.power(distance / beta_km, ALDEA_ALPHA))


def goda_atkinson_correlation(distance_km: ArrayLike) -> FloatArray:
    """Evaluate the Goda and Atkinson (2009) pooled spatial kernel."""

    distance = _as_nonnegative_distance_array(distance_km)
    correlation = (
        GODA_GAMMA * np.exp(-GODA_ALPHA * np.power(distance, GODA_BETA))
        - GODA_GAMMA
        + 1.0
    )
    return np.maximum(correlation, 0.0)


def spectral_square_root(
    matrix: ArrayLike,
    *,
    matrix_name: str,
    negative_tolerance: float = DEFAULT_NEGATIVE_EIGENVALUE_TOLERANCE,
    rank_tolerance: float = DEFAULT_RANK_TOLERANCE,
) -> tuple[FloatArray, MatrixDiagnostics]:
    """Return the unique symmetric PSD square root and diagnostics.

    Eigenvalues in ``[-negative_tolerance, rank_threshold]`` are treated as
    numerical zero modes and clipped to zero. A materially negative eigenvalue
    raises an error. The symmetric square root is invariant to eigenvector sign
    choices.
    """

    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("The correlation matrix must be square.")
    if values.shape[0] == 0:
        raise ValueError("The correlation matrix cannot be empty.")
    if not np.all(np.isfinite(values)):
        raise ValueError("The correlation matrix must be finite.")
    if negative_tolerance <= 0.0 or rank_tolerance <= 0.0:
        raise ValueError("Eigenvalue tolerances must be positive.")

    symmetry_error = float(np.max(np.abs(values - values.T)))
    symmetric = 0.5 * (values + values.T)
    input_diagonal_error = float(
        np.max(np.abs(np.diag(symmetric) - 1.0))
    )
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    material_negative = eigenvalues < -negative_tolerance
    if np.any(material_negative):
        minimum = float(eigenvalues[0])
        count = int(np.count_nonzero(material_negative))
        raise ValueError(
            f"{matrix_name} is not positive semidefinite: minimum "
            f"eigenvalue={minimum:.6e}, material negative count={count}."
        )

    maximum_input_eigenvalue = float(max(eigenvalues[-1], 0.0))
    rank_threshold = max(
        float(rank_tolerance),
        float(
            values.shape[0]
            * np.finfo(np.float64).eps
            * maximum_input_eigenvalue
        ),
    )
    clipped = np.where(eigenvalues > rank_threshold, eigenvalues, 0.0)
    square_root = (
        eigenvectors * np.sqrt(clipped)[None, :]
    ) @ eigenvectors.T
    corrected = (eigenvectors * clipped[None, :]) @ eigenvectors.T
    reconstructed = square_root @ square_root.T
    maximum_eigenvalue = float(clipped[-1])
    numerical_rank = int(np.count_nonzero(clipped > rank_threshold))

    diagnostics = MatrixDiagnostics(
        matrix_name=matrix_name,
        size=int(values.shape[0]),
        minimum_eigenvalue=float(eigenvalues[0]),
        maximum_eigenvalue=float(eigenvalues[-1]),
        numerical_rank=numerical_rank,
        zero_mode_count=int(values.shape[0] - numerical_rank),
        clipped_numerical_zero_eigenvalue_count=int(
            np.count_nonzero(eigenvalues <= rank_threshold)
        ),
        clipped_negative_eigenvalue_count=int(np.count_nonzero(eigenvalues < 0.0)),
        material_negative_eigenvalue_count=int(np.count_nonzero(material_negative)),
        rank_threshold=float(rank_threshold),
        symmetry_error_max_abs=symmetry_error,
        input_diagonal_error_max_abs=input_diagonal_error,
        correction_frobenius_norm=float(np.linalg.norm(corrected - symmetric, ord="fro")),
        reconstruction_error_max_abs=float(np.max(np.abs(reconstructed - corrected))),
        reconstructed_diagonal_error_max_abs=float(
            np.max(np.abs(np.diag(reconstructed) - 1.0))
        ),
    )
    return square_root, diagnostics


def _validate_distance_matrix(distance_km: ArrayLike) -> FloatArray:
    distance = _as_nonnegative_distance_array(distance_km)
    if distance.ndim != 2 or distance.shape[0] != distance.shape[1]:
        raise ValueError("The site-distance matrix must be square.")
    if not np.allclose(distance, distance.T, atol=1.0e-12, rtol=0.0):
        raise ValueError("The site-distance matrix must be symmetric.")
    if not np.allclose(np.diag(distance), 0.0, atol=1.0e-12, rtol=0.0):
        raise ValueError("The site-distance matrix diagonal must be zero.")
    return distance


def build_correlation_case(
    distance_km: ArrayLike,
    *,
    case_name: str,
    cross_imt_rho: float = DEFAULT_CROSS_IMT_RHO,
    negative_tolerance: float = DEFAULT_NEGATIVE_EIGENVALUE_TOLERANCE,
) -> CorrelationCase:
    """Build all matrices needed for one joint PGA and SA(0.4 s) case."""

    distance = _validate_distance_matrix(distance_km)
    normalized_case = case_name.strip().upper()
    if normalized_case not in SUPPORTED_CASES:
        raise ValueError(
            f"Unsupported case {case_name!r}. Expected one of {SUPPORTED_CASES}."
        )
    rho = float(cross_imt_rho)
    if not np.isfinite(rho) or not (-1.0 < rho < 1.0):
        raise ValueError("cross_imt_rho must be finite and strictly between -1 and 1.")

    site_count = distance.shape[0]
    if normalized_case == CASE_I0:
        pga_correlation = np.eye(site_count, dtype=np.float64)
        sa0p4_correlation = pga_correlation.copy()
    elif normalized_case == CASE_C1:
        pga_correlation = aldea_correlation(distance, imt="PGA")
        sa0p4_correlation = aldea_correlation(distance, imt="SA0P4")
    else:
        common = goda_atkinson_correlation(distance)
        pga_correlation = common.copy()
        sa0p4_correlation = common.copy()

    conditional = (
        sa0p4_correlation - rho**2 * pga_correlation
    ) / (1.0 - rho**2)
    matrices = {
        "pga_correlation": pga_correlation,
        "sa0p4_correlation": sa0p4_correlation,
        "conditional_correlation": conditional,
    }
    roots: dict[str, FloatArray] = {}
    diagnostics: list[MatrixDiagnostics] = []
    for matrix_name, matrix in matrices.items():
        root, matrix_diagnostics = spectral_square_root(
            matrix,
            matrix_name=f"{normalized_case}.{matrix_name}",
            negative_tolerance=negative_tolerance,
        )
        roots[matrix_name] = root
        diagnostics.append(matrix_diagnostics)

    if normalized_case == CASE_I0:
        roots["pga_correlation"] = np.eye(site_count, dtype=np.float64)
        roots["conditional_correlation"] = np.eye(site_count, dtype=np.float64)

    return CorrelationCase(
        case_name=normalized_case,
        cross_imt_rho=rho,
        pga_correlation=pga_correlation,
        sa0p4_correlation=sa0p4_correlation,
        conditional_correlation=conditional,
        pga_square_root=roots["pga_correlation"],
        conditional_square_root=roots["conditional_correlation"],
        diagnostics=tuple(diagnostics),
    )


def transform_site_latents(
    case: CorrelationCase,
    z_site_latent_1: ArrayLike,
    z_site_latent_2: ArrayLike,
) -> tuple[FloatArray, FloatArray]:
    """Transform the frozen latent vectors into joint PGA and SA residuals.

    Inputs may be vectors with shape ``(site_count,)`` or matrices with shape
    ``(site_count, realization_count)``. The first dimension must follow the
    frozen Phase 1 site order.
    """

    z1 = np.asarray(z_site_latent_1, dtype=np.float64)
    z2 = np.asarray(z_site_latent_2, dtype=np.float64)
    if z1.shape != z2.shape:
        raise ValueError("The two latent arrays must have identical shapes.")
    if z1.ndim not in (1, 2):
        raise ValueError("Latent arrays must be one- or two-dimensional.")
    if z1.shape[0] != case.site_count:
        raise ValueError(
            f"Expected first dimension {case.site_count}, received {z1.shape[0]}."
        )
    if not np.all(np.isfinite(z1)) or not np.all(np.isfinite(z2)):
        raise ValueError("Latent arrays must be finite.")

    if case.is_independent:
        epsilon_pga = z1.copy()
        conditional_component = z2.copy()
    else:
        epsilon_pga = case.pga_square_root @ z1
        conditional_component = case.conditional_square_root @ z2
    rho = case.cross_imt_rho
    epsilon_sa0p4 = (
        rho * epsilon_pga
        + np.sqrt(1.0 - rho**2) * conditional_component
    )
    return epsilon_pga, epsilon_sa0p4


def geometry_summary(
    longitude_deg: ArrayLike,
    latitude_deg: ArrayLike,
    distance_km: ArrayLike | None = None,
) -> dict[str, object]:
    """Return deterministic portfolio-geometry diagnostics."""

    longitude = np.asarray(longitude_deg, dtype=np.float64)
    latitude = np.asarray(latitude_deg, dtype=np.float64)
    distance = (
        haversine_distance_matrix(longitude, latitude)
        if distance_km is None
        else _validate_distance_matrix(distance_km)
    )
    if longitude.shape != latitude.shape or longitude.shape != (distance.shape[0],):
        raise ValueError("Coordinate arrays do not match the distance matrix.")

    coordinates = np.column_stack([longitude, latitude])
    _, counts = np.unique(coordinates, axis=0, return_counts=True)
    duplicate_counts = counts[counts > 1]
    upper = distance[np.triu_indices(distance.shape[0], k=1)]
    quantile_probabilities = np.array(
        [0.00, 0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99, 1.00]
    )
    quantiles = np.quantile(upper, quantile_probabilities)
    return {
        "site_count": int(distance.shape[0]),
        "unique_coordinate_count": int(counts.size),
        "duplicate_coordinate_group_count": int(duplicate_counts.size),
        "sites_in_duplicate_coordinate_groups": int(np.sum(duplicate_counts)),
        "largest_duplicate_coordinate_group": int(
            np.max(duplicate_counts) if duplicate_counts.size else 1
        ),
        "pair_count": int(upper.size),
        "minimum_pair_distance_km": float(np.min(upper)),
        "median_pair_distance_km": float(np.median(upper)),
        "maximum_pair_distance_km": float(np.max(upper)),
        "pair_distance_quantiles_km": {
            f"p{int(probability * 100):02d}": float(value)
            for probability, value in zip(quantile_probabilities, quantiles, strict=True)
        },
    }


def mean_off_diagonal_correlation(matrix: ArrayLike) -> float:
    """Return the mean correlation over unique off-diagonal site pairs."""

    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("The correlation matrix must be square.")
    upper = values[np.triu_indices(values.shape[0], k=1)]
    return float(np.mean(upper))


def equal_weight_effective_site_count(matrix: ArrayLike) -> float:
    """Return the equal-weight linear effective-site-count diagnostic."""

    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("The correlation matrix must be square.")
    site_count = values.shape[0]
    return float(site_count**2 / np.sum(values))
