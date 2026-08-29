"""Static reproducibility contracts for the committed Notebook 09 source."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "09_generate_correlated_ground_motion_fields.ipynb"


class Notebook09ReproducibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.sources = ["".join(cell.get("source", [])) for cell in cls.notebook["cells"]]
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
            ast.parse("".join(cell["source"]), filename=f"notebook09_code_{index}")

    def test_phase1_controls_are_frozen(self) -> None:
        required = [
            "EXPECTED_OCCURRENCES = 10_630",
            "EXPECTED_PARTITIONS = 16",
            "EXPECTED_BASE_SEED = 20260731",
            "e4725a57eab466348aa263d79b8f8bcc923f9542fb5507af279fece41c121f37",
            "5d202929c997c262abfd068e47ba7c7fdba91873af8135d28dfec35b78193e5b",
            "fc64d53410fdadab5379f82c73c1d74ce3393911fbdd73a0dbc483f056f3d100",
            "be93474ce2ab78d8002d49ae861adb641ae2741d",
            "numpy.random.PCG64DXSM",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_paired_case_and_output_contracts_are_explicit(self) -> None:
        required = [
            "I0_PHASE1_INDEPENDENT",
            "C1_ALDEA22_SUBDUCTION",
            "C2_GODA_ATKINSON09",
            "paired_ground_motion_fields.csv.gz",
            "PAIRED_OUTPUT_COLUMNS",
            "notebook9_correlated_ground_motion_handoff_v1",
            "one catalog occurrence and one site",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_restart_and_deterministic_output_contracts_are_explicit(self) -> None:
        required = [
            "NOTEBOOK9_EVENT_BATCH_SIZE",
            "notebook_9_correlated_ground_motion_work",
            "completion_markers",
            "mtime=0",
            "float_format=\"%.17g\"",
            "phase1_input_sha256",
            "factor_sha256",
            "module_sha256",
            "validation_sha256",
        ]
        for value in required:
            self.assertIn(value, self.full_source)

    def test_public_metadata_is_portable_and_time_independent(self) -> None:
        self.assertIn("project_relative_path", self.full_source)
        self.assertIn("metadata_paths_portable", self.full_source)
        forbidden = [
            "created_at_utc",
            "datetime.now",
            "datetime.utcnow",
            "C:\\\\Users\\\\",
        ]
        for value in forbidden:
            self.assertNotIn(value, self.full_source)

    def test_full_catalog_validation_is_required(self) -> None:
        required = [
            "final_row_count",
            "final_occurrence_count",
            "residual_means",
            "residual_standard_deviations",
            "same_site_cross_imt_correlation",
            "selected_pair_correlations",
            "maximum_selected_pair_correlation_error",
        ]
        for value in required:
            self.assertIn(value, self.full_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
