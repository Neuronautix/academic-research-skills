#!/usr/bin/env python3
"""Validate ARS KG handoff JSON (schema + semantic checks)."""
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
    / "ars_handoff.schema.json"
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
    items = payload.get("items", [])
    links = payload.get("links", [])
    ids = [i.get("id") for i in items if isinstance(i, dict)]
    id_set = set(ids)

    if len(ids) != len(id_set):
        seen: set[str] = set()
        dup: set[str] = set()
        for item_id in ids:
            if item_id in seen:
                dup.add(item_id)
            seen.add(item_id)
        errors.append(f"duplicate item ids: {sorted(dup)}")

    link_ids = [l.get("id") for l in links if isinstance(l, dict)]
    if len(link_ids) != len(set(link_ids)):
        errors.append("duplicate link ids detected")

    for link in links:
        from_id = link.get("from_id")
        to_id = link.get("to_id")
        if from_id not in id_set:
            errors.append(f"link {link.get('id')} from_id does not exist: {from_id}")
        if to_id not in id_set:
            errors.append(f"link {link.get('id')} to_id does not exist: {to_id}")

    claim_items = [i for i in items if i.get("type") == "Claim"]
    evidence_items = [i for i in items if i.get("type") == "Evidence"]

    for claim in claim_items:
        if claim.get("review_status") == "accepted":
            evidence_ids = claim.get("related_evidence_ids") or []
            notes = (claim.get("reviewer_notes") or "").strip()
            if not evidence_ids and not notes:
                errors.append(
                    f"accepted claim {claim.get('id')} missing related_evidence_ids and reviewer_notes exception"
                )

        for evidence_id in claim.get("related_evidence_ids", []):
            if evidence_id not in id_set:
                errors.append(
                    f"claim {claim.get('id')} references missing evidence id {evidence_id}"
                )
        for concept_id in claim.get("related_concept_ids", []):
            if concept_id not in id_set:
                errors.append(
                    f"claim {claim.get('id')} references missing concept id {concept_id}"
                )

    referenced_evidence_ids: set[str] = set()
    for claim in claim_items:
        for evidence_id in claim.get("related_evidence_ids", []):
            referenced_evidence_ids.add(evidence_id)

    for evidence in evidence_items:
        if evidence.get("id") not in referenced_evidence_ids:
            notes = (evidence.get("reviewer_notes") or "").strip()
            if not notes:
                errors.append(
                    f"evidence item {evidence.get('id')} is orphaned (no claim reference and no reviewer_notes)"
                )

    return errors


def validate(payload: dict) -> list[str]:
    return [*schema_errors(payload), *semantic_errors(payload)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path, help="Path to {article_id}.kg_candidates.json")
    args = parser.parse_args()

    try:
        payload = json.loads(args.handoff.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to load {args.handoff}: {exc}")
        return 1

    errors = validate(payload)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(
            f"\n{len(errors)} violation(s). See {SCHEMA_PATH} and kg_handoff_protocol.md.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {args.handoff} is a valid KG handoff package (schema + semantics)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
