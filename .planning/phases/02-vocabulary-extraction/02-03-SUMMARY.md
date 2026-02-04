---
phase: 02-vocabulary-extraction
plan: 03
subsystem: cli
tags: [typer, rich, progress-bar, batch-api, cli]

# Dependency graph
requires:
  - phase: 02-01
    provides: TermExtractor for NLP-based candidate extraction
  - phase: 02-02
    provides: ClassificationClient and BatchClassifier for Claude API
provides:
  - "corpora extract" CLI command with preview/sync/batch modes
  - Progress bar for classification feedback
  - Verbose mode for term-by-term debugging
  - Output to file or stdout
affects: [03-consolidation]

# Tech tracking
tech-stack:
  added: []
  patterns: [cli-preview-mode, rich-progress-bar, batch-vs-sync-toggle]

key-files:
  created:
    - src/corpora/cli/extract.py
    - tests/test_extract_cli.py
  modified:
    - src/corpora/cli/main.py

key-decisions:
  - "Preview mode uses estimate_cost() without API calls"
  - "Default mode uses Batch API for 50% cost savings"
  - "--sync flag switches to synchronous API with progress bar"
  - "Verbose mode shows category for each classified term"

patterns-established:
  - "CLI preview pattern: show work preview without doing work"
  - "load_document() for Phase 1 JSON loading with validation"
  - "_classify_sync() and _classify_batch() as separate code paths"

# Metrics
duration: 5min
completed: 2026-02-04
---

# Phase 02 Plan 03: Extract CLI Command Summary

**CLI extract command with preview mode, progress bar, and sync/batch classification options**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-04T03:52:22Z
- **Completed:** 2026-02-04T03:57:45Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Implemented `corpora extract` command that processes Phase 1 JSON documents
- Added preview mode showing term count, sample terms, and estimated API cost
- Implemented sync mode with Rich progress bar and retry logic
- Implemented batch mode using Batch API for 50% cost savings
- Created 11 comprehensive CLI tests with mocked API calls

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement extract CLI command** - `80d6726` (feat)
2. **Task 2: Register extract command in CLI** - `1cf98c2` (feat)
3. **Task 3: Add CLI tests** - `39c3769` (test)

## Files Created/Modified

- `src/corpora/cli/extract.py` - Full extract command with load_document, _show_preview, _classify_sync, _classify_batch, _write_results
- `src/corpora/cli/main.py` - Added extract_command import and registration
- `tests/test_extract_cli.py` - 11 tests covering help, preview, sync, batch, errors

## Decisions Made

- **Preview mode**: Uses ClassificationClient.estimate_cost() to show token/cost estimates without making API calls
- **Default to batch**: Batch API provides 50% cost savings, so it's the default; --sync flag for synchronous mode
- **Progress bar**: Rich progress bar shows classification progress in non-verbose mode
- **Verbose term-by-term**: -v flag shows each term's classification result inline

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - CLI uses existing dependencies (typer, rich already installed).

## Next Phase Readiness

**Phase 02 Complete.** The vocabulary extraction pipeline is fully operational:

- **Parse** (`corpora parse`): Extracts text from PDF/EPUB to JSON
- **Extract** (`corpora extract`): Extracts terms and classifies with Claude

**Available for Phase 03:**
- ClassifiedTerm output can be consolidated across documents
- JSON array format ready for deduplication and merging
- Source tracking enables IP review workflow

---
*Phase: 02-vocabulary-extraction*
*Completed: 2026-02-04*
