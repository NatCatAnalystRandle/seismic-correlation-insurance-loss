"""Unit tests for paired Phase 2 damage and policy-loss calculations."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from tools.correlated_damage_loss import (
    CASE_PREFIXES,
    COMPONENT_NAMESPACES,
    PAIRED_LOSS_OUTPUT_COLUMNS,
    apply_policy_terms,
    build_paired_damage_loss_batch,
    build_site_parameter_table,
    damage_state_probabilities,
    deterministic_uniforms,
    fragility_columns,
    repair_ratio_columns,
    sample_damage_states,
    summarize_occurrences,
)


def synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    sites = ["S1", "S2"]
    structural = pd.DataFrame({"site_id": sites})
    nonstructural = pd.DataFrame({"site_id": sites})
    for component, frame in [
        ("structural", structural),
        ("nsd", nonstructural),
        ("nsa", nonstructural),
    ]:
        median_columns, beta_columns = fragility_columns(component)
        for column, value in zip(median_columns, [0.1, 0.2, 0.4, 0.8]):
            frame[column] = value
        for column in beta_columns:
            frame[column] = 0.6

    structural_values = pd.DataFrame({"site_id": sites})
    nonstructural_values = pd.DataFrame({"site_id": sites})
    component_ratios = {
        "structural": [0.0, 0.03, 0.08, 0.18, 0.30],
        "nsd": [0.0, 0.02, 0.07, 0.17, 0.30],
        "nsa": [0.0, 0.05, 0.15, 0.30, 0.40],
    }
    for component, values in component_ratios.items():
        target = structural_values if component == "structural" else nonstructural_values
        for column, value in zip(repair_ratio_columns(component), values):
            target[column] = value

    policy = pd.DataFrame(
        {
            "site_id": sites,
            "site_ordinal": [0, 1],
            "policy_covered": [True, True],
            "covered_loss_share": [1.0, 1.0],
            "building_replacement_value_2022_usd": [1_000_000.0, 2_000_000.0],
            "deductible_amount_2022_usd": [100_000.0, 200_000.0],
            "policy_limit_amount_2022_usd": [1_000_000.0, 2_000_000.0],
            "coinsurance_share": [1.0, 1.0],
        }
    )
    parameters = build_site_parameter_table(
        structural,
        nonstructural,
        structural_values,
        nonstructural_values,
        policy,
        expected_site_ids=sites,
    )

    rows: list[dict[str, object]] = []
    for occurrence_ordinal, (year, occurrence_id) in enumerate(
        [(2, "O1"), (7, "O2")]
    ):
        for site_ordinal, site_id in enumerate(sites):
            rows.append(
                {
                    "catalog_year": year,
                    "catalog_event_id": f"E{occurrence_ordinal}",
                    "occurrence_ordinal": occurrence_ordinal,
                    "occurrence_id": occurrence_id,
                    "rupture_ordinal": occurrence_ordinal,
                    "rupture_template_event_id": f"T{occurrence_ordinal}",
                    "rupture_id": f"R{occurrence_ordinal}",
                    "source_type": "INTERFACE",
                    "magnitude": 8.0,
                    "site_ordinal": site_ordinal,
                    "site_id": site_id,
                    "i0_sa0p4_simulated_g": 0.25,
                    "c1_sa0p4_simulated_g": 0.25,
                    "c2_sa0p4_simulated_g": 0.25,
                }
            )
    return pd.DataFrame(rows), parameters


class CorrelatedDamageLossTest(unittest.TestCase):
    def test_frozen_damage_uniforms(self) -> None:
        expected = {
            "structural": 0.9658458529034946,
            "nsd": 0.9496560570420585,
            "nsa": 0.4864409764634244,
        }
        for component, namespace in COMPONENT_NAMESPACES.items():
            actual = deterministic_uniforms(["O1"], ["S1"], namespace)[0]
            self.assertEqual(actual, expected[component])

    def test_damage_probabilities_and_inverse_cdf(self) -> None:
        probabilities, minimum = damage_state_probabilities(
            [0.2], [[0.1, 0.2, 0.4, 0.8]], [[0.6, 0.6, 0.6, 0.6]]
        )
        self.assertGreaterEqual(minimum, -1.0e-12)
        np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, atol=1.0e-15)
        states = sample_damage_states(
            np.repeat(probabilities, 5, axis=0),
            np.array([1.0e-12, 0.25, 0.50, 0.75, 1.0 - 1.0e-12]),
        )
        self.assertTrue(np.all((states >= 0) & (states <= 4)))
        self.assertEqual(int(states[0]), 0)
        self.assertEqual(int(states[-1]), 4)

    def test_phase1_policy_waterfall(self) -> None:
        result = apply_policy_terms(
            [50.0, 150.0, 1_500.0],
            [True, True, True],
            [1.0, 1.0, 1.0],
            [100.0, 100.0, 100.0],
            [1_000.0, 1_000.0, 1_000.0],
            [1.0, 1.0, 0.8],
        )
        np.testing.assert_allclose(
            result["gross_insured_loss_2022_usd"], [0.0, 50.0, 800.0]
        )
        np.testing.assert_allclose(
            result["policy_limit_absorbed_loss_2022_usd"], [0.0, 0.0, 400.0]
        )
        np.testing.assert_allclose(
            result["coinsurance_absorbed_loss_2022_usd"], [0.0, 0.0, 200.0]
        )
        np.testing.assert_allclose(
            result["uninsured_loss_2022_usd"], [50.0, 100.0, 700.0]
        )

    def test_site_parameters_reject_invalid_policy_share(self) -> None:
        _, parameters = synthetic_inputs()
        structural_medians, structural_betas = fragility_columns("structural")
        nsd_medians, nsd_betas = fragility_columns("nsd")
        nsa_medians, nsa_betas = fragility_columns("nsa")
        structural = parameters[
            ["site_id", *structural_medians, *structural_betas]
        ].copy()
        nonstructural = parameters[
            ["site_id", *nsd_medians, *nsd_betas, *nsa_medians, *nsa_betas]
        ].copy()
        structural_values = parameters[
            ["site_id", *repair_ratio_columns("structural")]
        ].copy()
        nonstructural_values = parameters[
            [
                "site_id",
                *repair_ratio_columns("nsd"),
                *repair_ratio_columns("nsa"),
            ]
        ].copy()
        policy = parameters[
            [
                "site_id",
                "site_ordinal",
                "policy_covered",
                "covered_loss_share",
                "building_replacement_value_2022_usd",
                "deductible_amount_2022_usd",
                "policy_limit_amount_2022_usd",
                "coinsurance_share",
            ]
        ].copy()
        policy.loc[0, "covered_loss_share"] = 1.01
        with self.assertRaises(ValueError):
            build_site_parameter_table(
                structural,
                nonstructural,
                structural_values,
                nonstructural_values,
                policy,
            )

    def test_equal_demands_produce_exactly_equal_case_losses(self) -> None:
        ground_motion, parameters = synthetic_inputs()
        output, diagnostics = build_paired_damage_loss_batch(
            ground_motion, parameters
        )
        self.assertEqual(list(output.columns), PAIRED_LOSS_OUTPUT_COLUMNS)
        self.assertEqual(diagnostics.rows, 4)
        self.assertEqual(diagnostics.occurrences, 2)
        self.assertEqual(diagnostics.nonfinite_output_count, 0)
        self.assertLessEqual(
            diagnostics.maximum_policy_reconciliation_error_2022_usd, 1.0e-9
        )
        prefixes = list(CASE_PREFIXES.values())
        for suffix in (
            "structural_damage_state",
            "nsd_damage_state",
            "nsa_damage_state",
            "total_ground_up_loss_2022_usd",
            "gross_insured_loss_2022_usd",
            "uninsured_loss_2022_usd",
        ):
            baseline = output[f"{prefixes[0]}_{suffix}"].to_numpy()
            for prefix in prefixes[1:]:
                np.testing.assert_array_equal(
                    output[f"{prefix}_{suffix}"].to_numpy(), baseline
                )

    def test_only_case_demand_changes_damage_result(self) -> None:
        ground_motion, parameters = synthetic_inputs()
        ground_motion["i0_sa0p4_simulated_g"] = 1.0e-8
        ground_motion["c1_sa0p4_simulated_g"] = 100.0
        output, _ = build_paired_damage_loss_batch(ground_motion, parameters)
        for component in COMPONENT_NAMESPACES:
            self.assertTrue((output[f"i0_{component}_damage_state"] == 0).all())
            self.assertTrue((output[f"c1_{component}_damage_state"] == 4).all())
        self.assertTrue((output["i0_total_ground_up_loss_2022_usd"] == 0.0).all())
        np.testing.assert_allclose(
            output["c1_total_ground_up_loss_2022_usd"],
            output["building_replacement_value_2022_usd"],
        )

    def test_occurrence_summary_reconciles(self) -> None:
        ground_motion, parameters = synthetic_inputs()
        output, _ = build_paired_damage_loss_batch(ground_motion, parameters)
        summary = summarize_occurrences(output)
        self.assertEqual(len(summary), 2)
        for prefix in CASE_PREFIXES.values():
            self.assertAlmostEqual(
                float(summary[f"{prefix}_total_ground_up_loss_2022_usd"].sum()),
                float(output[f"{prefix}_total_ground_up_loss_2022_usd"].sum()),
            )

    def test_incomplete_occurrence_is_rejected(self) -> None:
        ground_motion, parameters = synthetic_inputs()
        with self.assertRaises(ValueError):
            build_paired_damage_loss_batch(ground_motion.iloc[:-1], parameters)


if __name__ == "__main__":
    unittest.main(verbosity=2)
