"""Tests for the Phase 2 spatial-correlation engine."""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

import numpy as np


def find_project_root() -> Path:
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if (
            candidate
            / "data"
            / "metadata"
            / "notebook_4_cell_18_site_order.csv"
        ).is_file():
            return candidate
    raise FileNotFoundError(
        "Could not find data/metadata/notebook_4_cell_18_site_order.csv."
    )


PROJECT_ROOT = find_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.spatial_correlation import (  # noqa: E402
    CASE_C1,
    CASE_C2,
    CASE_I0,
    DEFAULT_CROSS_IMT_RHO,
    aldea_correlation,
    aldea_sa_beta_km,
    build_correlation_case,
    geometry_summary,
    goda_atkinson_correlation,
    haversine_distance_matrix,
    transform_site_latents,
)


def load_site_coordinates() -> tuple[np.ndarray, np.ndarray]:
    path = (
        PROJECT_ROOT
        / "data"
        / "metadata"
        / "notebook_4_cell_18_site_order.csv"
    )
    longitude: list[float] = []
    latitude: list[float] = []
    ordinals: list[int] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            ordinals.append(int(row["site_ordinal"]))
            longitude.append(float(row["site_longitude"]))
            latitude.append(float(row["site_latitude"]))
    np.testing.assert_array_equal(ordinals, np.arange(470))
    return np.asarray(longitude), np.asarray(latitude)


class SpatialCorrelationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.longitude, cls.latitude = load_site_coordinates()
        cls.distance = haversine_distance_matrix(cls.longitude, cls.latitude)
        cls.cases = {
            name: build_correlation_case(cls.distance, case_name=name)
            for name in (CASE_I0, CASE_C1, CASE_C2)
        }

    def test_haversine_matrix_contract(self) -> None:
        self.assertEqual(self.distance.shape, (470, 470))
        np.testing.assert_allclose(self.distance, self.distance.T, atol=0.0, rtol=0.0)
        np.testing.assert_allclose(np.diag(self.distance), 0.0, atol=0.0, rtol=0.0)
        self.assertAlmostEqual(float(np.max(self.distance)), 6.4243940484, places=8)

    def test_frozen_geometry_summary(self) -> None:
        summary = geometry_summary(self.longitude, self.latitude, self.distance)
        self.assertEqual(summary["site_count"], 470)
        self.assertEqual(summary["unique_coordinate_count"], 426)
        self.assertEqual(summary["duplicate_coordinate_group_count"], 25)
        self.assertEqual(summary["sites_in_duplicate_coordinate_groups"], 69)
        self.assertEqual(summary["largest_duplicate_coordinate_group"], 17)
        self.assertEqual(summary["pair_count"], 110_215)
        self.assertAlmostEqual(summary["median_pair_distance_km"], 1.24155, places=4)

    def test_published_kernel_parameters(self) -> None:
        self.assertAlmostEqual(aldea_sa_beta_km(0.4), 7.6, places=14)
        self.assertAlmostEqual(
            float(aldea_correlation(np.array([0.0]), imt="PGA")[0]),
            1.0,
            places=14,
        )
        self.assertAlmostEqual(
            float(aldea_correlation(np.array([0.0]), imt="SA0P4")[0]),
            1.0,
            places=14,
        )
        self.assertAlmostEqual(
            float(goda_atkinson_correlation(np.array([0.0]))[0]),
            1.0,
            places=14,
        )

    def test_all_case_matrices_are_valid(self) -> None:
        for case in self.cases.values():
            for matrix in (
                case.pga_correlation,
                case.sa0p4_correlation,
                case.conditional_correlation,
            ):
                np.testing.assert_allclose(matrix, matrix.T, atol=1.0e-13, rtol=0.0)
                np.testing.assert_allclose(
                    np.diag(matrix), 1.0, atol=1.0e-13, rtol=0.0
                )
            for diagnostic in case.diagnostics:
                self.assertEqual(diagnostic.material_negative_eigenvalue_count, 0)
                self.assertLessEqual(diagnostic.reconstruction_error_max_abs, 1.0e-12)
                self.assertLessEqual(
                    diagnostic.reconstructed_diagonal_error_max_abs, 1.0e-12
                )

    def test_expected_matrix_ranks(self) -> None:
        independent_ranks = [item.numerical_rank for item in self.cases[CASE_I0].diagnostics]
        self.assertEqual(independent_ranks, [470, 470, 470])
        independent_duplicate_groups = [
            item.duplicate_row_group_count
            for item in self.cases[CASE_I0].diagnostics
        ]
        self.assertEqual(independent_duplicate_groups, [0, 0, 0])
        for name in (CASE_C1, CASE_C2):
            ranks = [item.numerical_rank for item in self.cases[name].diagnostics]
            self.assertEqual(ranks, [426, 426, 426])
            duplicate_groups = [
                item.duplicate_row_group_count
                for item in self.cases[name].diagnostics
            ]
            rows_in_duplicate_groups = [
                item.rows_in_duplicate_groups
                for item in self.cases[name].diagnostics
            ]
            self.assertEqual(duplicate_groups, [25, 25, 25])
            self.assertEqual(rows_in_duplicate_groups, [69, 69, 69])

    def test_aldea_conditional_construction_recovers_sa_covariance(self) -> None:
        case = self.cases[CASE_C1]
        rho = case.cross_imt_rho
        reconstructed = (
            rho**2 * case.pga_correlation
            + (1.0 - rho**2) * case.conditional_correlation
        )
        np.testing.assert_allclose(
            reconstructed,
            case.sa0p4_correlation,
            atol=2.0e-15,
            rtol=0.0,
        )

    def test_goda_uses_one_common_spatial_kernel(self) -> None:
        case = self.cases[CASE_C2]
        np.testing.assert_allclose(
            case.pga_correlation,
            case.sa0p4_correlation,
            atol=0.0,
            rtol=0.0,
        )
        np.testing.assert_allclose(
            case.pga_correlation,
            case.conditional_correlation,
            atol=2.0e-15,
            rtol=0.0,
        )

    def test_independent_case_reproduces_phase1_latent_transform_exactly(self) -> None:
        rng = np.random.Generator(np.random.PCG64DXSM(20260731))
        z1 = rng.standard_normal(470)
        z2 = rng.standard_normal(470)
        pga, sa = transform_site_latents(self.cases[CASE_I0], z1, z2)
        expected_sa = (
            DEFAULT_CROSS_IMT_RHO * z1
            + np.sqrt(1.0 - DEFAULT_CROSS_IMT_RHO**2) * z2
        )
        np.testing.assert_array_equal(pga, z1)
        np.testing.assert_array_equal(sa, expected_sa)

    def test_colocated_sites_have_identical_correlated_residuals(self) -> None:
        coordinates = np.column_stack([self.longitude, self.latitude])
        _, inverse, counts = np.unique(
            coordinates, axis=0, return_inverse=True, return_counts=True
        )
        rng = np.random.Generator(np.random.PCG64DXSM(20260828))
        z1 = rng.standard_normal(470)
        z2 = rng.standard_normal(470)
        for name in (CASE_C1, CASE_C2):
            pga, sa = transform_site_latents(self.cases[name], z1, z2)
            for group in np.flatnonzero(counts > 1):
                members = np.flatnonzero(inverse == group)
                np.testing.assert_array_equal(pga[members], pga[members[0]])
                np.testing.assert_array_equal(sa[members], sa[members[0]])

    def test_input_validation(self) -> None:
        with self.assertRaises(ValueError):
            aldea_correlation(np.array([-1.0]), imt="PGA")
        with self.assertRaises(ValueError):
            build_correlation_case(self.distance, case_name="UNKNOWN")
        with self.assertRaises(ValueError):
            transform_site_latents(
                self.cases[CASE_C1], np.zeros(469), np.zeros(469)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
