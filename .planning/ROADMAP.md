# Roadmap: Corpora

## Overview

This roadmap delivers a fantasy vocabulary extraction pipeline in four phases. Phase 1 establishes document parsing (PDF/EPUB). Phase 2 builds the core value: Claude API classification of extracted terms. Phase 3 handles output generation, consolidation, and IP review (legally critical before shipping). Phase 4 adds batch processing for production-scale use.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Document Parsing** - Extract and normalize text from PDF and EPUB files
- [ ] **Phase 2: Vocabulary Extraction & Classification** - Extract terms and classify with Claude API
- [ ] **Phase 3: Output & IP Review** - Generate per-document JSON, consolidate, and flag IP-encumbered terms
- [ ] **Phase 4: Batch Processing** - Process document folders with progress tracking and resumability

## Phase Details

### Phase 1: Document Parsing
**Goal**: Users can extract clean, normalized text from PDF and EPUB documents
**Depends on**: Nothing (first phase)
**Requirements**: PARSE-01, PARSE-02, PARSE-03, PARSE-04, PARSE-05
**Success Criteria** (what must be TRUE):
  1. User can run CLI command on a PDF file and receive extracted text output
  2. User can run CLI command on an EPUB file and receive extracted text output
  3. Scanned PDFs automatically fall back to OCR when native text extraction fails
  4. Extracted text is normalized to consistent format regardless of source format
  5. Font encoding issues produce warnings but do not crash processing
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md - Project setup, Pydantic models, and utility modules
- [x] 01-02-PLAN.md - PDF and EPUB parser implementation
- [x] 01-03-PLAN.md - OCR integration and CLI implementation

### Phase 2: Vocabulary Extraction & Classification
**Goal**: Users can extract fantasy-relevant terms from text and receive richly classified vocabulary
**Depends on**: Phase 1
**Requirements**: EXTRACT-01, EXTRACT-02, EXTRACT-03, CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05
**Success Criteria** (what must be TRUE):
  1. User can extract candidate vocabulary from parsed document text
  2. Extracted terms include nouns, verbs, adjectives, and multi-word expressions
  3. Each term is classified with full schema (id, text, genre, intent, pos, axes, tags, category, canonical, mood, energy, source)
  4. Classification output validates against Pydantic schema without errors
  5. API rate limits are respected without manual intervention (automatic backoff)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Output & IP Review
**Goal**: Users can generate per-document JSON, consolidate into master vocabulary, and review IP-flagged terms
**Depends on**: Phase 2
**Requirements**: OUTPUT-01, OUTPUT-02, OUTPUT-03, OUTPUT-04, IP-01, IP-02, IP-03
**Success Criteria** (what must be TRUE):
  1. User can generate one JSON file per processed source document
  2. User can consolidate multiple per-document JSONs into a single master vocabulary
  3. Duplicate entries are merged with variants linked to canonical forms
  4. Incremental updates add new documents without reprocessing existing ones
  5. Terms potentially IP-encumbered are flagged for human review
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Batch Processing
**Goal**: Users can process entire folders of documents with progress tracking and fault tolerance
**Depends on**: Phase 3
**Requirements**: BATCH-01, BATCH-02, BATCH-03, BATCH-04
**Success Criteria** (what must be TRUE):
  1. User can point CLI at a folder and process all supported documents
  2. Progress display shows documents completed vs remaining
  3. Interrupted processing can resume from where it stopped
  4. Multiple documents can process in parallel for faster throughput
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Document Parsing | 3/3 | ✓ Complete | 2026-02-03 |
| 2. Vocabulary Extraction & Classification | 0/TBD | Not started | - |
| 3. Output & IP Review | 0/TBD | Not started | - |
| 4. Batch Processing | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-03*
*Last updated: 2026-02-03 - Phase 1 complete*
