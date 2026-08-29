"""Static reproducibility contracts for the committed Notebook 11 source."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "11_reinsurance_sensitivity_and_capital.ipynb"


class Notebook11ReproducibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.sources = [
            "".join(cell.get("source", [])) for cell in cls.notebook["cells"]
        ]
        cls.full_source = "\n".join(cls.sources)

    def test_committed_notebook_is_clean_and_compilable(self) -> None:
        self.assertEqual(len(self.notebook["cells"]), 11)
        code_cells = [
            cell for cell in self.notebook["cells"] if cell["cell_type"] == "code"
        ]
        self.assertEqual(len(code_cells), 8)
        for index, cell in enumerate(code_cells):
            self.assertIsNone(cell["execution_count"])
            self.assertEqual(cell["outputs"], [])
            ast.parse("".join(cell["source"]), filename=f"notebook11_code_{index}")

    def test_frozen_phase1_occurrence_terms_and_cases_are_explicit(self) -> None:
        required = [
            "baseline_occurrence_xol_500yr_to_2500yr_oep_v1",
            "18_811_083.54014544",
            "61_837_983.314918146",
            "80_649_066.85506359",
            "I0_PHASE1_INDEPENDENT",
            "C1_ALDEA22_SUBDUCTION",
            "C2_GODA_ATKINSON09",
            "NO_REINSURANCE",
            "FROZEN_OCCURRENCE_XOL",
            "STANDALONE_AGGREGATE",
            "STACKED_OCCURRENCE_PLUS_AGGREGATE",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_sensitivity_design_is_common_across_cases(self) -> None:
        required = [
            "ATTACHMENT_RETURN_PERIODS = [100, 250, 500, 1_000]",
            "EXHAUSTION_RETURN_PERIODS = [1_000, 2_500, 5_000, 10_000]",
            "STANDALONE_ANNUAL_AGGREGATE",
            "STACKED_AFTER_FROZEN_OCCURRENCE",
            "notebook_11_occurrence_design_grid.csv",
            "notebook_11_aggregate_design_grid.csv",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_tail_risk_and_sparse_var_boundary_are_explicit(self) -> None:
        required = [
            "CONFIDENCE_LEVELS",
            "empirical_pml",
            "retained_var_economic_capital_floored_99_5_2022_usd",
            "retained_tvar_tail_capital_99_5_2022_usd",
            "var_capital_informative_99_5",
            "gross annual VaR is zero",
            "TVaR tail capital",
            "order-statistic rank below 20",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_capital_limit_and_diversification_contracts_are_explicit(self) -> None:
        required = [
            "minimum_occurrence_limit_for_target",
            "classification_tolerance=ROW_TOLERANCE_USD",
            '("aep_pml", 2_500.0, target_pml_2500)',
            '("aep_tvar", 0.995, target_tvar_99_5)',
            "notebook_11_required_limit_summary.csv",
            "diversification_from_sparse_units",
            "diversification_benefit",
            "notebook_11_diversification_summary.csv",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_paired_monte_carlo_uncertainty_is_explicit(self) -> None:
        required = [
            "NOTEBOOK11_BOOTSTRAP_REPLICATES",
            "paired_bootstrap_differences",
            "BOOTSTRAP_SEED = 112_026",
            "aep_pml_10000yr",
            "notebook_11_uncertainty_summary.csv",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_raroc_is_only_a_transparent_assumption_grid(self) -> None:
        required = [
            "PREMIUM_MULTIPLES_OF_GROSS_AAL",
            "EXPENSE_RATIOS",
            "CEDED_PRICE_MULTIPLIERS",
            "break_even_required_earned_premium_2022_usd",
            "raroc_using_tvar99_5_tail_capital",
            "assumption grid; not a quoted price",
            "no central price or recommended quote",
            "no_central_raroc_selected",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_deterministic_and_portable_output_contracts_are_explicit(self) -> None:
        required = [
            "project_relative_path",
            "sha256_lf_normalized_text",
            "mtime=0",
            'float_format="%.17g"',
            "write_bytes",
            "artifact_inventory",
            "public_paths_are_repository_relative",
        ]
        for value in required:
            self.assertIn(value, self.full_source)
        forbidden = [
            "created_at_utc",
            "completed_at_utc",
            "datetime.now",
            "datetime.utcnow",
            "C:\\Users\\",
        ]
        for value in forbidden:
            self.assertNotIn(value, self.full_source)

    def test_handoff_to_notebook12_is_explicit(self) -> None:
        required = [
            "notebook11_reinsurance_capital_handoff_v1",
            "12_parametric_cat_bond_basis_risk.ipynb",
            "parametric catastrophe-bond basis risk",
            "parametric trigger",
        ]
        for value in required:
            self.assertIn(value, self.full_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
