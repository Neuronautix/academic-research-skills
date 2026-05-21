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

    def test_build_package_fails_with_unresolved_high_warn_kg_audit(self) -> None:
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
                "--kg-audit-report",
                str(FIXTURE_DIR / "good_kg_audit_report.json"),
                "--output-dir",
                str(out),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("clean KG export blocked", result.stdout + result.stderr)

    def test_build_package_with_kg_exports_and_resolved_audit_success(self) -> None:
        with TemporaryDirectory() as tmp:
            resolved_audit = Path(tmp) / "resolved_kg_audit.json"
            resolved_audit.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "audit_id": "kg-audit-002",
                        "article_id": "article-123",
                        "run_id": "run-001",
                        "generated_at": "2026-05-19T18:20:00Z",
                        "summary": {
                            "total_findings": 1,
                            "unresolved_high_warn_count": 0,
                            "blocking": False
                        },
                        "findings": [
                            {
                                "finding_id": "kgf-001",
                                "code": "HIGH-WARN-KG-UNSUPPORTED-TRIPLE",
                                "severity": "HIGH-WARN",
                                "status": "resolved",
                                "triple_id": "kg_t_000124",
                                "rationale": "Updated evidence anchor and re-audited."
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            kg_jsonld = Path(tmp) / "kg.jsonld"
            kg_ttl = Path(tmp) / "kg.ttl"
            kg_graphml = Path(tmp) / "kg.graphml"
            kg_nodes = Path(tmp) / "kg_nodes.csv"
            kg_edges = Path(tmp) / "kg_edges.csv"
            kg_evidence = Path(tmp) / "kg_evidence.jsonl"
            kg_review = Path(tmp) / "kg_review_report.md"
            kg_schema = Path(tmp) / "kg_schema.yaml"
            kg_shacl = Path(tmp) / "kg_shacl_shapes.ttl"
            for path in (
                kg_jsonld,
                kg_ttl,
                kg_graphml,
                kg_nodes,
                kg_edges,
                kg_evidence,
                kg_review,
                kg_schema,
                kg_shacl,
            ):
                path.write_text("x", encoding="utf-8")

            out = Path(tmp) / "pkg"
            result = run_script(
                SCRIPT,
                "--article",
                str(FIXTURE_DIR / "article.md"),
                "--kg-handoff",
                str(FIXTURE_DIR / "good_kg_handoff.json"),
                "--claim-verification",
                str(FIXTURE_DIR / "good_claim_verification_report.json"),
                "--kg-audit-report",
                str(resolved_audit),
                "--kg-jsonld",
                str(kg_jsonld),
                "--kg-ttl",
                str(kg_ttl),
                "--kg-graphml",
                str(kg_graphml),
                "--kg-nodes-csv",
                str(kg_nodes),
                "--kg-edges-csv",
                str(kg_edges),
                "--kg-evidence-jsonl",
                str(kg_evidence),
                "--kg-review-report",
                str(kg_review),
                "--kg-schema-yaml",
                str(kg_schema),
                "--kg-shacl-shapes",
                str(kg_shacl),
                "--output-dir",
                str(out),
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["validation"]["kg_audit"], "pass")
            self.assertIn("kg_jsonld", manifest["files"])


if __name__ == "__main__":
    unittest.main()
