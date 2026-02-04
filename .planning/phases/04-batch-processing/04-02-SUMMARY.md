---
phase: 04-batch-processing
plan: 02
subsystem: cli
tags: [batch, cli, progress, typer, rich, testing]
dependency-graph:
  requires: [04-01]
  provides: [batch-cli, batch-tests]
  affects: [user-workflow]
tech-stack:
  added: []
  patterns: [rich-progress, typer-cli, pytest-mocking]
key-files:
  created:
    - src/corpora/cli/batch.py
    - tests/test_batch.py
  modified:
    - src/corpora/cli/main.py
decisions:
  - id: batch-exit-codes
    choice: "sysexits.h convention (0/75/66)"
    rationale: "Unix-standard exit codes for scripting"
  - id: worker-auto-detect
    choice: "0 = auto-detect, capped at 8"
    rationale: "Sensible default without overwhelming API"
metrics:
  duration: 3 min
  completed: "2026-02-04"
---

# Phase 04 Plan 02: Batch CLI Command Summary

**One-liner:** Rich progress CLI for batch document processing with --quiet, --force, --workers flags

## What Was Built

### Task 1: Batch CLI Command (src/corpora/cli/batch.py)
- `corpora batch <folder>` command for processing entire directories
- Rich progress bar with spinner, document counts, elapsed time
- Per-document status output (OK/SKIP/FAIL with term counts)
- Options:
  - `--workers N` (0 = auto-detect from CPU cores, capped at 8)
  - `--quiet` shows only errors and final summary
  - `--force` ignores manifest and reprocesses all
  - `--output` overrides default output directory
  - `--blocklist` specifies IP blocklist path
- Exit codes per sysexits.h: 0 (success), 75 (partial), 66 (no input)
- Error log written to output_dir/batch-errors.log on failures

### Task 2: Comprehensive Tests (tests/test_batch.py)
- 23 tests covering:
  - Model tests: DocumentResult, BatchConfig, BatchSummary
  - Processor tests: discovery, manifest skip, force reprocess
  - CLI tests: help, no-docs, invalid-dir, quiet mode, exit codes
  - Helper tests: duration formatting
- Uses pytest fixtures and unittest.mock for isolation
- All tests pass

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Exit codes | sysexits.h (0/75/66) | Standard Unix codes for shell scripting |
| Worker default | 0 = auto (max 8) | Balance between speed and API limits |
| Progress style | Rich with spinner | Consistent with Phase 2 extract progress |

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File | Change | Purpose |
|------|--------|---------|
| src/corpora/cli/batch.py | Created | batch_command with Rich progress |
| src/corpora/cli/main.py | Modified | Register batch command |
| tests/test_batch.py | Created | 23 tests for batch module |

## Integration Points

- **Depends on:** BatchProcessor, BatchConfig, BatchSummary from 04-01
- **Registered in:** src/corpora/cli/main.py
- **Uses:** Rich progress (like extract command)

## Verification Results

| Check | Status |
|-------|--------|
| `corpora batch --help` shows all options | Pass |
| `--workers` controls parallelism | Pass |
| `--quiet` shows only summary | Pass |
| `--force` reprocesses all | Pass |
| Exit code 66 on no documents | Pass |
| Exit code 75 on partial failure | Pass |
| All 23 tests pass | Pass |

## Next Phase Readiness

This completes Phase 4 and the v1 milestone. The full pipeline is now:
1. `corpora parse` - Extract text from PDF/EPUB
2. `corpora extract` - Extract and classify vocabulary
3. `corpora output` - Write .vocab.json files
4. `corpora consolidate` - Merge vocab files
5. `corpora batch` - Process entire folders

All commands support Rich progress display and proper exit codes.
