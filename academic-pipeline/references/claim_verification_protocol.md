# Claim Verification Protocol (Phase E)

## Purpose
Verifies that quantitative and factual claims in the paper are accurately supported by their cited sources. Phase A-D verify that references exist and are original; Phase E verifies that claims derived from those references are truthful.

## Scope
- All numerical claims (percentages, counts, effect sizes, p-values)
- All categorical assertions ("X is the largest...", "Y was the first to...")
- All trend claims ("increasing", "declining", "stable")
- All causal claims ("X causes Y", "X leads to Y")

## E1: Claim Extraction
- Scan the paper for all quantitative/factual claims
- For each claim, record: claim text, cited source(s), paper section, page/line
- Expected output: Claim Registry table

## E2: Source Tracing
- For each claim, locate the specific passage in the cited source that supports it
- Use WebSearch + DOI lookup to find the original source
- If source is behind paywall, note as UNVERIFIABLE_ACCESS

## E3: Cross-Referencing
- Compare claim text vs source text
- Check: exact numbers, date ranges, population descriptions, methodology descriptions
- Flag any discrepancies

## Verdict Taxonomy

| Verdict | Definition | Severity | Example |
|---------|-----------|----------|---------|
| VERIFIED | Claim matches source exactly or within rounding tolerance | None | Paper: "15.2%"; Source: "15.2%" |
| MINOR_DISTORTION | Claim paraphrases source but meaning is preserved | MINOR | Paper: "about 15%"; Source: "15.2%" |
| MAJOR_DISTORTION | Claim oversimplifies, exaggerates, or misrepresents source | SERIOUS | Paper: "declined sharply"; Source: "declined by 2.1%" |
| UNVERIFIABLE | Source doesn't contain the claimed information | SERIOUS | Paper cites Smith (2020) for a claim, but Smith (2020) doesn't discuss this topic |
| UNVERIFIABLE_ACCESS | Source exists but full text not accessible for verification | MEDIUM | Paywalled journal article |

## Sampling Strategy
- Mode 1 (pre-review): 30% random sample of claims (minimum 10 claims)
- Mode 2 (final-check): 100% of claims

## Output Contract

Primary output is machine-readable JSON conforming to:

- `shared/contracts/pipeline/claim_verification_report.schema.json`

Markdown remains required as a human-readable view, but JSON is the source of truth.

### JSON (authoritative)

Required top-level fields:

- `schema_version` (`1.0.0`)
- `report_id`
- `article_id`
- `run_id`
- `mode` (`pre-review` / `final-check`)
- `generated_at`
- `summary` (`total_claims_checked`, `verdict_counts`, `overall_verdict`)
- `claims[]`

Each `claims[]` row must include:

- stable identifiers: `claim_id` and `claim_registry_row`
- `claim_text`, `section`, `source_anchor`, `cited_source_ids`
- `verdict`, `severity`, `confidence`, `rationale`
- `kg_review_update` (`kg_item_id`, `old_status`, `new_status`, optional notes)

Optional `markdown_view` may carry the rendered markdown directly.

### Markdown (human view)

The markdown view must be derivable from the JSON rows:

#### Claim Verification Report
| # | Claim | Source | Section | Verdict | Detail |
|---|-------|-------|---------|---------|--------|
| 1 | [claim text] | [source] | [section] | VERIFIED | Exact match |
| 2 | [claim text] | [source] | [section] | MAJOR_DISTORTION | Paper says X, source says Y |

#### Summary
- Total claims checked: [N]
- VERIFIED: [N]
- MINOR_DISTORTION: [N]
- MAJOR_DISTORTION: [N] (must be 0 for PASS)
- UNVERIFIABLE: [N] (must be 0 for PASS)
- UNVERIFIABLE_ACCESS: [N] (noted but does not block PASS)

## KG Synchronization

When the pipeline provides `{article_id}.kg_candidates.json`, Phase E must update or emit a KG Review Update according to `references/kg_handoff_protocol.md`.

Each verified claim row must include a stable KG `Claim` item ID (`claim_id` / `kg_item_id`) and a stable Claim Registry row number (`claim_registry_row`). Use these identifiers to update matching KG items deterministically; do not rely on claim text matching alone.

Map Claim Verification verdicts to KG `review_status` as follows:

| Verdict | KG `review_status` | Action |
|---------|--------------------|--------|
| VERIFIED | accepted | Keep accepted if the claim span is unchanged; update reviewer metadata if reviewed |
| MINOR_DISTORTION | needs_revision | Record the correction needed in `reviewer_notes` |
| MAJOR_DISTORTION | rejected or needs_revision | Reject if the claim should be removed; otherwise require manuscript revision |
| UNVERIFIABLE | rejected | Record unsupported source details in `reviewer_notes` |
| UNVERIFIABLE_ACCESS | in_review or needs_revision | Keep in review if access is pending; require revision if an accessible source is needed |

When KG Stage-3 lifecycle is enabled, claim rows may transition through `candidate` / `evidence_supported` / `human_reviewed` before terminal `accepted` or `rejected`.

The KG Review Update must list changed item IDs, old/new `review_status`, and the Claim Verification row or stable claim ID that justified the update.

## Pass/Fail Criteria
- PASS: Zero MAJOR_DISTORTION + Zero UNVERIFIABLE
- FAIL: Any MAJOR_DISTORTION or UNVERIFIABLE
- PASS_WITH_NOTES: Only MINOR_DISTORTION and/or UNVERIFIABLE_ACCESS
