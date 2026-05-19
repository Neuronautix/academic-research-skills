# KG Handoff Protocol

## Purpose

Synchronize the manuscript artifact (`article.md`) with a structured KG candidate artifact (`{article_id}.kg_candidates.json`) during the ARS writing, integrity, revision, and finalization stages. The KG handoff is a first-class pipeline deliverable, not an end-of-run post-processing step.

The handoff file must conform to `kg_layer/schemas/ars_handoff_schema.json` and should be updated whenever article claims, concepts, evidence, or review decisions change.

## Required Filename

Use one KG handoff file per article:

```text
{article_id}.kg_candidates.json
```

`article_id` should match the parent `article_id` field when available. If no explicit article ID exists, derive a stable slug from the source document stem and keep it unchanged for the run.

## KG Object Types

| Type | Use |
|---|---|
| `Paper` | Article-level metadata and source-document identity |
| `Concept` | Key theoretical, empirical, methodological, or domain concepts used by the article |
| `Claim` | Factual, quantitative, interpretive, causal, or trend claims made in the article |
| `Evidence` | Source-backed quotations, data points, observations, or cited findings supporting claims |

## Handoff Shape

The root object contains:

| Field | Requirement |
|---|---|
| `article_id` | Recommended; stable per article |
| `title` | Recommended; current article title |
| `run_id` | Recommended for traceability |
| `source_document` | Required; normally `article.md` or the current manuscript artifact path |
| `items` | Required; array of KG candidates |

Each item must include fields compatible with `ars_handoff_schema.json`:

| Field | Requirement |
|---|---|
| `id` | Required; stable KG candidate ID |
| `type` | Required; one of `Paper`, `Concept`, `Claim`, `Evidence` |
| `source_document` | Required; same manuscript artifact or specific source artifact |
| `source_section` | Required; section heading or local label |
| `supporting_quote_or_span` | Required; exact manuscript span supporting the item |
| `confidence` | Required; numeric value from `0.0` to `1.0` |
| `extraction_method` | Required; use `ars_hitl` for ARS-authored/reviewed candidates unless a more specific method is recorded |
| `review_status` | Required; lifecycle value below |
| `reviewer` | Optional; reviewer/agent/human identity |
| `reviewed_at` | Optional; ISO 8601 timestamp for review decisions |
| `reviewer_notes` | Optional; concise rationale, change note, or obsolete marker |
| `article_id` | Optional item-level propagation |
| `run_id` | Optional item-level propagation |
| `related_evidence_ids` | Optional for most items, required for accepted `Claim` items except explicit documented exceptions; array of `Evidence` IDs supporting the claim |
| `related_concept_ids` | Optional; array of `Concept` IDs that define or contextualize the item |
| `source_citation` | Recommended for all source-backed items and expected for accepted `Claim` items; citation, DOI, URL, report locator, or source note distinct from the manuscript span |
| `canonical_label` | Recommended for `Concept` items; stable ontology label used for deduplication and downstream entity pages |
| `aliases` | Optional for `Concept` items; alternate labels, abbreviations, spelling variants, or deliberate merge signals |
| `iri` | Optional; stable ontology IRI when one is known or assigned, using an `http` or `https` identifier |

Additional item properties are allowed by the schema when needed for local traceability, but required schema fields must remain present.

## Ontology-Aware Field Guidance

Populate ontology-aware optional fields whenever the information is available from ARS review artifacts:

- `Claim` items should link to the `Evidence` items that support them through `related_evidence_ids`. A claim can reference multiple evidence items when it combines a source quote, dataset value, and methodological note.
- `Claim`, `Evidence`, and `Paper` items should use `source_citation` for the external source or citation. Keep `supporting_quote_or_span` as the exact article or source span being represented; do not use it as a substitute for a citation.
- `Concept` items should use `canonical_label` for the preferred ontology label and `aliases` for known variants. If two concept candidates intentionally represent the same concept, make the merge explicit with shared aliases or reviewer notes.
- `related_concept_ids` should connect claims and evidence to the concepts they instantiate, define, measure, or compare.
- `iri` should be stable across runs once assigned. Prefer resolvable `https` identifiers. Do not mint a new IRI for a renamed concept if the underlying concept is unchanged.

## Semantic Quality Rules

Semantic validation is stricter than schema validation. Before finalization or publishing, the handoff should satisfy these rules:

- IDs are unique across the validated handoff set, and every `related_evidence_ids` or `related_concept_ids` value points to an existing item ID.
- No accepted `Claim` may be unsupported. Accepted claims require at least one `related_evidence_ids` entry unless `reviewer_notes` explicitly explains why the claim is accepted without linked evidence.
- Evidence should not be orphaned. Every current `Evidence` item should be referenced by at least one `Claim`, or its `reviewer_notes` should explain why it remains in the handoff.
- Accepted `Claim` items should include `source_citation` so the KG can distinguish the article's claim text from the external source that verifies it.
- Concept labels must be canonical and stable. Duplicate `canonical_label` plus `supporting_quote_or_span` pairs should be merged or marked as intentional aliases.
- IRIs must remain stable and should look like `http` or `https` ontology identifiers when present.
- `confidence` must be numeric from `0.0` to `1.0`, and `review_status` must use the controlled lifecycle values in this protocol.
- Distinguish article claims from source claims: a `Claim` represents what the article asserts, while `Evidence` and `source_citation` identify the source-backed support for that assertion. Do not encode a quoted source finding as an accepted article claim unless the article itself makes that claim.

