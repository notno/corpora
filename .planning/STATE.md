# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Extract and classify fantasy vocabulary from source documents into structured, game-ready JSON
**Current focus:** Phase 2 - Vocabulary Extraction & Classification

## Current Position

Phase: 2 of 4 (Vocabulary Extraction & Classification)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-02-04 - Completed 02-01-PLAN.md

Progress: [######----] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 5.4 min
- Total execution time: 0.45 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-document-parsing | 3 | 8 min | 2.7 min |
| 02-vocabulary-extraction | 2 | 19 min | 9.5 min |

**Recent Trend:**
- Last 5 plans: 01-02 (2 min), 01-03 (3 min), 02-02 (6 min), 02-01 (13 min)
- Trend: Increasing complexity (NLP/API integration)

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-04T03:47:33Z
Stopped at: Completed 02-01-PLAN.md
Resume file: None
