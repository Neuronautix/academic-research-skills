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

    def test_kg_schema_requires_user_validation(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_schema"]["hitl_gate"]["user_validated"] = False
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("user_validated must be true", result.stdout + result.stderr)

    def test_force_alignment_requires_targets(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_schema"]["ontology_alignment_targets"] = []
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ontology_alignment_targets", result.stdout + result.stderr)

    def test_assertions_require_kg_schema(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            del payload["kg_schema"]
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("kg_assertions requires kg_schema", result.stdout + result.stderr)

    def test_assertion_predicate_must_be_declared_in_schema(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_assertions"][0]["predicate"] = "unknown_predicate"
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not declared in kg_schema.predicates", result.stdout + result.stderr)

    def test_clean_kg_eligible_requires_accepted_review_decision(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            payload["kg_review_history"][0]["decision"] = "rejected"
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("requires accepted reviewer decision", result.stdout + result.stderr)

    def test_clean_kg_eligible_requires_review_history_trace(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            payload["kg_review_history"] = []
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("requires review history", result.stdout + result.stderr)

    def test_review_history_unknown_triple_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_review_history"][0]["affected_triples"] = ["kg_t_unknown"]
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("references unknown triple_id", result.stdout + result.stderr)

    def test_clean_kg_eligible_requires_all_export_pointers(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            del payload["kg_exports"]["graphml"]
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("requires kg_exports.graphml", result.stdout + result.stderr)

    def test_clean_kg_eligible_rejects_duplicate_export_paths(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            payload["kg_exports"]["ttl"] = payload["kg_exports"]["jsonld"]
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unique export paths", result.stdout + result.stderr)

    def test_clean_kg_eligible_rejects_wrong_export_suffix(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            payload["kg_exports"]["evidence_index"] = "exports/kg_evidence.csv"
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("kg_exports.evidence_index must end with", result.stdout + result.stderr)

    def test_clean_kg_eligible_rejects_absolute_export_path(self) -> None:
        with TemporaryDirectory() as tmp:
            payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            payload["kg_exports"]["clean_kg_eligible"] = True
            payload["kg_exports"]["kg_review_report"] = "/tmp/kg_review_report.md"
            p = Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            result = _run(p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("should be a relative export pointer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
