#!/usr/bin/env python3
"""Validate ARS KG handoff JSON (schema + semantic checks)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
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


def _parse_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


ALLOWED_TRANSITIONS = {
    "pending": {"candidate", "rejected"},
    "candidate": {"evidence_supported", "rejected", "needs_revision", "superseded"},
    "in_review": {"accepted", "needs_revision", "rejected", "human_reviewed"},
    "evidence_supported": {"human_reviewed", "rejected", "needs_revision", "superseded"},
    "human_reviewed": {"accepted", "rejected", "superseded", "needs_revision"},
    "accepted": {"needs_revision", "rejected", "superseded"},
    "needs_revision": {"candidate", "evidence_supported", "human_reviewed", "in_review", "rejected"},
    "rejected": {"superseded"},
    "superseded": set(),
}

CLAIM_TYPE_MODALITIES = {
    "finding": {"measured", "observed", "reported", "inferred"},
    "hypothesis": {"hypothesized", "speculative", "inferred"},
    "limitation": {"reported", "inferred"},
    "method": {"measured", "reported", "observed"},
    "methodological": {"measured", "reported", "observed", "inferred"},
    "background": {"reported", "inferred"},
}


def semantic_errors(payload: dict) -> list[str]:
    errors: list[str] = []
    items = payload.get("items", [])
    links = payload.get("links", [])
    ids = [i.get("id") for i in items if isinstance(i, dict)]
    id_set = set(ids)
    item_by_id = {item.get("id"): item for item in items if isinstance(item, dict)}

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
    concept_items = [i for i in items if i.get("type") == "Concept"]

    for claim in claim_items:
        claim_type = claim.get("claim_type")
        modality = claim.get("modality")
        if claim_type in CLAIM_TYPE_MODALITIES and modality not in CLAIM_TYPE_MODALITIES[claim_type]:
            errors.append(
                f"HIGH-WARN-KG-MODALITY-MISMATCH: claim {claim.get('id')} claim_type={claim_type} incompatible with modality={modality}"
            )

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

    for item in items:
        status_history = item.get("status_history")
        if not status_history:
            continue
        current_status = item.get("review_status")
        if status_history[-1].get("status") != current_status:
            errors.append(
                f"item {item.get('id')} review_status={current_status} must match last status_history entry"
            )

        prior_status = None
        prior_decision_at = None
        for event in status_history:
            status = event.get("status")
            if prior_status is not None and status not in ALLOWED_TRANSITIONS.get(prior_status, set()):
                errors.append(
                    f"item {item.get('id')} has invalid status transition {prior_status} -> {status}"
                )
            decision_at = event.get("decision_at")
            if decision_at:
                try:
                    decision_at_parsed = _parse_iso8601(decision_at)
                except ValueError:
                    errors.append(
                        f"item {item.get('id')} status_history has invalid decision_at timestamp: {decision_at}"
                    )
                    decision_at_parsed = None
                if (
                    decision_at_parsed is not None
                    and prior_decision_at is not None
                    and decision_at_parsed <= prior_decision_at
                ):
                    errors.append(
                        f"item {item.get('id')} status_history decision_at timestamps must be strictly increasing"
                    )
                if decision_at_parsed is not None:
                    prior_decision_at = decision_at_parsed
            prior_status = status

    canonical_conflicts: dict[str, set[str]] = {}
    for concept in concept_items:
        if concept.get("review_status") in {"rejected", "superseded"}:
            continue
        label = (concept.get("canonical_label") or "").strip().lower()
        if not label:
            continue
        iri = (concept.get("iri") or "").strip()
        iri_marker = iri if iri else "__no_iri__"
        canonical_conflicts.setdefault(label, set()).add(iri_marker)
    for label, iris in canonical_conflicts.items():
        if len(iris) > 1:
            errors.append(
                f"HIGH-WARN-KG-ENTITY-MERGE-CONFLICT unresolved for canonical_label '{label}'"
            )

    for link in links:
        relation_type = link.get("relation_type")
        polarity = link.get("polarity")
        from_item = item_by_id.get(link.get("from_id"), {})
        to_item = item_by_id.get(link.get("to_id"), {})

        if relation_type == "claim_supported_by_evidence" and polarity != "support":
            errors.append(
                f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} support relation must use polarity=support"
            )
        if relation_type == "claim_contradicted_by_evidence" and polarity != "contradiction":
            errors.append(
                f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} contradiction relation must use polarity=contradiction"
            )
        if relation_type == "supports_claim" and polarity != "support":
            errors.append(
                f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} supports_claim must use polarity=support"
            )
        if relation_type == "contradicts_claim" and polarity != "contradiction":
            errors.append(
                f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} contradicts_claim must use polarity=contradiction"
            )
        if relation_type == "reports_finding" and polarity != "support":
            errors.append(
                f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} reports_finding must use polarity=support"
            )

        if relation_type in {"claim_supported_by_evidence", "claim_contradicted_by_evidence"}:
            if from_item.get("type") != "Claim" or to_item.get("type") != "Evidence":
                errors.append(
                    f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} requires Claim -> Evidence endpoints"
                )
        if relation_type == "claim_about_concept":
            if from_item.get("type") != "Claim" or to_item.get("type") != "Concept":
                errors.append(
                    f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} requires Claim -> Concept endpoints"
                )
        if relation_type == "evidence_about_concept":
            if from_item.get("type") != "Evidence" or to_item.get("type") != "Concept":
                errors.append(
                    f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} requires Evidence -> Concept endpoints"
                )
        if relation_type in {"supports_claim", "contradicts_claim", "reports_finding"}:
            if to_item.get("type") != "Claim":
                errors.append(
                    f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} requires target Claim endpoint"
                )
            if from_item.get("type") not in {"Evidence", "Claim"}:
                errors.append(
                    f"HIGH-WARN-KG-RELATION-MISCLASSIFIED: {link.get('id')} requires Evidence/Claim source endpoint"
                )

    contradiction_clusters: dict[str, dict[str, int]] = {}
    for link in links:
        relation_type = link.get("relation_type")
        from_id = link.get("from_id")
        to_id = link.get("to_id")
        claim_id: str | None = None
        if relation_type in {"claim_supported_by_evidence", "claim_contradicted_by_evidence", "claim_about_concept"}:
            claim_id = from_id
        elif relation_type in {"supports_claim", "contradicts_claim", "reports_finding"}:
            claim_id = to_id
        if not claim_id or not str(claim_id).startswith("claim:"):
            continue
        cluster = contradiction_clusters.setdefault(claim_id, {"support": 0, "contradiction": 0})
        if link.get("polarity") == "support":
            cluster["support"] += 1
        if link.get("polarity") == "contradiction":
            cluster["contradiction"] += 1

    for claim_id, cluster in contradiction_clusters.items():
        if cluster["support"] > 0 and cluster["contradiction"] > 0:
            claim = item_by_id.get(claim_id, {})
            notes = (claim.get("reviewer_notes") or "").lower()
            if "user_arbitrated" not in notes:
                errors.append(
                    f"HIGH-WARN-KG-CONTRADICTION-UNRESOLVED: claim {claim_id} has support+contradiction links without explicit user_arbitrated decision"
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
