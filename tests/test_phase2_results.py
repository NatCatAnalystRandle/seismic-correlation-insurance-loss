"""Behavioral checks for frozen-artifact audits and paired synthesis."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from tools.phase2_results import (
    BASELINE, CASE_PREFIXES, attachment_diagnostics, check_artifact,
    paired_comparison, safe_path,
    normalize_svg_bytes, normalize_publication_svgs, inventory_item, write_json,
)


class Phase2ResultsTest(unittest.TestCase):
    def test_svg_whitespace_has_identical_LF_and_CRLF_results(self):
        original = b'<svg><path d="M 0 0 \nL 1 1 \t\n"/></svg>\n'
        expected = b'<svg><path d="M 0 0\nL 1 1\n"/></svg>\n'
        self.assertEqual(normalize_svg_bytes(original), expected)
        self.assertEqual(normalize_svg_bytes(original.replace(b"\n", b"\r\n")), expected)
        self.assertEqual(normalize_svg_bytes(expected), expected)

    def test_publication_repair_verifies_originals_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prefix = root / "data/processed/phase_2/notebook_13_phase_2_results/plots"
            prefix.mkdir(parents=True)
            paths = []
            for i in range(5):
                path = prefix / f"fixture_{i}.svg"
                path.write_bytes(b'<svg><path d="M 0 0 \r\nL 1 1 \r\n"/></svg>\r\n')
                paths.append(path)
            csv_path = root / "result.csv"
            csv_path.write_bytes(b"loss\n1\n")
            hpath = root / "data/metadata/phase_2/notebook_13_phase_2_results/notebook_13_final_handoff.json"
            original_h = dict(notebook13_complete=True, mode="production", source={"original": "preserved"},
                              artifact_inventory=[inventory_item(root, p) for p in [*paths, csv_path]])
            write_json(hpath, original_h)
            original_svgs = [p.read_bytes() for p in paths]
            csv_path.write_bytes(b"loss\n2\n")
            with self.assertRaisesRegex(RuntimeError, "Original artifact"):
                normalize_publication_svgs(root)
            self.assertEqual(original_svgs, [p.read_bytes() for p in paths])
            csv_path.write_bytes(b"loss\n1\n")
            self.assertEqual(normalize_publication_svgs(root), 5)
            h = json.loads(hpath.read_text())
            self.assertEqual(h["source"], original_h["source"])
            for old, new in zip(original_h["artifact_inventory"][:5], h["artifact_inventory"][:5]):
                self.assertEqual(new["pre_publication_sha256"], old["sha256"])
                self.assertEqual(check_artifact(root, new)[0], "PASS")
            self.assertEqual(csv_path.read_bytes(), b"loss\n1\n")
            before = hpath.read_bytes()
            self.assertEqual(normalize_publication_svgs(root), 0)
            self.assertEqual(hpath.read_bytes(), before)

    def test_byte_audit_detects_tampering_and_requires_explicit_legacy_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "test.json"
            original = b'{\r\n  "x": 1\r\n}\r\n'
            item = dict(path="test.json", bytes=len(original), sha256=hashlib.sha256(original).hexdigest())
            path.write_bytes(original)
            self.assertEqual(check_artifact(root, item)[:2], ("PASS", "raw"))
            path.write_bytes(original.replace(b"\r\n", b"\n"))
            self.assertEqual(check_artifact(root, item)[0], "FAIL")
            self.assertEqual(check_artifact(root, item, legacy_crlf=True)[:2], ("PASS", "legacy_crlf_reconstruction"))
            path.write_bytes(path.read_bytes().replace(b"1", b"2"))
            self.assertEqual(check_artifact(root, item, legacy_crlf=True)[0], "FAIL")

    def test_nonportable_or_escaping_paths_rejected(self):
        for path in ("../secret", "/tmp/file", "C:/data/file", "data\\file"):
            with self.assertRaises(ValueError):
                safe_path(Path.cwd(), path)

    def test_comparisons_pair_scenarios_not_row_positions(self):
        rows = [dict(case_name=c, scenario=k, loss=v+i) for i,c in enumerate(CASE_PREFIXES) for k,v in [("a", 0.), ("b", 10.)]]
        frame = pd.DataFrame(rows).sample(frac=1, random_state=7)
        result = paired_comparison(frame, ["scenario"], ["loss"])
        c1 = result.loc[result.case_name.eq(list(CASE_PREFIXES)[1])]
        self.assertTrue(c1.absolute_change.eq(1).all())
        self.assertTrue(result.loc[result.scenario.eq("a"), "percent_change"].isna().all())
        self.assertEqual(c1.loc[c1.scenario.eq("b"), "percent_change"].iloc[0], 10.)
        with self.assertRaises(ValueError):
            paired_comparison(frame.iloc[:-1], ["scenario"], ["loss"])
        with self.assertRaises(ValueError):
            paired_comparison(pd.concat([frame, frame.iloc[:1]]), ["scenario"], ["loss"])

    def test_attachment_ties_do_not_create_spurious_optimum(self):
        score = "tvar99_5_capital_relief_per_expected_ceded_dollar"
        grid = pd.DataFrame(dict(case_name=[BASELINE]*3, attachment_2022_usd=[10.,20.,30.], **{score:[199.,np.nextafter(199., np.inf),199.]}))
        row = attachment_diagnostics(grid).iloc[0]
        self.assertEqual(row.tied_designs, 3)
        self.assertTrue(pd.isna(row.selected_attachment_2022_usd))
        grid.loc[2, score] = 200.
        self.assertEqual(attachment_diagnostics(grid).iloc[0].selected_attachment_2022_usd, 30.)


if __name__ == "__main__":
    unittest.main()
