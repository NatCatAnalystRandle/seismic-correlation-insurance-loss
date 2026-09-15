"""Static reproducibility-contract tests for Phase 2 Notebook 08."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = (
    REPOSITORY_ROOT / "08_spatial_correlation_model_and_validation.ipynb"
)


class Notebook08ReproducibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.source = "\n".join(
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
        )

    def test_committed_notebook_is_clean_and_deterministic(self) -> None:
        self.assertEqual(len(self.notebook["cells"]), 9)
        cell_ids = [cell["id"] for cell in self.notebook["cells"]]
        self.assertEqual(len(cell_ids), len(set(cell_ids)))
        for cell in self.notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_public_metadata_uses_repository_relative_paths(self) -> None:
        self.assertIn("def project_relative_path(path: Path)", self.source)
        self.assertIn("artifact_paths_are_repository_relative", self.source)
        self.assertNotIn('"factor_path": str(factor_path)', self.source)
        self.assertNotIn('"path": str(path)', self.source)

    def test_hash_tracked_metadata_excludes_runtime_timestamps(self) -> None:
        self.assertIn("metadata_excludes_runtime_timestamps", self.source)
        self.assertNotIn('"created_at_utc":', self.source)
        self.assertNotIn("datetime.now", self.source)

    def test_portable_handoff_schema_is_explicit(self) -> None:
        self.assertIn(
            '"schema_version": "notebook8_spatial_correlation_handoff_v2"',
            self.source,
        )
        self.assertIn(
            'PIPELINE_VERSION = "notebook8_spatial_correlation_model_validation_v2"',
            self.source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
