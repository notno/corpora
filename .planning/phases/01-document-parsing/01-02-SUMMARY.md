---
phase: 01-document-parsing
plan: 02
subsystem: parsers
tags: [python, pymupdf, pdf, epub, text-extraction]

# Dependency graph
requires:
  - phase: 01-01
    provides: Pydantic models (DocumentOutput, ContentBlock), normalize_text utility
provides:
  - Abstract BaseParser interface for document parsers
  - PDFParser with page-by-page text extraction
  - EPUBParser with chapter-aware text extraction
  - Graceful error handling for encoding issues
affects: [01-document-parsing, 02-classification]

# Tech tracking
tech-stack:
  added: []
  patterns: [ABC parser interface, location-based EPUB addressing]

key-files:
  created:
    - src/corpora/parsers/base.py
    - src/corpora/parsers/pdf.py
    - src/corpora/parsers/epub.py
  modified:
    - src/corpora/parsers/__init__.py

key-decisions:
  - "BaseParser ABC with can_parse, extract, needs_ocr methods"
  - "PyMuPDF sort=True for proper reading order in PDFs"
  - "Chapter-aware extraction with page-by-page fallback for EPUBs"
  - "Warnings not exceptions for encoding errors (PARSE-05)"

patterns-established:
  - "Parser interface: can_parse(), extract(flat), needs_ocr()"
  - "Extract returns DocumentOutput with ContentBlock list"
  - "warnings.warn() for non-fatal extraction issues"

# Metrics
duration: 2min
completed: 2026-02-03
---

# Phase 1 Plan 2: Document Parsers Summary

**PDF and EPUB text extraction using PyMuPDF with unified BaseParser interface and graceful encoding error handling**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-03T22:59:29Z
- **Completed:** 2026-02-03T23:01:45Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- BaseParser ABC defining consistent interface (can_parse, extract, needs_ocr)
- PDFParser with page-by-page extraction, sort=True for reading order
- EPUBParser with chapter-aware extraction via location-based addressing
- OCR detection heuristic for scanned PDFs (image coverage + minimal text)
- Graceful handling of encoding errors via warnings

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BaseParser interface and PDFParser** - `4015cee` (feat)
2. **Task 2: Create EPUBParser** - `18c46b0` (feat)

## Files Created/Modified
- `src/corpora/parsers/base.py` - Abstract BaseParser class with 3 abstract methods
- `src/corpora/parsers/pdf.py` - PDFParser using PyMuPDF with OCR detection heuristic
- `src/corpora/parsers/epub.py` - EPUBParser with chapter-aware and page-by-page extraction
- `src/corpora/parsers/__init__.py` - Export BaseParser, PDFParser, EPUBParser

## Decisions Made
- Used PyMuPDF's `sort=True` parameter for proper reading order in PDFs
- Chapter-aware extraction uses location-based addressing `(chapter_num, page_num)` per PyMuPDF docs
- Fall back to page-by-page extraction when `chapter_count <= 1`
- OCR detection threshold: image covering >80% of page + <50 chars extracted text
- EPUBs never need OCR (text-based format)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all imports and verifications passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Parsers ready for CLI integration in Plan 03
- PDFParser and EPUBParser can be selected based on file extension
- Both parsers produce DocumentOutput compatible with Phase 2 classification

---
*Phase: 01-document-parsing*
*Completed: 2026-02-03*
