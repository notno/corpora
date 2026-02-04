# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Extract and classify fantasy vocabulary from source documents into structured, game-ready JSON
**Current focus:** Phase 4 (Batch Processing) - In Progress

## Current Position

Phase: 4 of 4 (Batch Processing)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-04 - Completed 04-01-PLAN.md

Progress: [###########-] 92% (11/12 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 4.4 min
- Total execution time: 0.80 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-document-parsing | 3 | 8 min | 2.7 min |
| 02-vocabulary-extraction | 3 | 27 min | 9.0 min |
| 03-output-ip-review | 4 | 13 min | 3.3 min |
| 04-batch-processing | 1 | 4 min | 4.0 min |

**Recent Trend:**
- Last 5 plans: 03-02 (3 min), 03-03 (3 min), 03-04 (5 min), 04-01 (4 min)
- Trend: Consistent execution speed (~3-5 min per plan)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Claude API over local LLM for rich classification on CPU-only machine
- [Init]: Per-document JSON then consolidate for incremental processing
- [Init]: Separate IP review step for human oversight
- [01-01]: src-layout package structure for clean imports
- [01-01]: Pydantic v2 with model_dump_json for serialization
- [01-01]: NFKC normalization for ligature decomposition
- [01-02]: BaseParser ABC with can_parse, extract, needs_ocr methods
- [01-02]: PyMuPDF sort=True for proper reading order in PDFs
- [01-02]: Chapter-aware extraction with page-by-page fallback for EPUBs
- [01-02]: Warnings not exceptions for encoding errors (PARSE-05)
- [01-03]: OCR uses PyMuPDF built-in Tesseract integration (get_textpage_ocr)
- [01-03]: Exit codes follow sysexits.h convention (64-66 range)
- [01-03]: Interactive prompt for OCR unless --yes or --no-ocr specified
- [02-01]: spaCy en_core_web_sm with NER disabled for fast extraction
- [02-01]: ~200 common English words filtered in addition to spaCy stopwords
- [02-01]: Noun chunks filtered to 2-3 content words for phrase extraction
- [02-01]: Deduplication by lemma to avoid redundant candidates
- [02-02]: Claude Haiku 4.5 model for cost-efficient classification
- [02-02]: Prompt caching with ephemeral cache_control
- [02-02]: tenacity for exponential backoff on rate limits
- [02-03]: Preview mode with cost estimation before API calls
- [02-03]: Batch API default for 50% cost savings, --sync for synchronous
- [02-03]: Rich progress bar for classification feedback
- [03-01]: Schema version 1.0 for forward compatibility
- [03-01]: MD5 hash with 64KB chunked reading for memory efficiency
- [03-01]: ip_flag passthrough - vocab_writer preserves flags, does not check blocklist
- [03-02]: Dual detection: blocklist matching + classification-time detection
- [03-02]: Franchise-organized JSON blocklist for user customization
- [03-02]: Pre-compiled regex patterns for efficient multi-word matching
- [03-03]: Manifest uses MD5 content hashes for change detection
- [03-03]: Merge strategy: highest confidence entry as base, weighted axis average
- [03-03]: Backup: both timestamped .bak AND simple .bak for easy restore
- [03-04]: Review queue sorted alphabetically by canonical
- [03-04]: Automatic flagged.json on IP-flagged terms detection
- [03-04]: CLI default blocklist: data/ip-blocklist.json
- [04-01]: Full pipeline per document (not step batching) for simplicity
- [04-01]: Independent worker backoff with tenacity (no shared rate limiter)
- [04-01]: Sync API for classification in batch (parallel-friendly)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-04T20:41:28Z
Stopped at: Completed 04-01-PLAN.md
Resume file: None
