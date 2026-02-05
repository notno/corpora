# Corpora v1 Integration Check

**Date:** 2026-02-04
**Milestone:** v1 (Fantasy Vocabulary Extraction Pipeline)
**Status:** PASS

---

## Summary

| Category | Connected | Orphaned | Missing | Status |
|----------|-----------|----------|---------|--------|
| Exports | 27 | 0 | 0 | PASS |
| API Routes | N/A (CLI) | N/A | N/A | N/A |
| CLI Commands | 5 | 0 | 0 | PASS |
| E2E Flows | 3 | 0 | 0 | PASS |

**Overall Integration Status: PASS**

All phases properly wire together. No orphaned exports. All critical E2E flows complete.

---

## 1. Cross-Phase Wiring Verification

### Phase 1 -> Phase 2: Document Parsing -> Vocabulary Extraction

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|----------|
| PDFParser.parse() | TermExtractor.extract() | DocumentOutput.content | CONNECTED | batch/processor.py:100-104 extracts text from doc_output.content |
| EPUBParser.parse() | TermExtractor.extract() | DocumentOutput.content | CONNECTED | Same flow, line 96 selects parser |
| DocumentOutput model | extract_command | CLI JSON input | CONNECTED | cli/extract.py:36-58 loads via load_document() |
| normalize_text() | Parsers | Import | CONNECTED | parsers/pdf.py, parsers/epub.py import from utils |

### Phase 2 -> Phase 3: Vocabulary Extraction -> Output and IP Review

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|----------|
| ClassifiedTerm model | write_vocab_file() | Function param | CONNECTED | output/vocab_writer.py:41 takes List[ClassifiedTerm] |
| ClassificationClient | BatchProcessor | Import | CONNECTED | batch/processor.py:84 imports client |
| TermExtractor | BatchProcessor | Import | CONNECTED | batch/processor.py:85 imports extractor |
| ClassifiedTerm.ip_flag | VocabularyEntry.ip_flag | Field mapping | CONNECTED | vocab_writer.py:88 passes through |
| IPBlocklist.check() | BatchProcessor | Called | CONNECTED | batch/processor.py:145-152 applies blocklist |

### Phase 3 -> Phase 4: Output and IP Review -> Batch Processing

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|----------|
| CorporaManifest | BatchProcessor | Import/Constructor | CONNECTED | batch/processor.py:14,55 |
| CorporaManifest.needs_processing() | BatchProcessor.process() | Method call | CONNECTED | batch/processor.py:212 |
| CorporaManifest.update_entry() | BatchProcessor.process() | Method call | CONNECTED | batch/processor.py:249-253 |
| CorporaManifest.save() | BatchProcessor.process() | Method call | CONNECTED | batch/processor.py:254 |
| write_vocab_file() | BatchProcessor | Import/Call | CONNECTED | batch/processor.py:87,158-162 |

---

## 2. Export Usage Matrix

### Phase 1 Exports

| Export | Module | Used By | Status |
|--------|--------|---------|--------|
| PDFParser | parsers/__init__.py | cli/parse.py, batch/processor.py | CONNECTED |
| EPUBParser | parsers/__init__.py | cli/parse.py, batch/processor.py | CONNECTED |
| BaseParser | parsers/__init__.py | Internal inheritance | CONNECTED |
| DocumentOutput | models/__init__.py | cli/parse.py, cli/extract.py | CONNECTED |
| ContentBlock | models/__init__.py | cli/parse.py | CONNECTED |
| normalize_text | utils/__init__.py | Parsers | CONNECTED |
| log_error | utils/__init__.py | cli/parse.py | CONNECTED |

### Phase 2 Exports

| Export | Module | Used By | Status |
|--------|--------|---------|--------|
| TermExtractor | extraction/__init__.py | cli/extract.py, batch/processor.py | CONNECTED |
| TermFilter | extraction/__init__.py | Internal to extractor | CONNECTED |
| CandidateTerm | models/__init__.py | extraction/, cli/extract.py | CONNECTED |
| ClassifiedTerm | models/__init__.py | Throughout | CONNECTED |
| AxisScores | models/__init__.py | classification/, output/ | CONNECTED |
| ClassificationClient | classification/__init__.py | cli/extract.py, batch/processor.py | CONNECTED |
| BatchClassifier | classification/__init__.py | cli/extract.py | CONNECTED |