## Stable ID Policy

IDs must remain stable across drafting, integrity review, revision, and finalization unless the underlying object is split or merged.

Recommended format:

```text
{type_lower}:{article_id}:{stable_key}
```

Examples:

- `paper:article-123:main`
- `concept:article-123:quality-assurance`
- `claim:article-123:c017`
- `evidence:article-123:e017a`

For claims, prefer a persistent claim registry ID. If none exists, use the Claim Verification Report row number only as a temporary key, then preserve that ID once assigned. When a claim is rewritten but remains semantically the same, keep the ID and update the span. When a claim is replaced by a different assertion, create a new ID and mark the prior item rejected or obsolete.

## Review Status Lifecycle

| Status | Meaning |
|---|---|
| `pending` | Candidate extracted or created but not reviewed |
| `in_review` | Candidate currently under integrity, claim, or human review |
| `accepted` | Candidate is verified and suitable for KG ingestion |
| `rejected` | Candidate should not be ingested; keep an audit note |
| `needs_revision` | Candidate may be valid but the manuscript span, citation, or support must be corrected before acceptance |

Normal lifecycle:

```text
pending -> in_review -> accepted
pending -> in_review -> needs_revision -> in_review -> accepted
pending -> in_review -> rejected
accepted -> needs_revision | rejected
```

## Claim Verdict Mapping

When a Claim Verification Report is available, map verdicts to KG review status:

| Claim Verification verdict | KG `review_status` | Notes |
|---|---|---|
| `VERIFIED` | `accepted` | The claim item and linked evidence may remain accepted if the manuscript span is unchanged |
| `MINOR_DISTORTION` | `needs_revision` | Accept only after the span/citation is corrected; record the distortion in `reviewer_notes` |
| `MAJOR_DISTORTION` | `rejected` or `needs_revision` | Use `rejected` when the claim should be removed; use `needs_revision` when it is retained but must be rewritten |
| `UNVERIFIABLE` | `rejected` | The claim is unsupported by the cited source |
| `UNVERIFIABLE_ACCESS` | `in_review` or `needs_revision` | Use `in_review` if access is pending; use `needs_revision` if the manuscript must cite an accessible source |

Claim Verification Reports must include stable claim IDs or stable Claim Registry row numbers so KG `Claim` items can be updated deterministically.

## Revision Synchronization Rules

After Stage 4 or 4' revision, synchronize `article.md` and `{article_id}.kg_candidates.json` before the next review or final integrity gate:

| Manuscript change | KG action |
|---|---|
| Changed claim text, scope, number, citation, or evidentiary basis | Keep the ID only if the semantic claim is the same; set `review_status` to `needs_revision` or `pending` until re-verified |
| Removed claim | Set the matching `Claim` item to `rejected`; add `reviewer_notes` such as `obsolete: removed from article.md in Stage 4 revision` |
| New claim | Create a new `Claim` item with `review_status: pending` |
| Verified unchanged claim | May remain `accepted`; update location/span only if needed |
| Changed concept label or definition | Update the `Concept` item and set `needs_revision` if the change affects meaning |
| Removed concept | Set `review_status: rejected` with an obsolete note |
| New concept | Create a new `Concept` item with `review_status: pending` |
| Changed evidence span or citation | Update or create the `Evidence` item and set `pending` or `needs_revision` until checked |

Do not silently delete obsolete items during the pipeline; preserve them as `rejected` with reviewer notes for auditability.

## Required Pipeline Touchpoints

- Stage 2 WRITE: emit the initial `{article_id}.kg_candidates.json` after the complete draft.
- Stage 2.5 INTEGRITY: update KG review statuses from claim verification and integrity findings.
- Stage 4 / 4' REVISE: emit a KG Candidate Delta for claims, concepts, and evidence added, changed, or removed.
- Stage 4.5 FINAL INTEGRITY: re-check KG synchronization and update review statuses from final claim verification.
- Stage 5 FINALIZE: include the final KG handoff JSON with the output package when present.

## Finalization Checklist

Before Stage 5 completes, confirm:

- [ ] `article.md` is the final verified manuscript.
- [ ] `{article_id}.kg_candidates.json` exists and validates against `kg_layer/schemas/ars_handoff_schema.json`.
- [ ] All current `Claim`, `Concept`, and `Evidence` items have current `supporting_quote_or_span` values from `article.md`.
- [ ] Accepted items correspond to unchanged, verified manuscript content.
- [ ] Removed or superseded items are retained as `rejected` with `reviewer_notes`.
- [ ] Claim Verification Report is attached or referenced if available.
- [ ] Any remaining `pending`, `in_review`, or `needs_revision` items are explicitly listed for human follow-up.
