---
phase: 01-document-parsing
plan: 03
subsystem: cli
tags: [python, typer, ocr, tesseract, pymupdf, cli]

# Dependency graph
requires:
  - phase: 01-01
    provides: Pydantic models (DocumentOutput, ContentBlock), normalize_text, log_error
  - phase: 01-02
    provides: PDFParser, EPUBParser with extract() interface
provides:
  - OCR detection and extraction module (is_ocr_available, needs_ocr_page, extract_with_ocr)
  - Complete CLI with `corpora parse` command
  - All CONTEXT.md flags implemented (-o, -v, --ocr/--no-ocr, --yes, --fail-fast, --partial, --flat)
affects: [02-classification, user-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns: [sysexits.h exit codes, auto-detect with prompting pattern, Rich console for CLI output]

key-files:
  created:
    - src/corpora/parsers/ocr.py
    - src/corpora/cli/parse.py
  modified:
    - src/corpora/parsers/__init__.py
    - src/corpora/cli/__init__.py
    - src/corpora/cli/main.py

key-decisions:
  - "OCR uses PyMuPDF built-in Tesseract integration (get_textpage_ocr)"
  - "OCR detection samples first 3 pages with image coverage heuristics"
  - "Exit codes follow sysexits.h convention (64-66 range)"
  - "Interactive prompt for OCR unless --yes or --no-ocr specified"
  - "Non-interactive mode requires explicit --ocr flag"

patterns-established:
  - "OCR pattern: needs_ocr_page() checks text threshold and image coverage"
  - "CLI pattern: Rich console for stderr, plain stdout for JSON output"
  - "Input resolution: single file, directory (all .pdf/.epub), or glob pattern"

# Metrics
duration: 3min
completed: 2026-02-03
---

# Phase 01 Plan 03: OCR and CLI Summary

**OCR fallback for scanned PDFs using PyMuPDF/Tesseract with complete `corpora parse` CLI supporting all CONTEXT.md flags**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-03T23:04:07Z
- **Completed:** 2026-02-03T23:07:XX
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- OCR detection using image coverage heuristics (80% page coverage + <50 chars)
- OCR extraction using PyMuPDF's built-in Tesseract integration
- Complete CLI with all CONTEXT.md flags implemented
- OCR auto-detection with interactive prompting (unless --yes)
- Error logging to corpora-errors.log with exit codes per sysexits.h

## Task Commits

Each task was committed atomically:

1. **Task 1: Create OCR module** - `3047ff5` (feat)
2. **Task 2: Implement CLI with all flags** - `2fcf9e1` (feat)

## Files Created/Modified

- `src/corpora/parsers/ocr.py` - OCR detection (is_ocr_available, needs_ocr_page/document) and extraction (extract_with_ocr)
- `src/corpora/cli/parse.py` - Parse command with all flags, input resolution, OCR decision handling
- `src/corpora/cli/main.py` - Register parse command with Typer app
- `src/corpora/cli/__init__.py` - Export app and parse_command
- `src/corpora/parsers/__init__.py` - Export OCR functions

## Decisions Made

- **OCR via PyMuPDF:** Used `page.get_textpage_ocr()` rather than direct pytesseract calls for cleaner integration
- **Heuristic thresholds:** 50 char minimum, 80% image coverage - matches RESEARCH.md recommendations
- **Exit codes:** Used sysexits.h convention (64=input error, 65=data error, 66=no input)
- **Non-interactive OCR:** Requires explicit --ocr flag in non-interactive mode for safety
- **Output handling:** JSON array when multiple files output to single destination

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly.

## User Setup Required

**For OCR functionality (optional):**

1. Install Tesseract OCR:
   - Windows: `choco install tesseract`
   - macOS: `brew install tesseract`
   - Linux: `apt install tesseract-ocr`

2. Install Python wrapper:
   - `pip install pytesseract` or `pip install corpora[ocr]`

3. Verify: `corpora parse scanned.pdf --ocr` should process without errors

## Next Phase Readiness

Phase 1 is now complete. All success criteria from ROADMAP.md achievable:
- `corpora parse <file>` extracts text to stdout
- `corpora parse <file> -o output.json` writes JSON file
- OCR auto-detects and prompts before running (unless --yes)
- `--ocr` forces OCR, `--no-ocr` skips it
- Errors logged to corpora-errors.log
- `--fail-fast` stops on first error, default continues

Ready for Phase 2: Classification.

---
*Phase: 01-document-parsing*
*Completed: 2026-02-03*
