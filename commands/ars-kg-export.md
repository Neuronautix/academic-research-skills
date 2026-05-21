---
description: ARS utility command — build a KG-ready export package (article + validated handoff contracts + manifest)
model: sonnet
---

Build a KG-ready export package by invoking:

`python3 scripts/build_kg_ready_export.py --article <article.md> --kg-handoff <{article_id}.kg_candidates.json> --claim-verification <claim_verification.json> [--claim-verification-markdown <claim_verification.md>] [--kg-audit-report <kg_audit_report.json>] [--kg-jsonld <kg.jsonld>] [--kg-ttl <kg.ttl>] [--kg-graphml <kg.graphml>] [--kg-nodes-csv <kg_nodes.csv>] [--kg-edges-csv <kg_edges.csv>] [--kg-evidence-jsonl <kg_evidence.jsonl>] [--kg-review-report <kg_review_report.md>] [--kg-schema-yaml <kg_schema.yaml>] [--kg-shacl-shapes <kg_shacl_shapes.ttl>] --output-dir <out_dir>`

Validation is mandatory before packaging:
- KG handoff: `scripts/check_kg_handoff.py`
- Claim verification report: `scripts/check_claim_verification_report.py`
- KG audit report, when provided: `scripts/check_kg_audit_report.py`

If validation fails, or if the KG audit report contains unresolved `HIGH-WARN-KG` findings, stop and return the blocking errors.
