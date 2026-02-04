---
status: complete
phase: 03-output-ip-review
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md]
started: 2026-02-04T06:45:00Z
updated: 2026-02-04T06:48:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Generate Per-Document Vocabulary JSON
expected: Run `corpora output <extract-json>` on an extracted vocabulary file. Creates a `.vocab.json` file with schema_version, source hash, and classified entries.
result: skipped
reason: No extracted vocabulary file available for testing

### 2. IP Blocklist Detection
expected: Terms matching IP blocklist (D&D, Warhammer, LOTR terms like "Beholder", "Mind Flayer") are flagged with `ip_flag: "blocklist:<franchise>"` in output.
result: skipped
reason: No pipeline output available for testing

### 3. Consolidate Multiple Vocab Files
expected: Run `corpora consolidate <vocab-dir>` to merge multiple `.vocab.json` files into `master.vocab.json`. Shows change summary (+new, ~updated).
result: skipped
reason: No pipeline output available for testing

### 4. Duplicate Merging
expected: When consolidating, terms with the same `canonical` form are merged. Sources combined, confidence-weighted axis averaging applied.
result: skipped
reason: No pipeline output available for testing

### 5. Incremental Processing
expected: Running consolidate again after adding a new vocab file only processes the new file (detected via content hash in manifest).
result: skipped
reason: No pipeline output available for testing

### 6. IP Flagged Terms Generate Review Queue
expected: If any terms have `ip_flag` set, a `flagged.json` file is automatically created with the flagged terms for human review.
result: skipped
reason: No pipeline output available for testing

### 7. Backup on Update
expected: Updating an existing `master.vocab.json` creates a timestamped backup (e.g., `master.vocab.json.2026-02-04T...bak`).
result: skipped
reason: No pipeline output available for testing

## Summary

total: 7
passed: 0
issues: 0
pending: 0
skipped: 7

## Gaps

[none yet]
