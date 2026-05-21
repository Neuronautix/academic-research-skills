"""Unit tests for scripts/check_kg_audit_report.py."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts._test_helpers import run_script

SCRIPT = Path(__file__).resolve().parent / "check_kg_audit_report.py"
FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "kg_contract"
    / "good_kg_audit_report.json"
)


def _run(path: Path):
    return run_script(SCRIPT, str(path))


class TestCheckKgAuditReport(unittest.TestCase):
    def test_good_fixture_passes(self) -> None:
        result = _run(FIXTURE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_summary_mismatch_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["summary"]["unresolved_high_warn_count"] = 0
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unresolved_high_warn_count", result.stdout + result.stderr)

    def test_duplicate_finding_id_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["findings"].append(payload["findings"][0].copy())
            payload["summary"]["total_findings"] = 2
            payload["summary"]["unresolved_high_warn_count"] = 2
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate finding_id", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
