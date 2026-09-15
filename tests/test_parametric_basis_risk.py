"""Numerical and out-of-sample controls for the parametric bond model."""

import unittest

import numpy as np
import pandas as pd

from tools.parametric_basis_risk import (
    annual_basis_series, apply_annual_collateral, basis_metrics,
    calibrate_trigger, portfolio_distances, predict_payout, tail_rows,
    tier_payout, year_indices,
)


def feature_fixture():
    return pd.DataFrame({
        "occurrence_id": ["a", "b", "c", "d", "e", "f"],
        "catalog_year": [1, 2, 2, 5, 5, 8],
        "time_within_year": [.1, .2, .3, .1, .9, .5],
        "source_type": ["INTERFACE", "SLAB", "INTERFACE"] * 2,
        "magnitude": [6., 7., 8., 7., 9., 8.],
        "portfolio_distance_km": [0., 50., 20., 10., 0., 100.],
        "target": [0., 25., 100., 50., 100., 0.],
    })


class ParametricBasisRiskTest(unittest.TestCase):
    def fit(self, frame):
        return calibrate_trigger(frame, "target", 100., train_end=4,
                                 declared_years=8, attachment_grid=(5., 6., 7.),
                                 decay_grid=(.5, 1.), step_grid=(.5, 1.))

    def test_exact_tier_boundaries_and_monotonicity(self):
        result = tier_payout([5.999, 6., 6.5, 7., 7.5, 8.], [0.] * 6,
                             attachment=6., decay=1., step=.5, principal=100.)
        np.testing.assert_array_equal(result, [0., 25., 50., 75., 100., 100.])
        farther = tier_payout([7.] * 3, [0., 50., 500.], attachment=6.,
                              decay=1., step=.5, principal=100.)
        self.assertTrue(np.all(np.diff(farther) <= 0.))

    def test_calibration_does_not_read_evaluation_or_correlated_losses(self):
        frame = feature_fixture()
        spec, candidates = self.fit(frame)
        altered = frame.copy()
        altered.loc[altered.catalog_year > 4, "target"] = np.nan
        altered["c1_loss"] = np.inf
        other, other_candidates = self.fit(altered)
        self.assertEqual(spec, other)
        pd.testing.assert_frame_equal(candidates, other_candidates)
        np.testing.assert_array_equal(predict_payout(frame, spec), predict_payout(altered, spec))
        self.assertEqual(candidates.selected.sum(), 2)

    def test_deterministic_tie_and_invalid_training_target(self):
        frame = feature_fixture()
        frame["target"] = 0.
        spec, _ = calibrate_trigger(frame, "target", 100., train_end=4,
                                    declared_years=8, attachment_grid=(10., 11.))
        self.assertTrue(all(x["candidate_id"] == 1 for x in spec["selected_by_source"].values()))
        frame.loc[0, "target"] = -1.
        with self.assertRaises(ValueError):
            self.fit(frame)

    def test_collateral_chronology_year_reset_and_row_order(self):
        frame = feature_fixture()
        nominal = np.full(6, 75.)
        actual = apply_annual_collateral(frame, nominal, 100., declared_years=8)
        np.testing.assert_array_equal(actual, [75., 75., 25., 75., 25., 75.])
        permutation = [4, 2, 0, 5, 1, 3]
        shuffled = apply_annual_collateral(frame.iloc[permutation], nominal, 100., declared_years=8)
        np.testing.assert_array_equal(shuffled, actual[permutation])
        annual = pd.Series(actual).groupby(frame.catalog_year).sum()
        self.assertTrue(annual.le(100.).all())

    def test_real_scale_collateral_conservation(self):
        frame = feature_fixture()
        principal = 61_837_983.314918146
        nominal = np.array([1., .75, .5, .25, 1., 1.]) * principal
        actual = apply_annual_collateral(frame, nominal, principal, declared_years=8)
        self.assertTrue(np.all(actual >= 0))
        self.assertTrue(np.all(actual <= nominal))
        totals = pd.Series(actual).groupby(frame.catalog_year).sum()
        self.assertLessEqual(float((totals - principal).max()), 1e-7)

    def test_surplus_and_shortfall_are_preserved_with_zero_years(self):
        frame = feature_fixture().iloc[:2].copy()
        frame["catalog_year"] = [1, 1]
        for p in ("i0", "c1", "c2"):
            frame[f"{p}_gross_insured_loss_2022_usd"] = [0., 40.]
            frame[f"{p}_frozen_occurrence_ceded_loss_2022_usd"] = [0., 30.]
        payout = np.array([100., 0.])
        annual = annual_basis_series(frame, {"nominal": payout, "collateralized": payout}, declared_years=4)
        self.assertEqual(len(annual), 4)
        self.assertEqual(annual.i0_cash_net_aep_2022_usd[0], -60.)
        self.assertEqual(annual.i0_surplus_aep_2022_usd[0], 60.)
        self.assertEqual(annual.i0_unfunded_aep_2022_usd[0], 0.)
        self.assertEqual(annual.i0_shortfall_sum_2022_usd[0], 30.)
        np.testing.assert_array_equal(annual.iloc[1:, 1:].to_numpy(), 0.)
        metrics = basis_metrics([0., 30.], payout, [0., 40.], declared_years=4)
        self.assertEqual(metrics["payout_aal_2022_usd"], 25.)
        self.assertEqual(metrics["expected_protection_shortfall_2022_usd"], 7.5)
        self.assertEqual(metrics["false_negative_probability_given_target"], 1.)
        self.assertEqual(metrics["false_positive_probability_given_payout"], 1.)
        tails = tail_rows(annual, return_periods=(2, 4))
        self.assertFalse(tails.headline_supported.any())

    def test_authoritative_distances_require_complete_unique_portfolio(self):
        frame = pd.DataFrame({"rupture_id": ["a", "a", "b", "b"],
                              "site_id": ["x", "y", "x", "y"], "r_rup_km": [3., 2., 1., 4.]})
        result = portfolio_distances(frame, ["x", "y"])
        np.testing.assert_array_equal(result.portfolio_distance_km, [2., 1.])
        for bad in (frame.iloc[:-1], pd.concat([frame, frame.iloc[:1]]), frame.assign(r_rup_km=np.nan)):
            with self.assertRaises(ValueError):
                portfolio_distances(bad, ["x", "y"])

    def test_invalid_features_terms_and_classification_inputs(self):
        for years in ([0], [1.5], [9], [np.nan]):
            with self.assertRaises(ValueError):
                year_indices(years, 8)
        with self.assertRaises(ValueError):
            tier_payout([7.], [-1.], attachment=6., decay=1., step=.5, principal=100.)
        frame = feature_fixture()
        spec, _ = self.fit(frame)
        frame.loc[0, "source_type"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            predict_payout(frame, spec)
        with self.assertRaises(ValueError):
            basis_metrics([2.], [0.], [1.], declared_years=8)


if __name__ == "__main__":
    unittest.main()