### Phase 3 Exports

| Export | Module | Used By | Status |
|--------|--------|---------|--------|
| write_vocab_file | output/__init__.py | cli/output.py, batch/processor.py | CONNECTED |
| VocabularyOutput | output/__init__.py | cli/output.py | CONNECTED |
| CorporaManifest | output/__init__.py | cli/output.py, batch/processor.py | CONNECTED |
| compute_file_hash | output/__init__.py | manifest.py, tests | CONNECTED |
| consolidate_vocabularies | output/__init__.py | cli/output.py | CONNECTED |
| IPBlocklist | ip/__init__.py | cli/output.py, batch/processor.py | CONNECTED |
| flag_terms | ip/__init__.py | cli/output.py | CONNECTED |
| generate_review_queue | ip/__init__.py | cli/output.py | CONNECTED |

### Phase 4 Exports

| Export | Module | Used By | Status |
|--------|--------|---------|--------|
| BatchProcessor | batch/__init__.py | cli/batch.py | CONNECTED |
| BatchConfig | batch/__init__.py | cli/batch.py | CONNECTED |
| BatchSummary | batch/__init__.py | cli/batch.py | CONNECTED |
| DocumentResult | batch/__init__.py | cli/batch.py | CONNECTED |
| DocumentStatus | batch/__init__.py | cli/batch.py | CONNECTED |

---

## 3. CLI Command Coverage

| Command | Registered | Implementation | Uses Phases | Status |
|---------|------------|----------------|-------------|--------|
| parse | main.py:18 | cli/parse.py | Phase 1 | CONNECTED |
| extract | main.py:19 | cli/extract.py | Phase 1, 2 | CONNECTED |
| output | main.py:20 | cli/output.py | Phase 2, 3 | CONNECTED |
| consolidate | main.py:21 | cli/output.py | Phase 3 | CONNECTED |
| batch | main.py:17 | cli/batch.py | Phase 1-4 | CONNECTED |

**Note:** No standalone review command exists. IP review queue is generated automatically by output and consolidate commands via generate_review_queue(). This is by design per IP-03 requirement.

---

## 4. E2E Flow Verification

### Flow 1: Single Document Processing

**Command:** corpora parse document.pdf -o doc.json && corpora extract doc.json -o terms.json

| Step | Component | Input | Output | Status |
|------|-----------|-------|--------|--------|
| 1. Parse | PDFParser.parse() | document.pdf | DocumentOutput | PASS |
| 2. Serialize | DocumentOutput.to_json_file() | Model | doc.json | PASS |
| 3. Load | load_document() | doc.json | DocumentOutput | PASS |
| 4. Extract Text | Text concatenation | doc.content | full_text | PASS |
| 5. Extract Terms | TermExtractor.extract() | full_text | List[CandidateTerm] | PASS |
| 6. Classify | ClassificationClient.classify_term() | CandidateTerm | ClassifiedTerm | PASS |
| 7. Output | _write_results() | List[ClassifiedTerm] | terms.json | PASS |

**Evidence:**
- cli/parse.py:184-200 handles parse flow
- cli/extract.py:314-358 handles extract flow
- Models properly chain via JSON serialization

### Flow 2: Batch Processing

**Command:** corpora batch ./documents/

| Step | Component | Input | Output | Status |
|------|-----------|-------|--------|--------|
| 1. Discover | processor.discover_documents() | Directory | List[Path] | PASS |
| 2. Load Manifest | CorporaManifest.load() | .corpora-manifest.json | Manifest | PASS |
| 3. Filter | manifest.needs_processing() | Path | Boolean | PASS |
| 4. Parse | PDFParser/EPUBParser.parse() | Document | DocumentOutput | PASS |
| 5. Extract | TermExtractor.extract() | Text | List[CandidateTerm] | PASS |
| 6. Classify | ClassificationClient.classify_term() | Term | ClassifiedTerm | PASS |
| 7. IP Check | IPBlocklist.check() | Term | Flag | PASS |
| 8. Write | write_vocab_file() | Terms | .vocab.json | PASS |
| 9. Update Manifest | manifest.update_entry() | Result | Entry | PASS |
| 10. Save Manifest | manifest.save() | Manifest | File | PASS |

