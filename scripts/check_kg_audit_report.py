#!/usr/bin/env python3
"""Validate ARS KG audit report JSON (schema + semantic checks)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "shared"
    / "contracts"
    / "kg"
    / "kg_audit_report.schema.json"
)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def schema_errors(payload: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        load_schema(),
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    return [f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(payload)]


def semantic_errors(payload: dict) -> list[str]:
    errors: list[str] = []
    findings = payload.get("findings", [])
    summary = payload.get("summary", {})

    finding_ids = [f.get("finding_id") for f in findings if isinstance(f, dict)]
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("duplicate finding_id values detected")

    unresolved_high_warn_count = 0
    for finding in findings:
        if finding.get("severity") != "HIGH-WARN":
            continue
        if finding.get("status") == "open":
            unresolved_high_warn_count += 1

    if summary.get("total_findings") != len(findings):
        errors.append("summary.total_findings does not match number of findings")

    if summary.get("unresolved_high_warn_count") != unresolved_high_warn_count:
        errors.append(
            "summary.unresolved_high_warn_count does not match computed unresolved HIGH-WARN findings"
        )

    expected_blocking = unresolved_high_warn_count > 0
    if summary.get("blocking") != expected_blocking:
        errors.append(
            f"summary.blocking must be {expected_blocking} when unresolved_high_warn_count={unresolved_high_warn_count}"
        )

    return errors


def validate(payload: dict) -> list[str]:
    return [*schema_errors(payload), *semantic_errors(payload)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to KG audit report JSON")
    args = parser.parse_args()

    try:
        payload = json.loads(args.report.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to load {args.report}: {exc}")
        return 1

    errors = validate(payload)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(
            f"\n{len(errors)} violation(s). See {SCHEMA_PATH}.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {args.report} is a valid KG audit report (schema + semantics)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
