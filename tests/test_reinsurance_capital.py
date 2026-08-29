"""Unit tests for Phase 2 reinsurance and capital utilities."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from tools.reinsurance_capital import (
    annual_program_metrics,
    annualize_occurrence_program,
    apply_aggregate_stop_loss,
    apply_occurrence_xol,
    diversification_from_sparse_units,
    empirical_pml,
    empirical_var_tvar,
    minimum_occurrence_limit_for_target,
    paired_bootstrap_differences,
    reconcile_annual_waterfall,
    sparse_var_tvar,
)


class ReinsuranceCapitalTest(unittest.TestCase):
    def test_occurrence_layer_waterfall_and_conservation(self) -> None:
        result = apply_occurrence_xol(
            [50.0, 100.0, 150.0, 350.0],
            attachment=100.0,
            limit=200.0,
        )
        np.testing.assert_allclose(
            result["ceded_loss_2022_usd"], [0.0, 0.0, 50.0, 200.0]
        )
        np.testing.assert_allclose(
            result["retained_loss_2022_usd"], [50.0, 100.0, 100.0, 150.0]
        )
        np.testing.assert_array_equal(
            result["triggered"], [False, False, True, True]
        )
        np.testing.assert_array_equal(
            result["exhausted"], [False, False, False, True]
        )
        np.testing.assert_allclose(
            np.asarray(result["ceded_loss_2022_usd"])
            + np.asarray(result["retained_loss_2022_usd"]),
            [50.0, 100.0, 150.0, 350.0],
        )

    def test_participation_and_aggregate_cover(self) -> None:
        result = apply_aggregate_stop_loss(
            [80.0, 180.0, 500.0],
            attachment=100.0,
            limit=200.0,
            participation=0.5,
        )
        np.testing.assert_allclose(
            result["ceded_loss_2022_usd"], [0.0, 40.0, 100.0]
        )
        np.testing.assert_allclose(
            result["retained_loss_2022_usd"], [80.0, 140.0, 400.0]
        )

    def test_exhaustion_classification_accepts_explicit_numeric_tolerance(self) -> None:
        boundary = 300.0 - 1.0e-8
        exact = apply_occurrence_xol(
            [boundary], attachment=100.0, limit=200.0
        )
        tolerant = apply_occurrence_xol(
            [boundary],
            attachment=100.0,
            limit=200.0,
            classification_tolerance=2.0e-6,
        )
        self.assertFalse(bool(exact["exhausted"][0]))
        self.assertTrue(bool(tolerant["exhausted"][0]))
        np.testing.assert_array_equal(
            exact["ceded_loss_2022_usd"], tolerant["ceded_loss_2022_usd"]
        )
        np.testing.assert_array_equal(
            exact["retained_loss_2022_usd"],
            tolerant["retained_loss_2022_usd"],
        )

    def test_annual_waterfall_reconciles_only_boundary_level_noise(self) -> None:
        epsilon = 1.0e-8
        reconciled = reconcile_annual_waterfall(
            gross_aep=[100.0, 100.0, 100.0],
            ceded_aep=[100.0 + epsilon, -epsilon, 40.0],
            retained_aep=[-epsilon, 100.0 + epsilon, 60.0 + epsilon],
            tolerance=1.0e-6,
        )
        np.testing.assert_array_equal(
            reconciled["ceded_aep_2022_usd"], [100.0, 0.0, 40.0]
        )
        np.testing.assert_array_equal(
            reconciled["retained_aep_2022_usd"], [0.0, 100.0, 60.0]
        )
        np.testing.assert_array_equal(
            reconciled["ceded_aep_2022_usd"]
            + reconciled["retained_aep_2022_usd"],
            [100.0, 100.0, 100.0],
        )

        with self.assertRaises(ValueError):
            reconcile_annual_waterfall(
                gross_aep=[100.0],
                ceded_aep=[100.01],
                retained_aep=[-0.01],
                tolerance=1.0e-6,
            )

    def test_invalid_layer_terms_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            apply_occurrence_xol([1.0], -1.0, 2.0)
        with self.assertRaises(ValueError):
            apply_occurrence_xol([1.0], 0.0, -2.0)
        with self.assertRaises(ValueError):
            apply_occurrence_xol([1.0], 0.0, 2.0, 1.1)
        with self.assertRaises(ValueError):
            apply_occurrence_xol([-1.0], 0.0, 2.0)
        with self.assertRaises(ValueError):
            apply_occurrence_xol(
                [1.0], 0.0, 2.0, classification_tolerance=-1.0
            )

    def test_occurrence_program_annualization_preserves_multiple_events(self) -> None:
        annual = annualize_occurrence_program(
            [1, 1, 3],
            [100.0, 200.0, 50.0],
            [20.0, 80.0, 0.0],
            declared_years=4,
        )
        np.testing.assert_array_equal(
            annual["catalog_occurrence_count"], [2, 0, 1, 0]
        )
        np.testing.assert_allclose(
            annual["gross_aep_2022_usd"], [300.0, 0.0, 50.0, 0.0]
        )
        np.testing.assert_allclose(
            annual["gross_oep_2022_usd"], [200.0, 0.0, 50.0, 0.0]
        )
        np.testing.assert_allclose(
            annual["ceded_aep_2022_usd"], [100.0, 0.0, 0.0, 0.0]
        )
        np.testing.assert_allclose(
            annual["retained_aep_2022_usd"], [200.0, 0.0, 50.0, 0.0]
        )

    def test_empirical_pml_and_fixed_count_tvar(self) -> None:
        losses = np.array([0.0, 0.0, 10.0, 20.0, 30.0])
        pml, rank = empirical_pml(losses, 2)
        self.assertEqual(rank, 3)
        self.assertEqual(pml, 10.0)
        var, tvar, tail_count = empirical_var_tvar(losses, 0.6)
        self.assertEqual(tail_count, 2)
        self.assertEqual(var, 20.0)
        self.assertEqual(tvar, 25.0)

    def test_sparse_tvar_includes_implicit_zero_years(self) -> None:
        var, tvar, tail_count = sparse_var_tvar(
            [10.0, 30.0], declared_years=10, confidence=0.7
        )
        self.assertEqual(tail_count, 4)
        self.assertEqual(var, 0.0)
        self.assertEqual(tvar, 10.0)

    def test_annual_program_metrics_document_noninformative_var(self) -> None:
        gross = np.array([100.0, 0.0, 0.0, 0.0])
        ceded = np.array([40.0, 0.0, 0.0, 0.0])
        retained = gross - ceded
        metrics = annual_program_metrics(
            gross, ceded, retained, confidences=[0.5]
        )
        self.assertAlmostEqual(metrics["gross_aal_2022_usd"], 25.0)
        self.assertAlmostEqual(metrics["retained_aal_2022_usd"], 15.0)
        self.assertEqual(metrics["gross_var_50_2022_usd"], 0.0)
        self.assertFalse(metrics["var_capital_informative_50"])
        self.assertEqual(
            metrics["retained_var_economic_capital_floored_50_2022_usd"],
            0.0,
        )

    def test_diversification_uses_sum_of_standalone_tail_risk(self) -> None:
        frame = pd.DataFrame(
            {
                "unit": ["A", "B", "A", "B"],
                "year": [1, 1, 2, 2],
                "loss": [100.0, 0.0, 0.0, 100.0],
            }
        )
        result = diversification_from_sparse_units(
            frame,
            unit_column="unit",
            year_column="year",
            loss_column="loss",
            portfolio_annual_losses=[100.0, 100.0, 0.0, 0.0],
            declared_years=4,
            confidences=[0.75],
        )
        tvar = result.loc[result["risk_measure"].eq("tvar")].iloc[0]
        self.assertEqual(tvar["portfolio_risk_2022_usd"], 100.0)
        self.assertEqual(tvar["sum_standalone_risk_2022_usd"], 200.0)
        self.assertEqual(tvar["diversification_benefit"], 0.5)

    def test_paired_bootstrap_is_repeatable_and_preserves_zero_difference(self) -> None:
        series = np.array([0.0, 10.0, 0.0, 20.0, 0.0, 30.0])
        arguments = dict(
            annual_series={"case": series, "baseline": series.copy()},
            comparisons=[("case", "baseline")],
            metric_specs=[
                {"name": "aal", "kind": "mean"},
                {"name": "pml_2", "kind": "pml", "return_period": 2},
                {"name": "tvar_50", "kind": "tvar", "confidence": 0.5},
            ],
            replicates=20,
            seed=123,
        )
        first = paired_bootstrap_differences(**arguments)
        second = paired_bootstrap_differences(**arguments)
        pd.testing.assert_frame_equal(first, second)
        np.testing.assert_allclose(first["absolute_change_2022_usd"], 0.0)
        np.testing.assert_allclose(first["bootstrap_ci_lower_2022_usd"], 0.0)
        np.testing.assert_allclose(first["bootstrap_ci_upper_2022_usd"], 0.0)

    def test_minimum_limit_search_recovers_known_solution(self) -> None:
        result = minimum_occurrence_limit_for_target(
            [1, 2],
            [100.0, 200.0],
            declared_years=10,
            attachment=50.0,
            target_kind="aep_pml",
            target_parameter=10,
            target_metric_2022_usd=100.0,
            limit_tolerance_2022_usd=0.01,
        )
        self.assertTrue(result.feasible)
        self.assertGreaterEqual(result.required_limit_2022_usd, 100.0)
        self.assertLess(result.required_limit_2022_usd, 100.01)
        self.assertLessEqual(result.achieved_metric_2022_usd, 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
