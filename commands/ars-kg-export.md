---
description: ARS utility command — build a KG-ready export package (article + validated handoff contracts + manifest)
model: sonnet
---

Build a KG-ready export package by invoking:

`python scripts/build_kg_ready_export.py --article <article.md> --kg-handoff <{article_id}.kg_candidates.json> --claim-verification <claim_verification.json> [--claim-verification-markdown <claim_verification.md>] --output-dir <out_dir>`

Validation is mandatory before packaging:
- KG handoff: `scripts/check_kg_handoff.py`
- Claim verification report: `scripts/check_claim_verification_report.py`

If validation fails, stop and return the list of missing/invalid fields.
