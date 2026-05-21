"""Unit tests for scripts/check_claim_verification_report.py."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts._test_helpers import run_script

SCRIPT = Path(__file__).resolve().parent / "check_claim_verification_report.py"
FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "kg_contract"
    / "good_claim_verification_report.json"
)


def _run(path: Path):
    return run_script(SCRIPT, str(path))


class TestCheckClaimVerificationReport(unittest.TestCase):
    def test_good_fixture_passes(self) -> None:
        result = _run(FIXTURE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_invalid_total_claims_checked_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["summary"]["total_claims_checked"] = 2
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("total_claims_checked", result.stdout + result.stderr)

    def test_duplicate_claim_id_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["claims"].append(payload["claims"][0].copy())
            payload["summary"]["total_claims_checked"] = 2
            payload["summary"]["verdict_counts"]["VERIFIED"] = 2
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate claim_id", result.stdout + result.stderr)

    def test_kg_item_mismatch_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["claims"][0]["kg_review_update"]["kg_item_id"] = "claim:article-123:c999"
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("kg_item_id must equal claim_id", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
