#!/usr/bin/env python3
"""Build a KG-ready export package (article + validated KG/claim artifacts + manifest)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.check_claim_verification_report import validate as validate_claim_report
    from scripts.check_kg_audit_report import validate as validate_kg_audit_report
    from scripts.check_kg_handoff import validate as validate_kg_handoff
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from check_claim_verification_report import validate as validate_claim_report
    from check_kg_audit_report import validate as validate_kg_audit_report
    from check_kg_handoff import validate as validate_kg_handoff


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_optional(path: Path | None, output_dir: Path) -> str | None:
    if not path:
        return None
    out = output_dir / path.name
    shutil.copy2(path, out)
    return out.name


def _clean_kg_eligible(kg_payload: dict) -> bool:
    resolved_statuses = {"accepted", "human_reviewed", "rejected", "superseded"}
    unresolved_statuses = {"pending", "in_review", "needs_revision", "candidate", "evidence_supported"}
    for item in kg_payload.get("items", []):
        status = item.get("review_status")
        if status in unresolved_statuses:
            return False
        if status not in resolved_statuses:
            return False
    return True


def build_package(
    article_path: Path,
    kg_handoff_path: Path,
    claim_report_path: Path,
    output_dir: Path,
    claim_markdown_view_path: Path | None = None,
    kg_audit_report_path: Path | None = None,
    kg_jsonld_path: Path | None = None,
    kg_ttl_path: Path | None = None,
    kg_graphml_path: Path | None = None,
    kg_nodes_csv_path: Path | None = None,
    kg_edges_csv_path: Path | None = None,
    kg_evidence_jsonl_path: Path | None = None,
    kg_review_report_path: Path | None = None,
    kg_schema_yaml_path: Path | None = None,
    kg_shacl_shapes_path: Path | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        kg_payload = _load_json(kg_handoff_path)
    except Exception as exc:  # noqa: BLE001
        return False, [f"failed to load KG handoff JSON: {exc}"]
    try:
        claim_payload = _load_json(claim_report_path)
    except Exception as exc:  # noqa: BLE001
        return False, [f"failed to load claim verification JSON: {exc}"]

    kg_audit_payload = None
    if kg_audit_report_path:
        try:
            kg_audit_payload = _load_json(kg_audit_report_path)
        except Exception as exc:  # noqa: BLE001
            return False, [f"failed to load KG audit report JSON: {exc}"]

    errors.extend(validate_kg_handoff(kg_payload))
    errors.extend(validate_claim_report(claim_payload))
    if kg_audit_payload is not None:
        errors.extend(validate_kg_audit_report(kg_audit_payload))
    if errors:
        return False, errors

    if kg_audit_payload and kg_audit_payload.get("summary", {}).get("unresolved_high_warn_count", 0) > 0:
        return False, [
            "clean KG export blocked: unresolved HIGH-WARN-KG findings present in KG audit report"
        ]

    output_dir.mkdir(parents=True, exist_ok=True)
    article_out = output_dir / article_path.name
    kg_out = output_dir / kg_handoff_path.name
    claim_out = output_dir / claim_report_path.name
    shutil.copy2(article_path, article_out)
    shutil.copy2(kg_handoff_path, kg_out)
    shutil.copy2(claim_report_path, claim_out)

    markdown_name = _copy_optional(claim_markdown_view_path, output_dir)
    kg_audit_name = _copy_optional(kg_audit_report_path, output_dir)
    kg_jsonld_name = _copy_optional(kg_jsonld_path, output_dir)
    kg_ttl_name = _copy_optional(kg_ttl_path, output_dir)
    kg_graphml_name = _copy_optional(kg_graphml_path, output_dir)
    kg_nodes_csv_name = _copy_optional(kg_nodes_csv_path, output_dir)
    kg_edges_csv_name = _copy_optional(kg_edges_csv_path, output_dir)
    kg_evidence_jsonl_name = _copy_optional(kg_evidence_jsonl_path, output_dir)
    kg_review_report_name = _copy_optional(kg_review_report_path, output_dir)
    kg_schema_yaml_name = _copy_optional(kg_schema_yaml_path, output_dir)
    kg_shacl_shapes_name = _copy_optional(kg_shacl_shapes_path, output_dir)
    clean_kg_eligible = _clean_kg_eligible(kg_payload)

    manifest = {
        "schema_version": "1.0.0",
        "package_type": "kg_ready_export",
        "generated_at": _utc_now_iso(),
        "article_id": kg_payload.get("article_id"),
        "run_id": kg_payload.get("run_id"),
        "contracts": {
            "kg_handoff_schema_version": kg_payload.get("schema_version"),
            "claim_verification_schema_version": claim_payload.get("schema_version"),
            "kg_audit_schema_version": (
                kg_audit_payload.get("schema_version") if kg_audit_payload else None
            ),
        },
        "files": {
            "article": article_out.name,
            "kg_handoff_json": kg_out.name,
            "claim_verification_json": claim_out.name,
            "claim_verification_markdown": markdown_name,
            "kg_audit_report_json": kg_audit_name,
            "kg_jsonld": kg_jsonld_name,
            "kg_ttl": kg_ttl_name,
            "kg_graphml": kg_graphml_name,
            "kg_nodes_csv": kg_nodes_csv_name,
            "kg_edges_csv": kg_edges_csv_name,
            "kg_evidence_jsonl": kg_evidence_jsonl_name,
            "kg_review_report_md": kg_review_report_name,
            "kg_schema_yaml": kg_schema_yaml_name,
            "kg_shacl_shapes_ttl": kg_shacl_shapes_name,
        },
        "validation": {
            "kg_handoff": "pass",
            "claim_verification": "pass",
            "kg_audit": "pass" if kg_audit_payload else "not_provided",
            "clean_kg_eligible": clean_kg_eligible,
            "overall": "pass",
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return True, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", type=Path, required=True, help="Path to article markdown")
    parser.add_argument("--kg-handoff", type=Path, required=True, help="Path to kg_candidates.json")
    parser.add_argument(
        "--claim-verification",
        type=Path,
        required=True,
        help="Path to claim verification JSON contract",
    )
    parser.add_argument(
        "--claim-verification-markdown",
        type=Path,
        help="Optional markdown view of claim verification report",
    )
    parser.add_argument("--kg-audit-report", type=Path, help="Optional KG audit report JSON contract")
    parser.add_argument("--kg-jsonld", type=Path, help="Optional clean KG JSON-LD export file")
    parser.add_argument("--kg-ttl", type=Path, help="Optional clean KG Turtle export file")
    parser.add_argument("--kg-graphml", type=Path, help="Optional clean KG GraphML export file")
    parser.add_argument("--kg-nodes-csv", type=Path, help="Optional clean KG nodes CSV export file")
    parser.add_argument("--kg-edges-csv", type=Path, help="Optional clean KG edges CSV export file")
    parser.add_argument(
        "--kg-evidence-jsonl",
        type=Path,
        help="Optional KG evidence index JSONL export file",
    )
    parser.add_argument(
        "--kg-review-report",
        type=Path,
        help="Optional KG review report markdown file",
    )
    parser.add_argument("--kg-schema-yaml", type=Path, help="Optional KG schema YAML file")
    parser.add_argument(
        "--kg-shacl-shapes",
        type=Path,
        help="Optional KG SHACL shapes turtle file",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Output package directory")
    args = parser.parse_args()

    ok, errors = build_package(
        article_path=args.article,
        kg_handoff_path=args.kg_handoff,
        claim_report_path=args.claim_verification,
        output_dir=args.output_dir,
        claim_markdown_view_path=args.claim_verification_markdown,
        kg_audit_report_path=args.kg_audit_report,
        kg_jsonld_path=args.kg_jsonld,
        kg_ttl_path=args.kg_ttl,
        kg_graphml_path=args.kg_graphml,
        kg_nodes_csv_path=args.kg_nodes_csv,
        kg_edges_csv_path=args.kg_edges_csv,
        kg_evidence_jsonl_path=args.kg_evidence_jsonl,
        kg_review_report_path=args.kg_review_report,
        kg_schema_yaml_path=args.kg_schema_yaml,
        kg_shacl_shapes_path=args.kg_shacl_shapes,
    )
    if not ok:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print(f"OK: KG-ready export package built at {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
