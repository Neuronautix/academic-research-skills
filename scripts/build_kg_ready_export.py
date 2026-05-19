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
    from scripts.check_kg_handoff import validate as validate_kg_handoff
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from check_claim_verification_report import validate as validate_claim_report
    from check_kg_handoff import validate as validate_kg_handoff


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_package(
    article_path: Path,
    kg_handoff_path: Path,
    claim_report_path: Path,
    output_dir: Path,
    claim_markdown_view_path: Path | None = None,
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

    errors.extend(validate_kg_handoff(kg_payload))
    errors.extend(validate_claim_report(claim_payload))
    if errors:
        return False, errors

    output_dir.mkdir(parents=True, exist_ok=True)
    article_out = output_dir / article_path.name
    kg_out = output_dir / kg_handoff_path.name
    claim_out = output_dir / claim_report_path.name
    shutil.copy2(article_path, article_out)
    shutil.copy2(kg_handoff_path, kg_out)
    shutil.copy2(claim_report_path, claim_out)

    markdown_name = None
    if claim_markdown_view_path:
        markdown_out = output_dir / claim_markdown_view_path.name
        shutil.copy2(claim_markdown_view_path, markdown_out)
        markdown_name = markdown_out.name

    manifest = {
        "schema_version": "1.0.0",
        "package_type": "kg_ready_export",
        "generated_at": _utc_now_iso(),
        "article_id": kg_payload.get("article_id"),
        "run_id": kg_payload.get("run_id"),
        "contracts": {
            "kg_handoff_schema_version": kg_payload.get("schema_version"),
            "claim_verification_schema_version": claim_payload.get("schema_version"),
        },
        "files": {
            "article": article_out.name,
            "kg_handoff_json": kg_out.name,
            "claim_verification_json": claim_out.name,
            "claim_verification_markdown": markdown_name,
        },
        "validation": {
            "kg_handoff": "pass",
            "claim_verification": "pass",
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
    parser.add_argument("--output-dir", type=Path, required=True, help="Output package directory")
    args = parser.parse_args()

    ok, errors = build_package(
        article_path=args.article,
        kg_handoff_path=args.kg_handoff,
        claim_report_path=args.claim_verification,
        output_dir=args.output_dir,
        claim_markdown_view_path=args.claim_verification_markdown,
    )
    if not ok:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print(f"OK: KG-ready export package built at {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
