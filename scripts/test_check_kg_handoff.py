"""Unit tests for scripts/check_kg_handoff.py."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts._test_helpers import run_script

SCRIPT = Path(__file__).resolve().parent / "check_kg_handoff.py"
FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "kg_contract"
    / "good_kg_handoff.json"
)


def _run(path: Path):
    return run_script(SCRIPT, str(path))


class TestCheckKgHandoff(unittest.TestCase):
    def test_good_fixture_passes(self) -> None:
        result = _run(FIXTURE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_missing_required_field_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            del payload["run_metadata"]
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("run_metadata", result.stdout + result.stderr)

    def test_missing_link_target_fails_semantic_check(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["links"][0]["to_id"] = "evidence:article-123:missing"
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("to_id does not exist", result.stdout + result.stderr)

    def test_orphan_evidence_without_note_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["items"][2]["related_evidence_ids"] = []
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("orphaned", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