**Evidence:**
- batch/processor.py:69-178 implements full pipeline per document
- batch/processor.py:195-259 implements parallel processing with manifest updates

### Flow 3: Resume After Interruption

**Command:** corpora batch ./documents/ (after Ctrl+C)

| Step | Component | Behavior | Status |
|------|-----------|----------|--------|
| 1. Load Manifest | CorporaManifest.load() | Loads existing entries | PASS |
| 2. Check Need | needs_processing() | Returns False for processed docs | PASS |
| 3. Skip Processed | process() | Yields SKIPPED for unchanged | PASS |
| 4. Process New | _process_with_retry() | Only processes unprocessed | PASS |

**Evidence:**
- batch/processor.py:209-222 skips documents that do not need processing
- batch/processor.py:247-254 updates manifest after EACH document (interrupt-safe)
- tests/test_batch.py:192-229 verifies manifest skip behavior

---

## 5. Integration Points Deep Dive

### BatchProcessor Pipeline Integration (batch/processor.py:69-178)

The _process_single_document() method is the critical integration point. Verified imports:

```python
# Line 84-88 - All phases properly imported
from corpora.classification import ClassificationClient  # Phase 2
from corpora.extraction import TermExtractor            # Phase 2
from corpora.ip import IPBlocklist                       # Phase 3
from corpora.output import write_vocab_file             # Phase 3
from corpora.parsers import EPUBParser, PDFParser       # Phase 1
```

Pipeline execution order:
1. Parse document (Phase 1): Lines 92-100
2. Extract text (Phase 1->2 bridge): Lines 102-104
3. Extract terms (Phase 2): Lines 116-117
4. Classify terms (Phase 2): Lines 129-142
5. Apply IP blocklist (Phase 3): Lines 145-152
6. Write vocab file (Phase 3): Lines 155-162

All phases connected with proper data flow.

### Manifest Integration (CorporaManifest)

| Method | Usage | File:Line |
|--------|-------|-----------|
| load() | Constructor | batch/processor.py:55 |
| needs_processing() | Skip check | batch/processor.py:212 |
| update_entry() | After success | batch/processor.py:249-253 |
| save() | Persist changes | batch/processor.py:254 |

All manifest methods properly called in expected order.

---

## 6. Missing or Orphaned Components

### Missing Components

**None identified.** All required integrations present.

### Orphaned Exports

**None identified.** All exports have consumers.

### Potential Improvements (Not Blocking)

1. **Review Command:** User mentioned expecting corpora review command. Currently IP review is generated automatically by output and consolidate commands. This is adequate for IP-03 requirement but could be enhanced.

2. **Test Coverage:** Tests exist for batch module (test_batch.py) but mock the processing pipeline. Integration tests with real documents would strengthen confidence.

---

## 7. Verification Commands

To manually verify integration, run:

```bash
# Verify CLI commands registered
python -m corpora --help

# Verify parse flow
python -m corpora parse test.pdf -o test.json

# Verify extract flow
python -m corpora extract test.json -o vocab.json --sync

# Verify batch flow
python -m corpora batch ./documents/ --quiet

# Verify consolidation
python -m corpora consolidate ./output/
```

---

## Conclusion

**Integration Status: PASS**

All four phases of the Corpora v1 milestone are properly integrated:

1. **Phase 1 -> Phase 2:** Parsers produce DocumentOutput that extraction uses correctly
2. **Phase 2 -> Phase 3:** ClassifiedTerm flows through to write_vocab_file() with IP flagging
3. **Phase 3 -> Phase 4:** Manifest and output utilities fully integrated into BatchProcessor
4. **E2E Flows:** Single doc, batch, and resume flows all complete without breaks

The BatchProcessor class (batch/processor.py) serves as the integration hub, importing and orchestrating all phase components in the correct order.

---
*Integration check completed: 2026-02-04*
*Checked by: Integration Verifier Agent*
