"""Unit tests for scripts/check_kg_passport_extension.py."""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from scripts._test_helpers import run_script

SCRIPT = Path(__file__).resolve().parent / "check_kg_passport_extension.py"
FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "kg_contract"
    / "good_passport_with_kg_extension.yaml"
)


def _run(path: Path):
    return run_script(SCRIPT, str(path))


class TestCheckKgPassportExtension(unittest.TestCase):
    def test_good_fixture_passes(self) -> None:
        result = _run(FIXTURE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_missing_competency_questions_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_scope"]["competency_questions"] = []
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("competency_questions", result.stdout + result.stderr)

    def test_clean_kg_eligible_with_unresolved_assertion_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            payload["kg_assertions"][0]["review_status"] = "candidate"
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("clean_kg_eligible=true", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
