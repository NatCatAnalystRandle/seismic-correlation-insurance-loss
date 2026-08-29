"""Tests for paired Phase 2 ground-motion generation."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from tools.correlated_ground_motion import (
    BASE_RANDOM_SEED,
    CASE_OUTPUT_SUFFIXES,
    CASE_PREFIXES,
    PAIRED_OUTPUT_COLUMNS,
    BatchDiagnostics,
    CaseFactors,
    build_paired_field_batch,
    load_case_factors,
    regenerate_site_latent_batch,
    seed_from_hex,
    simulate_log_ground_motion,
    site_seed_for_occurrence,
    stable_seed,
    transform_latent_batch,
    validate_occurrence_site_order,
)
from tools.spatial_correlation import CASE_C1, CASE_C2, CASE_I0


RHO = 0.7321409900247263


def small_factors() -> dict[str, CaseFactors]:
    identity = np.eye(3)
    correlated = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.4, np.sqrt(1.0 - 0.4**2), 0.0],
            [0.2, 0.1, np.sqrt(1.0 - 0.2**2 - 0.1**2)],
        ]
    )
    return {
        CASE_I0: CaseFactors(identity, identity),
        CASE_C1: CaseFactors(correlated, correlated),
        CASE_C2: CaseFactors(correlated.T, correlated.T),
    }


def synthetic_baseline() -> pd.DataFrame:
    site_ids = ["S0", "S1", "S2"]
    occurrence_ids = ["occurrence_A", "occurrence_B"]
    rupture_ids = ["rupture_A", "rupture_B"]
    eta_pga = np.array([0.25, -0.70])
    eta_sa = np.array([-0.10, 0.55])
    seed_hexes = [
        site_seed_for_occurrence(occurrence_id, rupture_id)[1]
        for occurrence_id, rupture_id in zip(occurrence_ids, rupture_ids)
    ]
    z1, z2 = regenerate_site_latent_batch(seed_hexes, site_count=3)
    epsilon_sa = RHO * z1 + np.sqrt(1.0 - RHO**2) * z2
    mean_pga = np.array([[-1.5, -1.4, -1.3], [-1.2, -1.1, -1.0]])
    mean_sa = mean_pga + 0.4
    tau_pga = np.full((2, 3), 0.30)
    phi_pga = np.full((2, 3), 0.55)
    tau_sa = np.full((2, 3), 0.35)
    phi_sa = np.full((2, 3), 0.60)
    pga_ln, pga_g = simulate_log_ground_motion(
        mean_pga, tau_pga, phi_pga, eta_pga, z1
    )
    sa_ln, sa_g = simulate_log_ground_motion(
        mean_sa, tau_sa, phi_sa, eta_sa, epsilon_sa
    )

    rows: list[dict[str, object]] = []
    for event_index, (occurrence_id, rupture_id) in enumerate(
        zip(occurrence_ids, rupture_ids)
    ):
        for site_index, site_id in enumerate(site_ids):
            rows.append(
                {
                    "catalog_year": 100 + event_index,
                    "catalog_event_id": f"E{event_index}",
                    "occurrence_ordinal": event_index,
                    "occurrence_id": occurrence_id,
                    "rupture_ordinal": event_index,
                    "rupture_template_event_id": f"T{event_index}",
                    "rupture_id": rupture_id,
                    "source_type": "INTERFACE",
                    "gmm_name": "TEST_GMM",
                    "magnitude": 8.5,
                    "site_ordinal": site_index,
                    "site_id": site_id,
                    "site_longitude": -124.0 + site_index * 0.01,
                    "site_latitude": 46.0 + site_index * 0.01,
                    "r_rup_km": 20.0 + site_index,
                    "vs30_mps": 365.0,
                    "period_s": 0.4,
                    "cross_imt_rho": RHO,
                    "eta_pga": eta_pga[event_index],
                    "epsilon_pga": z1[event_index, site_index],
                    "pga_epi_off_mean_ln_g": mean_pga[event_index, site_index],
                    "pga_tau_ln": tau_pga[event_index, site_index],
                    "pga_phi_ln": phi_pga[event_index, site_index],
                    "pga_simulated_ln_g": pga_ln[event_index, site_index],
                    "pga_simulated_g": pga_g[event_index, site_index],
                    "eta_sa0p4": eta_sa[event_index],
                    "epsilon_sa0p4": epsilon_sa[event_index, site_index],
                    "sa0p4_epi_off_mean_ln_g": mean_sa[event_index, site_index],
                    "sa0p4_tau_ln": tau_sa[event_index, site_index],
                    "sa0p4_phi_ln": phi_sa[event_index, site_index],
                    "sa0p4_simulated_ln_g": sa_ln[event_index, site_index],
                    "sa0p4_simulated_g": sa_g[event_index, site_index],
                }
            )
    return pd.DataFrame(rows)


class CorrelatedGroundMotionTest(unittest.TestCase):
    def test_frozen_seed_derivation(self) -> None:
        seed, seed_hex = stable_seed(
            BASE_RANDOM_SEED,
            "cell19",
            "occurrence_A",
            "rupture_A",
            "site",
        )
        self.assertEqual(seed_hex, "f271ad2dd84935b20632d928ec13b50f")
        self.assertEqual(seed, 20878629744439338179998889123706139122)
        self.assertEqual(seed_from_hex(seed_hex), seed)

    def test_seed_validation(self) -> None:
        for invalid in ("", "xyz", "0" * 31, "g" * 32):
            with self.assertRaises(ValueError):
                seed_from_hex(invalid)

    def test_regenerated_stream_is_repeatable(self) -> None:
        seed_hex = site_seed_for_occurrence("occurrence_A", "rupture_A")[1]
        first = regenerate_site_latent_batch([seed_hex], site_count=3)
        second = regenerate_site_latent_batch([seed_hex], site_count=3)
        np.testing.assert_array_equal(first[0], second[0])
        np.testing.assert_array_equal(first[1], second[1])

    def test_identity_transform_reproduces_phase1_exactly(self) -> None:
        z1 = np.arange(6, dtype=float).reshape(2, 3)
        z2 = z1 + 10.0
        identity = np.eye(3)
        pga, sa = transform_latent_batch(
            z1,
            z2,
            CaseFactors(identity, identity),
            cross_imt_rho=RHO,
        )
        np.testing.assert_array_equal(pga, z1)
        np.testing.assert_array_equal(
            sa, RHO * z1 + np.sqrt(1.0 - RHO**2) * z2
        )

    def test_log_ground_motion_equation(self) -> None:
        mean = np.array([[1.0, 2.0]])
        tau = np.array([[0.2, 0.3]])
        phi = np.array([[0.4, 0.5]])
        eta = np.array([0.6])
        epsilon = np.array([[-0.5, 0.7]])
        actual_ln, actual = simulate_log_ground_motion(
            mean, tau, phi, eta, epsilon
        )
        expected_ln = mean + tau * eta[:, None] + phi * epsilon
        np.testing.assert_array_equal(actual_ln, expected_ln)
        np.testing.assert_array_equal(actual, np.exp(expected_ln))

    def test_paired_batch_preserves_i0_and_common_fields(self) -> None:
        baseline = synthetic_baseline()
        paired, diagnostics = build_paired_field_batch(
            baseline,
            small_factors(),
            expected_site_ids=["S0", "S1", "S2"],
            site_count=3,
        )
        self.assertEqual(paired.columns.tolist(), PAIRED_OUTPUT_COLUMNS)
        np.testing.assert_array_equal(
            paired["i0_epsilon_pga"], baseline["epsilon_pga"]
        )
        np.testing.assert_array_equal(
            paired["i0_pga_simulated_ln_g"], baseline["pga_simulated_ln_g"]
        )
        np.testing.assert_array_equal(paired["eta_pga"], baseline["eta_pga"])
        self.assertIsInstance(diagnostics, BatchDiagnostics)
        self.assertEqual(diagnostics.occurrences, 2)
        self.assertEqual(diagnostics.nonfinite_output_count, 0)

    def test_correlated_cases_change_only_within_event_result(self) -> None:
        baseline = synthetic_baseline()
        paired, _ = build_paired_field_batch(
            baseline,
            small_factors(),
            expected_site_ids=["S0", "S1", "S2"],
            site_count=3,
        )
        self.assertTrue(
            np.any(
                paired["c1_pga_simulated_ln_g"].to_numpy()
                != paired["i0_pga_simulated_ln_g"].to_numpy()
            )
        )
        self.assertTrue(
            np.array_equal(
                paired["catalog_year"].to_numpy(),
                baseline["catalog_year"].to_numpy(),
            )
        )

    def test_site_order_validation(self) -> None:
        baseline = synthetic_baseline()
        occurrences, occurrence_ids, rupture_ids = validate_occurrence_site_order(
            baseline,
            site_count=3,
            expected_site_ids=["S0", "S1", "S2"],
        )
        self.assertEqual(occurrences, 2)
        self.assertEqual(occurrence_ids, ["occurrence_A", "occurrence_B"])
        self.assertEqual(rupture_ids, ["rupture_A", "rupture_B"])
        invalid = baseline.copy()
        invalid.loc[1, "site_ordinal"] = 2
        with self.assertRaises(ValueError):
            validate_occurrence_site_order(invalid, site_count=3)
        with self.assertRaises(ValueError):
            validate_occurrence_site_order(
                baseline,
                site_count=3,
                expected_site_ids=["S0", "S1"],
            )

    def test_invalid_cross_imt_correlation_is_rejected(self) -> None:
        baseline = synthetic_baseline()
        baseline["cross_imt_rho"] = 1.01
        with self.assertRaises(ValueError):
            build_paired_field_batch(
                baseline,
                small_factors(),
                expected_site_ids=["S0", "S1", "S2"],
                site_count=3,
            )

    def test_factor_artifact_loader(self) -> None:
        factors = small_factors()
        payload: dict[str, np.ndarray] = {}
        for case_name, prefix in CASE_PREFIXES.items():
            payload[f"{prefix}_pga_square_root"] = factors[
                case_name
            ].pga_square_root
            payload[f"{prefix}_conditional_square_root"] = factors[
                case_name
            ].conditional_square_root
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "factors.npz"
            np.savez_compressed(path, **payload)
            loaded = load_case_factors(path, expected_site_count=3)
        self.assertEqual(set(loaded), set(CASE_PREFIXES))
        np.testing.assert_array_equal(
            loaded[CASE_C1].pga_square_root,
            factors[CASE_C1].pga_square_root,
        )

    def test_nonfinite_factor_artifact_is_rejected(self) -> None:
        factors = small_factors()
        payload: dict[str, np.ndarray] = {}
        for case_name, prefix in CASE_PREFIXES.items():
            payload[f"{prefix}_pga_square_root"] = factors[
                case_name
            ].pga_square_root.copy()
            payload[f"{prefix}_conditional_square_root"] = factors[
                case_name
            ].conditional_square_root.copy()
        payload["c1_pga_square_root"][0, 0] = np.nan
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "factors.npz"
            np.savez_compressed(path, **payload)
            with self.assertRaises(ValueError):
                load_case_factors(path, expected_site_count=3)

    def test_output_schema_has_six_fields_per_case(self) -> None:
        self.assertEqual(len(CASE_OUTPUT_SUFFIXES), 6)
        for prefix in CASE_PREFIXES.values():
            for suffix in CASE_OUTPUT_SUFFIXES:
                self.assertIn(f"{prefix}_{suffix}", PAIRED_OUTPUT_COLUMNS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
