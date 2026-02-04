# Phase 3: Output & IP Review - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate per-document vocabulary JSON files from classified terms (Phase 2 output), consolidate multiple per-document files into a master vocabulary, deduplicate and merge entries, and flag potentially IP-encumbered terms for human review. This phase handles output generation and IP safety — batch processing of multiple documents is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Output File Structure
- File extension: `.vocab.json` (e.g., `document.vocab.json`)
- Output location: Claude's discretion (same folder as source or dedicated output folder)
- JSON format: Pretty-printed (indented) for human readability and easy diffing
- Metadata: Full extraction info including source path, timestamp, term count, processing stats, schema version

### Consolidation Approach
- Master file: Single flat `master.vocab.json` containing all merged terms
- Variant linking: Each term has `canonical` field pointing to normalized form (unidirectional)
- Safety: Always create `master.vocab.json.bak` backup before consolidation
- Duplicate merge strategy: Claude's discretion (choose sensible approach based on confidence, sources, etc.)

### IP Flagging Criteria
- Detection method: Both blocklist matching AND Claude detection during classification
- Blocklist format: JSON organized by franchise (e.g., `{"dnd": [...], "warhammer": [...]}`)
- Review queue output: Both — add `ip_flag` field to terms in vocabulary AND generate separate `flagged.json` file for review
- Review decision tracking: Claude's discretion

### Incremental Update Strategy
- Tracking method: Manifest file (`.corpora-manifest.json`) listing processed documents with timestamps
- Reprocessing trigger: Claude's discretion (auto-detect changes or require --force)
- Orphan handling: Claude's discretion (keep, remove, or flag orphaned terms)
- Change reporting: Always show diff summary (+X new, ~Y updated, -Z removed)

### Claude's Discretion
- Output file location (same folder vs dedicated folder)
- Duplicate merge strategy for terms appearing in multiple documents
- Reprocessing trigger logic
- Orphan term handling approach
- Review decision file format

</decisions>

<specifics>
## Specific Ideas

- Backup before consolidation is important — don't want to lose a good master vocabulary
- IP flagging should be comprehensive (blocklist + Claude detection) since this is legally critical
- Change summary on consolidation helps verify incremental updates are working correctly

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-output-ip-review*
*Context gathered: 2026-02-04*
