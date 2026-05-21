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
    review_history = payload.get("kg_review_history", [])
    kg_exports = payload.get("kg_exports") or {}
    kg_schema = payload.get("kg_schema") or {}
    kg_scope = payload.get("kg_scope")
    hitl_gate = kg_schema.get("hitl_gate") or {}
    schema_predicates = set(kg_schema.get("predicates") or [])

    triple_ids = [a.get("triple_id") for a in assertions if isinstance(a, dict)]
    if len(triple_ids) != len(set(triple_ids)):
        errors.append("duplicate kg_assertions[].triple_id values detected")
    known_triple_ids = {t for t in triple_ids if t}

    reviewed_triples: set[str] = set()
    accepted_reviewed_triples: set[str] = set()
    for review in review_history:
        decision = review.get("decision")
        for triple_id in review.get("affected_triples") or []:
            reviewed_triples.add(triple_id)
            if decision == "accepted":
                accepted_reviewed_triples.add(triple_id)
            if triple_id not in known_triple_ids:
                errors.append(
                    f"kg_review_history references unknown triple_id '{triple_id}'"
                )

    for assertion in assertions:
        status = assertion.get("review_status")
        decision = assertion.get("human_decision")
        triple_id = assertion.get("triple_id")
        predicate = assertion.get("predicate")
        if status in {"human_reviewed", "accepted"} and not decision:
            errors.append(f"assertion {triple_id} requires human_decision for status={status}")
        if status == "accepted" and decision and decision != "accept":
            errors.append(f"assertion {triple_id} accepted status requires human_decision=accept")
        if status in {"candidate", "evidence_supported"} and decision == "accept":
            errors.append(
                f"assertion {triple_id} cannot be marked human_decision=accept before human_reviewed/accepted"
            )
        if schema_predicates and predicate not in schema_predicates:
            errors.append(
                f"assertion {triple_id} predicate '{predicate}' is not declared in kg_schema.predicates"
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
        for assertion in assertions:
            triple_id = assertion.get("triple_id")
            status = assertion.get("review_status")
            if status in {"accepted", "human_reviewed", "rejected", "superseded"}:
                if triple_id not in reviewed_triples:
                    errors.append(
                        f"kg_exports.clean_kg_eligible=true requires review history for assertion {triple_id} status={status}"
                    )
            if status == "accepted" and triple_id not in accepted_reviewed_triples:
                errors.append(
                    f"kg_exports.clean_kg_eligible=true requires accepted reviewer decision for assertion {triple_id}"
                )

    if payload.get("kg_schema"):
        if hitl_gate.get("user_validated") is not True:
            errors.append("kg_schema.hitl_gate.user_validated must be true before KG extraction")

        if hitl_gate.get("user_validated") is True:
            if not hitl_gate.get("validated_by"):
                errors.append(
                    "kg_schema.hitl_gate.validated_by is required when user_validated=true"
                )
            if not hitl_gate.get("validated_at"):
                errors.append(
                    "kg_schema.hitl_gate.validated_at is required when user_validated=true"
                )

        if hitl_gate.get("force_ontology_alignment") is True:
            ontology_mappings = kg_schema.get("external_ontology_mappings") or []
            alignment_targets = kg_schema.get("ontology_alignment_targets") or []
            if not ontology_mappings:
                errors.append(
                    "kg_schema.hitl_gate.force_ontology_alignment=true requires external_ontology_mappings"
                )
            if not alignment_targets:
                errors.append(
                    "kg_schema.hitl_gate.force_ontology_alignment=true requires ontology_alignment_targets"
                )
            if not hitl_gate.get("alignment_rationale"):
                errors.append(
                    "kg_schema.hitl_gate.force_ontology_alignment=true requires alignment_rationale"
                )

    if assertions:
        if not kg_scope:
            errors.append("kg_assertions requires kg_scope (KG-1 gate) before extraction")
        if not kg_schema:
            errors.append("kg_assertions requires kg_schema (KG-2 gate) before extraction")

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
