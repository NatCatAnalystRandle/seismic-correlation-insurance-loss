"""Execute the actual Notebook 12 cells against a small, auditable catalog."""

import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from tools.reinsurance_capital import CASE_PREFIXES, apply_occurrence_xol


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "12_parametric_cat_bond_basis_risk.ipynb"


class Notebook12ReproducibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.sources = {cell["id"]: "".join(cell["source"]) for cell in cls.notebook["cells"] if cell["cell_type"] == "code"}

    def setup_namespace(self):
        namespace = {}
        # Display formatting is outside the numerical integration test. This
        # permits the standard unittest suite without installing Jupyter itself.
        from types import ModuleType
        ipython = ModuleType("IPython")
        display_module = ModuleType("IPython.display")
        display_module.display = lambda *args, **kwargs: None
        with patch("pathlib.Path.cwd", return_value=ROOT), patch.dict("sys.modules", {"IPython": ipython, "IPython.display": display_module}):
            exec(self.sources["nb12-setup"], namespace)
        return namespace

    def install_fixture(self, namespace, root):
        n = namespace
        n.update(ROOT=root, META=root / "data/metadata/phase_2/notebook_12_parametric_basis_risk",
                 PROCESSED=root / "data/processed/phase_2/notebook_12_parametric_basis_risk",
                 CATALOG_YEARS=8, TRAIN_END=4, EXPECTED_OCCURRENCES=6,
                 EXPECTED_OCCUPIED_YEARS=4, EXPECTED_SITES=2, EXPECTED_RUPTURES=3,
                 FROZEN_ATTACHMENT=20., PRINCIPAL=100., BOOTSTRAP_REPLICATES=20,
                 RETURN_PERIODS=(2, 4, 8))
        events = pd.DataFrame({"catalog_event_id": list("abcdef"),
            "occurrence_id": ["Y1|a", "Y2|b", "Y2|c", "Y5|d", "Y5|e", "Y8|f"],
            "catalog_year": [1, 2, 2, 5, 5, 8], "rupture_id": ["x", "y", "z", "x", "y", "z"],
            "source_type": ["INTERFACE", "SLAB", "INTERFACE"]*2,
            "magnitude": [np.nextafter(6., np.inf), 7., 8., 6., 7., 8.]})
        program_rows = []
        for i, (case, prefix) in enumerate(CASE_PREFIXES.items()):
            gross = np.array([0., 45., 150., 60., 0., 80.]) * (1 + .2*i)
            layer = apply_occurrence_xol(gross, 20., 100.)
            events[f"{prefix}_gross_insured_loss_2022_usd"] = gross
            events[f"{prefix}_frozen_occurrence_ceded_loss_2022_usd"] = layer["ceded_loss_2022_usd"]
            events[f"{prefix}_frozen_occurrence_retained_loss_2022_usd"] = layer["retained_loss_2022_usd"]
            program_rows.append(dict(case_prefix=prefix, program="FROZEN_OCCURRENCE_XOL", ceded_aal_2022_usd=float(layer["ceded_loss_2022_usd"].sum()/8)))
        event_path = root / "input/events.csv.gz"
        validation_path = root / "input/validation.csv"
        n["write_csv"](event_path, events)
        n["write_csv"](validation_path, pd.DataFrame([dict(check_id="fixture", severity="critical", passed=True)]))
        catalog = events[["catalog_event_id", "catalog_year", "rupture_id", "source_type", "magnitude"]].rename(columns={"catalog_event_id": "event_id", "catalog_year": "simulation_year"})
        catalog["time_within_year"] = [.1, .2, .3, .1, .9, .5]
        catalog["magnitude"] = [6., 7., 8.]*2
        site_frame = pd.DataFrame({"site_id": ["s1", "s2"], "site_ordinal": [0, 1]})
        distance_frame = pd.DataFrame({"rupture_id": ["x", "x", "y", "y", "z", "z"], "site_id": ["s1", "s2"]*3, "r_rup_km": [0., 10., 50., 60., 20., 25.]})
        input_frames = {"catalog": catalog, "sites": site_frame, "distances": distance_frame}
        for name, frame in input_frames.items():
            path = root / n["INPUTS"][name]["path"]
            n["write_csv"](path, frame)
            n["INPUTS"][name]["sha256"] = n["sha256_file"](path, n["INPUTS"][name].get("hash_mode", "raw"))
        for name in ("parametric_module", "reinsurance_module"):
            item = n["INPUTS"][name]
            path = root / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / item["path"]).read_bytes())
        handoff = dict(notebook11_complete=True, dependence_cases=list(CASE_PREFIXES),
            validation={"critical_failures": 0, "path": "input/validation.csv"},
            frozen_controls=dict(catalog_years=8, occurrences=6, sites=2,
                phase1_release="fixture", phase1_commit="fixture",
                occurrence_layer=dict(attachment_2022_usd=20., limit_2022_usd=100., participation=1.)),
            artifact_inventory=[n["inventory_item"](event_path), n["inventory_item"](validation_path)],
            output_contract={"event_reinsurance": {"path": "input/events.csv.gz"}},
            fixed_program_results=program_rows)
        path = root / n["INPUTS"]["notebook11_handoff"]["path"]
        n["write_json"](path, handoff)
        n["INPUTS"]["notebook11_handoff"]["sha256"] = n["sha256_file"](path)

    def test_clean_source_and_published_input_hashes(self):
        self.assertEqual(len(self.notebook["cells"]), 11)
        for cell in self.notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                ast.parse("".join(cell["source"]))
        with redirect_stdout(io.StringIO()):
            n = self.setup_namespace()
        for item in n["INPUTS"].values():
            self.assertEqual(len(item["sha256"]), 64)
            if (ROOT / item["path"]).is_file():
                self.assertEqual(n["sha256_file"](ROOT / item["path"], item.get("hash_mode", "raw")), item["sha256"])
        nb9 = json.loads((ROOT / "data/metadata/phase_2/notebook_9_correlated_ground_motion/notebook_9_final_handoff.json").read_text())
        self.assertEqual(n["INPUTS"]["catalog"]["sha256"], nb9["frozen_controls"]["catalog_sha256"])

    def test_all_production_cells_on_small_catalog_and_deterministic_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            n = self.setup_namespace()
            self.install_fixture(n, Path(directory))
            for name, source in self.sources.items():
                if name != "nb12-setup":
                    exec(compile(source, name, "exec"), n)
            validation = n["final_validation"]
            self.assertTrue(validation.loc[validation.severity.eq("critical"), "passed"].all())
            self.assertEqual(n["annual"].catalog_occurrence_count.tolist(), [1, 2, 0, 0, 2, 0, 0, 1])
            for item in n["handoff"]["artifact_inventory"]:
                path = Path(directory) / item["path"]
                self.assertEqual(path.stat().st_size, item["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
            # JSON artifacts use literal LF even on Windows, and nested trigger
            # hashes stay consistent with the artifact inventory.
            for path in n["META"].glob("*.json"):
                self.assertNotIn(b"\r", path.read_bytes())
                json.loads(path.read_text())
            first_hash = n["sha256_file"](n["ANNUAL_PATH"])
            n["write_csv"](n["ANNUAL_PATH"], n["annual"])
            self.assertEqual(first_hash, n["sha256_file"](n["ANNUAL_PATH"]))
            loaded = n["read_csv"](n["ANNUAL_PATH"])
            pd.testing.assert_frame_equal(loaded, n["annual"], check_dtype=False, check_exact=True)
            self.assertEqual(n["handoff"]["trigger"]["sha256"], n["FROZEN_TRIGGER_HASH"])
            self.assertEqual(n["handoff"]["next_notebook"], "13_phase_2_results_and_validation.ipynb")

    def test_corrupted_input_stops_before_calibration(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            n = self.setup_namespace()
            self.install_fixture(n, Path(directory))
            n["INPUTS"]["catalog"]["sha256"] = "0"*64
            with self.assertRaisesRegex(RuntimeError, "frozen input hashes"):
                exec(self.sources["nb12-inputs"], n)
            self.assertFalse(n["META"].exists())


if __name__ == "__main__":
    unittest.main()
