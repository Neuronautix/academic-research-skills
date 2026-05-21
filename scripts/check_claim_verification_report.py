#!/usr/bin/env python3
"""Validate ARS claim verification report JSON (schema + semantic checks)."""
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
    / "pipeline"
    / "claim_verification_report.schema.json"
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
    claims = payload.get("claims", [])
    summary = payload.get("summary", {})
    counts = summary.get("verdict_counts", {})

    claim_ids = [c.get("claim_id") for c in claims if isinstance(c, dict)]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("duplicate claim_id values detected")

    rows = [c.get("claim_registry_row") for c in claims if isinstance(c, dict)]
    if len(rows) != len(set(rows)):
        errors.append("duplicate claim_registry_row values detected")

    computed: dict[str, int] = {
        "VERIFIED": 0,
        "MINOR_DISTORTION": 0,
        "MAJOR_DISTORTION": 0,
        "UNVERIFIABLE": 0,
        "UNVERIFIABLE_ACCESS": 0,
    }
    for claim in claims:
        verdict = claim.get("verdict")
        if verdict in computed:
            computed[verdict] += 1
        kg_item_id = claim.get("kg_review_update", {}).get("kg_item_id")
        if kg_item_id and kg_item_id != claim.get("claim_id"):
            errors.append(
                f"kg_review_update.kg_item_id must equal claim_id for deterministic updates ({claim.get('claim_id')})"
            )

    if summary.get("total_claims_checked") != len(claims):
        errors.append("summary.total_claims_checked does not match number of claim rows")

    for verdict, count in computed.items():
        if counts.get(verdict) != count:
            errors.append(
                f"summary.verdict_counts.{verdict}={counts.get(verdict)} does not match computed count {count}"
            )

    return errors


def validate(payload: dict) -> list[str]:
    return [*schema_errors(payload), *semantic_errors(payload)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to claim verification report JSON")
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
            f"\n{len(errors)} violation(s). See {SCHEMA_PATH} and claim_verification_protocol.md.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {args.report} is a valid claim verification contract (schema + semantics)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
