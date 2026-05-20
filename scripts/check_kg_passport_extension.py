#!/usr/bin/env python3
"""Validate Material Passport KG extension fields (schema + semantic checks)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema
import yaml

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "shared"
    / "contracts"
    / "passport"
    / "kg_passport_extension.schema.json"
)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_payload(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".json"}:
        return json.loads(text)
    loaded = yaml.safe_load(text)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("passport payload must be a mapping/object")
    return loaded


def schema_errors(payload: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        load_schema(),
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    return [f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(payload)]


def semantic_errors(payload: dict) -> list[str]:
    errors: list[str] = []
    assertions = payload.get("kg_assertions", [])
    kg_exports = payload.get("kg_exports") or {}

    triple_ids = [a.get("triple_id") for a in assertions if isinstance(a, dict)]
    if len(triple_ids) != len(set(triple_ids)):
        errors.append("duplicate kg_assertions[].triple_id values detected")

    for assertion in assertions:
        status = assertion.get("review_status")
        decision = assertion.get("human_decision")
        triple_id = assertion.get("triple_id")
        if status in {"human_reviewed", "accepted"} and not decision:
            errors.append(f"assertion {triple_id} requires human_decision for status={status}")
        if status == "accepted" and decision and decision != "accept":
            errors.append(f"assertion {triple_id} accepted status requires human_decision=accept")
        if status in {"candidate", "evidence_supported"} and decision == "accept":
            errors.append(
                f"assertion {triple_id} cannot be marked human_decision=accept before human_reviewed/accepted"
            )

    if kg_exports.get("clean_kg_eligible") is True:
        required = ("kg_scope", "kg_schema", "kg_assertions", "kg_review_history")
        for field in required:
            if field not in payload:
                errors.append(f"kg_exports.clean_kg_eligible=true requires field {field}")
        unresolved = [
            a.get("triple_id")
            for a in assertions
            if a.get("review_status") in {"candidate", "evidence_supported"}
        ]
        if unresolved:
            errors.append(
                f"kg_exports.clean_kg_eligible=true but unresolved assertion statuses exist: {sorted(unresolved)}"
            )

    return errors


def validate(payload: dict) -> list[str]:
    return [*schema_errors(payload), *semantic_errors(payload)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("passport", type=Path, help="Path to Material Passport (YAML/JSON)")
    args = parser.parse_args()

    try:
        payload = _load_payload(args.passport)
    except (FileNotFoundError, json.JSONDecodeError, yaml.YAMLError, ValueError) as exc:
        print(f"ERROR: failed to load {args.passport}: {exc}")
        return 1

    errors = validate(payload)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\n{len(errors)} violation(s). See {SCHEMA_PATH}.", file=sys.stderr)
        return 1

    print(f"OK: {args.passport} is valid for KG passport extension fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
