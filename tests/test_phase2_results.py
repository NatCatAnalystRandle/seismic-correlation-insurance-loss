"""Behavioral checks for frozen-artifact audits and paired synthesis."""
import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from tools.phase2_results import (
    BASELINE, CASE_PREFIXES, attachment_diagnostics, check_artifact,
    paired_comparison, safe_path,
)


class Phase2ResultsTest(unittest.TestCase):
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
