---
phase: 02-vocabulary-extraction
plan: 02
subsystem: classification
tags: [claude-api, batch-api, prompt-caching, pydantic, tenacity]
dependency_graph:
  requires: [02-01]
  provides: [classification-client, batch-classifier, classification-prompts]
  affects: [02-03]
tech_stack:
  added: [anthropic>=0.77.0, tenacity>=8.0]
  patterns: [prompt-caching, exponential-backoff, batch-api]
key_files:
  created:
    - src/corpora/classification/__init__.py
    - src/corpora/classification/prompts.py
    - src/corpora/classification/client.py
    - src/corpora/classification/batch.py
    - tests/__init__.py
    - tests/test_classification.py
  modified:
    - pyproject.toml
    - src/corpora/models/vocabulary.py
decisions:
  - id: CLASS-MODEL
    choice: claude-haiku-4-5-20250929
    rationale: 90% quality of Sonnet at 1/3 cost for classification tasks
  - id: CLASS-CACHE
    choice: ephemeral cache_control on system prompt
    rationale: 90% input cost savings with 5-min TTL
  - id: CLASS-RETRY
    choice: tenacity with exponential backoff (2x, 1-120s, 5 attempts)
    rationale: Industry standard retry pattern for rate limits
metrics:
  duration: 9 min
  completed: 2026-02-04
---

# Phase 02 Plan 02: Claude API Classification Infrastructure Summary

Claude API classification client with Batch API support and prompt caching for cost-efficient vocabulary classification.

## What Was Built

### Classification Prompts (`src/corpora/classification/prompts.py`)

- **CLASSIFICATION_SYSTEM_PROMPT**: ~1139 words (~2093 tokens) detailed system prompt
  - Full 16-axis definitions (8 elemental + 8 mechanical)
  - Output schema with examples
  - Classification guidelines for intent, mood, category
  - Designed for prompt caching (>1024 token threshold)

- **build_user_prompt()**: Single-term classification prompt with optional lemma/POS/context
- **build_batch_user_prompt()**: Multi-term batch prompt for JSON array output

### Classification Client (`src/corpora/classification/client.py`)

- **ClassificationClient**: Claude API wrapper with:
  - Model: `claude-haiku-4-5-20250929` for cost efficiency
  - Prompt caching via `cache_control: {"type": "ephemeral"}`
  - `@retry` decorator for rate limits (5 attempts, exponential backoff)
  - `classify_term()`: Single-term classification
  - `estimate_cost()`: Preview mode cost estimation

### Batch Classifier (`src/corpora/classification/batch.py`)

- **BatchClassifier**: Batch API handler with:
  - `create_batch()`: Create batch requests from term tuples
  - `poll_batch()`: Poll until completion with progress callback
  - `stream_results()`: Yield ClassifiedTerm objects from results
  - `get_batch_status()`: Check request counts
  - `cancel_batch()`: Cancel in-progress batch

### Test Suite (`tests/test_classification.py`)

- 24 tests covering:
  - System prompt length and content (6 tests)
  - ClassificationClient (6 tests)
  - BatchClassifier (7 tests)
  - AxisScores and ClassifiedTerm models (5 tests)
- All tests use mocked API calls for CI

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Model | Haiku 4.5 | 90% quality, 3x cheaper than Sonnet |
| Caching | ephemeral type | 5-min TTL, 90% input cost savings |
| Retry | tenacity | Battle-tested, handles edge cases |
| Batch size | Configurable | Default 50, supports up to 100k |

## Cost Estimation

With prompt caching and Batch API:
- 500 terms: ~$0.51
- 1000 terms: ~$1.02
- 5000 terms: ~$5.08

## Requirements Coverage

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| CLASS-01 | Covered | ClassificationClient.classify_term() |
| CLASS-02 | Covered | Pydantic ClassifiedTerm validation |
| CLASS-03 | Covered | @retry with exponential backoff |
| CLASS-04 | Covered | BatchClassifier with 50% savings |
| CLASS-05 | Covered | cache_control on system prompt |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ClassifiedTerm energy field missing default**
- **Found during:** Task 3 test execution
- **Issue:** The `energy` field in vocabulary.py (from Plan 02-01) lacked a default value, causing test failures
- **Fix:** Added `default=""` to energy field
- **Files modified:** src/corpora/models/vocabulary.py
- **Commit:** 242a95e (bundled with Task 3)

## Files Changed

```
src/corpora/classification/
  __init__.py        # Module exports
  prompts.py         # System prompt + helpers (248 lines)
  client.py          # Claude API client (116 lines)
  batch.py           # Batch API handling (165 lines)

tests/
  __init__.py        # Test package
  test_classification.py  # 24 tests (388 lines)

pyproject.toml       # Added anthropic, tenacity deps
src/corpora/models/vocabulary.py  # Fixed energy default
```

## Commit History

| Hash | Type | Description |
|------|------|-------------|
| cc95b91 | feat | Create classification prompts module |
| 284d54d | feat | Implement Claude API client with retry logic |
| 242a95e | feat | Implement Batch API handling and tests |

## Next Phase Readiness

**Ready for:** Plan 02-03 (CLI integration)

**Available exports:**
- `ClassificationClient` - Sync API classification
- `BatchClassifier` - Batch API for bulk processing
- `CLASSIFICATION_SYSTEM_PROMPT` - For direct use
- `build_user_prompt`, `build_batch_user_prompt` - Prompt helpers

**Integration points:**
- CLI can use `estimate_cost()` for preview mode
- CLI can choose sync vs batch based on term count
- Progress callback available for batch polling
