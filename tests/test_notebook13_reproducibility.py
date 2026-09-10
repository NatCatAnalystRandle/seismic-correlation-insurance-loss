"""Execute all Notebook 13 cells on the actual committed metadata in preview.

Private production files are intentionally absent. Their absence must prevent
production completion; no synthetic loss results are presented as validation.
"""
import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from tools.phase2_results import DIRECTORIES, audit_upstream, sha256_file

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "13_phase_2_results_and_validation.ipynb"


class Notebook13ReproducibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.sources = {c["id"]: "".join(c["source"]) for c in cls.nb["cells"] if c["cell_type"] == "code"}

    def fixture(self, root):
        for directory in DIRECTORIES.values():
            relative = Path("data/metadata/phase_2") / directory
            shutil.copytree(ROOT / relative, root / relative)
        shutil.copyfile(NOTEBOOK, root / NOTEBOOK.name)
        (root / "tools").mkdir()
        shutil.copyfile(ROOT / "tools/phase2_results.py", root / "tools/phase2_results.py")
        n = {}
        # The scientific suite does not require a Jupyter installation.
        display_module = ModuleType("IPython.display")
        display_module.display = display_module.Image = display_module.Markdown = lambda *a, **k: None
        with patch("pathlib.Path.cwd", return_value=root), patch.dict("sys.modules", {"IPython": ModuleType("IPython"), "IPython.display": display_module}):
            exec(self.sources["nb13-setup"], n)
        n["display"] = lambda *args, **kwargs: None
        return n

    def test_clean_compilable_source_defaults_to_production(self):
        for c in self.nb["cells"]:
            if c["cell_type"] == "code":
                self.assertIsNone(c["execution_count"])
                self.assertEqual(c["outputs"], [])
                ast.parse("".join(c["source"]))
        self.assertIn("VERIFY_PROCESSED_ARTIFACTS = True", self.sources["nb13-setup"])

    def test_production_missing_private_files_stops_before_outputs(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            root = Path(d)
            n = self.fixture(root)
            with self.assertRaisesRegex(RuntimeError, "artifact audit failed"):
                exec(self.sources["nb13-inputs"], n)
            self.assertFalse((root / "data/metadata/phase_2/notebook_13_phase_2_results").exists())

    def test_all_preview_cells_and_deterministic_hashed_outputs(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            root = Path(d)
            n = self.fixture(root)
            n["VERIFY_PROCESSED_ARTIFACTS"] = False
            for name, source in self.sources.items():
                if name != "nb13-setup":
                    exec(compile(source, name, "exec"), n)
            self.assertFalse(n["handoff"]["notebook13_complete"])
            self.assertEqual(n["handoff"]["mode"], "metadata_preview")
            self.assertEqual(n["audit"].status.eq("SKIPPED").sum(), 10)
            self.assertEqual(len(n["upstream_validation"]), 99)
            self.assertEqual(len(n["results"]["paired_uncertainty"]), 84)
            self.assertEqual(len(n["figure_paths"]), 10)
            self.assertTrue(n["results"]["attachment_selection_diagnostics"].tied_designs.eq(15).all())
            for item in n["handoff"]["artifact_inventory"]:
                p = root / item["path"]
                self.assertEqual(p.stat().st_size, item["bytes"])
                self.assertEqual(sha256_file(p), item["sha256"])
            old = {p.name: sha256_file(p) for p in n["figure_paths"]}
            n["make_figures"](n["tables"], n["results"], n["FIGURES"])
            self.assertEqual(old, {p.name: sha256_file(p) for p in n["figure_paths"]})
            handoff_bytes = n["handoff_path"].read_bytes()
            exec(self.sources["nb13-handoff"], n)
            self.assertEqual(handoff_bytes, n["handoff_path"].read_bytes())
            # Changing the flag after a skipped audit cannot claim production.
            n["VERIFY_PROCESSED_ARTIFACTS"] = True
            exec(self.sources["nb13-handoff"], n)
            self.assertFalse(n["handoff"]["notebook13_complete"])

    def test_changed_public_table_is_rejected_even_in_preview(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            root = Path(d)
            self.fixture(root)
            path = root / "data/metadata/phase_2/notebook_11_reinsurance_capital/notebook_11_program_summary.csv"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(RuntimeError, "artifact audit failed"):
                audit_upstream(root, verify_processed=False)

    def test_legacy_windows_handoff_uses_only_the_exact_pinned_LF_view(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            root = Path(d)
            self.fixture(root)
            path = root / "data/metadata/phase_2/notebook_8_spatial_correlation/notebook_8_final_handoff.json"
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            audit, _, _ = audit_upstream(root, verify_processed=False)
            self.assertEqual(audit.iloc[0].hash_mode, "legacy_lf_handoff_view")
            path.write_bytes(path.read_bytes().replace(b"2000000", b"2000001"))
            with self.assertRaisesRegex(RuntimeError, "handoff hash mismatch"):
                audit_upstream(root, verify_processed=False)


if __name__ == "__main__":
    unittest.main()
