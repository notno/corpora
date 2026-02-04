# Phase 4: Batch Processing - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Process entire folders of documents with progress tracking and fault tolerance. Users can point the CLI at a folder, process all supported documents (PDF/EPUB), and get vocabulary output for each. Interrupted runs can resume from where they stopped. This is the final phase of the v1 milestone.

</domain>

<decisions>
## Implementation Decisions

### Progress Reporting
- Display style: Rich progress bar (like Phase 2 classification)
- Per-document info: Document name + term count as results come in
- End summary: Full summary with total docs, terms extracted, terms flagged, time taken, any errors
- Quiet mode: --quiet flag for CI/scripts (shows only errors and final summary)

### Parallelization
- Worker count: Auto-detect based on CPU cores or sensible limit, with --workers N override
- API rate limits: Claude's discretion on coordinating workers vs independent backoff
- Batch scale: Optimized for small batches (5-20 documents typical use case)
- Pipeline style: Claude's discretion (full pipeline per document vs step batching)

### Resume Behavior
- Resume trigger: Automatic detection of previous run, skip already-completed documents
- State storage: Use existing .corpora-manifest.json from Phase 3 (already tracks processed docs)
- Force reprocess: --force flag to ignore manifest and reprocess all
- Partial state: Reprocess document from scratch if partially completed (safer)

### Error Handling
- Failure mode: Continue with other documents, don't stop on single failure
- Error logging: Both inline during progress AND write to error log file
- Retry: Retry each failed document once before marking as failed
- Exit codes: Claude's discretion based on sysexits.h convention

### Claude's Discretion
- API rate coordination strategy (shared limiter vs independent backoff)
- Pipeline execution style (per-document vs step batching)
- Exit code semantics for partial success
- Error log file location and format
- Specific worker count limits

</decisions>

<specifics>
## Specific Ideas

- Typical batch is 5-20 documents at a time (books/PDFs), not huge archives
- Should feel like a smooth, interruptible operation — can stop and resume easily
- Progress bar style consistent with existing Phase 2 classification progress

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-batch-processing*
*Context gathered: 2026-02-04*
