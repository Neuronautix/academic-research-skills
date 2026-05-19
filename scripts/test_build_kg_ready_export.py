"""Unit tests for scripts/build_kg_ready_export.py."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts._test_helpers import run_script

SCRIPT = Path(__file__).resolve().parent / "build_kg_ready_export.py"
FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "kg_contract"
)


class TestBuildKgReadyExport(unittest.TestCase):
    def test_build_package_success(self) -> None:
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            result = run_script(
                SCRIPT,
                "--article",
                str(FIXTURE_DIR / "article.md"),
                "--kg-handoff",
                str(FIXTURE_DIR / "good_kg_handoff.json"),
                "--claim-verification",
                str(FIXTURE_DIR / "good_claim_verification_report.json"),
                "--output-dir",
                str(out),
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((out / "manifest.json").exists())
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["validation"]["overall"], "pass")

    def test_build_package_fails_on_invalid_contract(self) -> None:
        with TemporaryDirectory() as tmp:
            bad_claim = Path(tmp) / "bad_claim.json"
            payload = json.loads(
                (FIXTURE_DIR / "good_claim_verification_report.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["summary"]["total_claims_checked"] = 999
            bad_claim.write_text(json.dumps(payload), encoding="utf-8")

            out = Path(tmp) / "pkg"
            result = run_script(
                SCRIPT,
                "--article",
                str(FIXTURE_DIR / "article.md"),
                "--kg-handoff",
                str(FIXTURE_DIR / "good_kg_handoff.json"),
                "--claim-verification",
                str(bad_claim),
                "--output-dir",
                str(out),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("total_claims_checked", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
