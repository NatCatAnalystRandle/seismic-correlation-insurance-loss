"""Static reproducibility contracts for the committed Notebook 10 source."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "10_correlated_damage_and_loss.ipynb"


class Notebook10ReproducibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.sources = [
            "".join(cell.get("source", [])) for cell in cls.notebook["cells"]
        ]
        cls.full_source = "\n".join(cls.sources)

    def test_committed_notebook_is_clean_and_compilable(self) -> None:
        self.assertEqual(len(self.notebook["cells"]), 9)
        code_cells = [
            cell for cell in self.notebook["cells"] if cell["cell_type"] == "code"
        ]
        self.assertEqual(len(code_cells), 6)
        for index, cell in enumerate(code_cells):
            self.assertIsNone(cell["execution_count"])
            self.assertEqual(cell["outputs"], [])
            ast.parse("".join(cell["source"]), filename=f"notebook10_code_{index}")

    def test_phase1_damage_and_policy_controls_are_frozen(self) -> None:
        required = [
            "notebook5_structural_damage_v1",
            "notebook5_nonstructural_drift_damage_v1",
            "notebook5_nonstructural_acceleration_damage_v1",
            "baseline_full_coverage_10pct_deductible_v1",
            "be93474ce2ab78d8002d49ae861adb641ae2741d",
            "391_844_900_060.5801",
            "245_959_119_934.65695",
            "145_885_780_125.9232",
            "3_290_326",
            "2_366_776",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_paired_damage_and_policy_contracts_are_explicit(self) -> None:
        required = [
            "I0_PHASE1_INDEPENDENT",
            "C1_ALDEA22_SUBDUCTION",
            "C2_GODA_ATKINSON09",
            "build_paired_damage_loss_batch",
            "structural_ground_up_loss_2022_usd",
            "nsd_ground_up_loss_2022_usd",
            "nsa_ground_up_loss_2022_usd",
            "deductible_absorbed_loss_2022_usd",
            "policy_limit_absorbed_loss_2022_usd",
            "coinsurance_absorbed_loss_2022_usd",
            "gross_insured_loss_2022_usd",
            "uninsured_loss_2022_usd",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_restart_and_deterministic_output_contracts_are_explicit(self) -> None:
        required = [
            "NOTEBOOK10_EVENT_BATCH_SIZE",
            "notebook_10_correlated_damage_loss_work",
            "completion_markers",
            "mtime=0",
            'float_format="%.17g"',
            "basis_hash",
            "input_sha256",
            "output_sha256",
            "validation_sha256",
            "marker_sha256",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_i0_acceptance_requires_exact_states_and_financial_reconciliation(self) -> None:
        required = [
            "i0_damage_state_counts_reproduce_phase1_exactly",
            "i0_financial_totals_reproduce_phase1",
            'f"i0_{component}_damage_states_exact"',
            '"structural": "sampled_structural_damage_state"',
            '"nsd": "sampled_nsd_damage_state"',
            '"nsa": "sampled_nsa_damage_state"',
            "AGGREGATE_TOLERANCE_USD = 0.01",
            "ROW_TOLERANCE_USD = 2.0e-6",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_annual_and_tail_output_contracts_are_explicit(self) -> None:
        required = [
            "EXPECTED_CATALOG_YEARS = 2_000_000",
            "EXPECTED_ZERO_EVENT_YEARS = 1_989_407",
            "paired_annual_loss_series.csv.gz",
            "catalog_occurrence_count",
            "annual_series_includes_all_zero_event_years",
            "i0_annual_metrics_reproduce_phase1",
            "maximum_annual_error",
            "empirical_pml",
            "tail_support_sufficient",
            "order_statistic_rank",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_public_metadata_is_portable_and_time_independent(self) -> None:
        self.assertIn("project_relative_path", self.full_source)
        self.assertIn("public_paths_are_repository_relative", self.full_source)
        forbidden = [
            "created_at_utc",
            "completed_at_utc",
            "datetime.now",
            "datetime.utcnow",
            "C:\\Users\\",
        ]
        for value in forbidden:
            self.assertNotIn(value, self.full_source)

    def test_handoff_to_notebook11_is_explicit(self) -> None:
        required = [
            "notebook10_correlated_damage_loss_handoff_v1",
            "11_reinsurance_sensitivity_and_capital.ipynb",
            "retained, ceded, capital, TVaR",
            "risk-adjusted-return",
        ]
        for value in required:
            self.assertIn(value, self.full_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
