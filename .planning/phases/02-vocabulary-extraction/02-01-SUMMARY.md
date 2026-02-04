---
phase: 02-vocabulary-extraction
plan: 01
subsystem: extraction
tags: [spacy, nlp, pydantic, vocabulary, term-extraction]

# Dependency graph
requires:
  - phase: 01-document-parsing
    provides: DocumentOutput model with extracted text content
provides:
  - CandidateTerm, AxisScores, ClassifiedTerm Pydantic models
  - TermExtractor for NLP-based term extraction
  - TermFilter for stopword and common word filtering
affects: [02-02-classification, 02-03-cli]

# Tech tracking
tech-stack:
  added: [spacy, en_core_web_sm]
  patterns: [hybrid-nlp-extraction, lemma-deduplication]

key-files:
  created:
    - src/corpora/models/vocabulary.py
    - src/corpora/extraction/__init__.py
    - src/corpora/extraction/extractor.py
    - src/corpora/extraction/filters.py
    - tests/test_extraction.py
  modified:
    - src/corpora/models/__init__.py
    - src/corpora/models/output.py

key-decisions:
  - "spaCy en_core_web_sm with NER disabled for fast extraction"
  - "~200 common English words filtered in addition to spaCy stopwords"
  - "Noun chunks filtered to 2-3 content words for phrase extraction"
  - "Deduplication by lemma to avoid redundant candidates"

patterns-established:
  - "CandidateTerm with source_span for traceability back to original text"
  - "TermFilter.should_keep() pattern for extensible filtering"
  - "16-axis classification system (8 elemental + 8 mechanical)"

# Metrics
duration: 13min
completed: 2026-02-04
---

# Phase 2 Plan 1: Term Extraction Summary

**spaCy-based NLP extraction pipeline with 16-axis vocabulary models and stopword/common-word filtering**

## Performance

- **Duration:** 13 min
- **Started:** 2026-02-04T03:34:51Z
- **Completed:** 2026-02-04T03:47:33Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Created CandidateTerm, AxisScores, and ClassifiedTerm Pydantic models for the extraction pipeline
- Implemented TermExtractor using spaCy for noun, verb, adjective, and phrase extraction
- Built TermFilter with ~670 stopwords (spaCy defaults + common English words)
- Added 19 comprehensive tests covering all extraction and filtering functionality

## Task Commits

Each task was committed atomically:

1. **Task 1: Create vocabulary models** - `a73eaf8` (feat)
2. **Task 2: Implement term extraction with spaCy** - `b5c9290` (feat)
3. **Task 3: Add extraction tests** - `a0b03cb` (test)

## Files Created/Modified

- `src/corpora/models/vocabulary.py` - CandidateTerm, AxisScores, ClassifiedTerm models
- `src/corpora/extraction/__init__.py` - Module exports
- `src/corpora/extraction/extractor.py` - TermExtractor class with spaCy integration
- `src/corpora/extraction/filters.py` - TermFilter with stopword and common word filtering
- `tests/test_extraction.py` - 19 tests for extraction functionality
- `src/corpora/models/__init__.py` - Updated exports for new models
- `src/corpora/models/output.py` - Cleaned up to contain only Phase 1 models

## Decisions Made

- **spaCy model:** Used en_core_web_sm with NER disabled for faster processing (NER not needed for POS tagging)
- **Filtering approach:** Combined spaCy's built-in stopwords with a curated list of ~200 high-frequency English words
- **Phrase extraction:** Limited to 2-3 content words from noun chunks (filtering out DET, PRON, ADP, CCONJ)
- **Deduplication:** By lemma to avoid redundant candidates (e.g., "wizard" and "wizards")
- **Source spans:** Tracked character offsets in source_span for traceability

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed spaCy dependency**
- **Found during:** Task 2 preparation
- **Issue:** spaCy not installed, blocking extraction implementation
- **Fix:** Ran `pip install spacy` and `python -m spacy download en_core_web_sm`
- **Files modified:** None (dependency installation)
- **Verification:** `import spacy; spacy.load('en_core_web_sm')` succeeds
- **Committed in:** Not committed (dependency installation)

**2. [Rule 1 - Bug] Fixed duplicate model definitions in output.py**
- **Found during:** Task 1
- **Issue:** AxisScores and ClassifiedTerm were added to output.py by linter, creating duplicates
- **Fix:** Cleaned output.py to contain only Phase 1 models, vocabulary.py has extraction models
- **Files modified:** src/corpora/models/output.py
- **Verification:** Imports work correctly from both modules
- **Committed in:** a73eaf8 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correct operation. No scope creep.

## Issues Encountered

- Capitalized words like "Wizards" are tagged as PROPN (proper noun) by spaCy, not NOUN. This is expected behavior and tests were adjusted accordingly.

## User Setup Required

None - spaCy and model are installed via pip.

## Next Phase Readiness

- Extraction module ready for use by classification pipeline (02-02)
- CandidateTerm output can be passed to Claude for classification
- TermFilter can be extended if additional filtering is needed

---
*Phase: 02-vocabulary-extraction*
*Completed: 2026-02-04*
