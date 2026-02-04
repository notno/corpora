# Requirements: Corpora

**Defined:** 2026-02-03
**Core Value:** Extract and classify fantasy vocabulary from source documents into structured, game-ready JSON

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Document Parsing

- [x] **PARSE-01**: Extract text content from PDF files
- [x] **PARSE-02**: Extract text content from EPUB files
- [x] **PARSE-03**: Detect and use OCR fallback for scanned/image-based PDFs
- [x] **PARSE-04**: Normalize extracted text to common format (Markdown/TextBlocks)
- [x] **PARSE-05**: Handle font encoding issues gracefully

### Vocabulary Extraction

- [x] **EXTRACT-01**: Identify fantasy-relevant candidate words and phrases
- [x] **EXTRACT-02**: Extract nouns, verbs, and adjectives
- [x] **EXTRACT-03**: Extract multi-word expressions (2-4 words)

### Classification

- [x] **CLASS-01**: Classify terms with full schema (id, text, genre, intent, pos, axes, tags, category, canonical, mood, energy, source)
- [x] **CLASS-02**: Validate output against Pydantic schema
- [x] **CLASS-03**: Implement rate limiting for Claude API
- [x] **CLASS-04**: Use Batch API for cost-efficient processing
- [x] **CLASS-05**: Implement prompt caching to reduce token usage

### Output

- [x] **OUTPUT-01**: Generate one JSON file per source document
- [x] **OUTPUT-02**: Consolidate per-document JSONs into master vocabulary
- [x] **OUTPUT-03**: Deduplicate entries and link variants to canonical forms
- [x] **OUTPUT-04**: Support incremental updates without full reprocessing

### IP Review

- [x] **IP-01**: Flag terms that may be IP-encumbered
- [x] **IP-02**: Support configurable blocklist of known IP terms
- [x] **IP-03**: Generate review queue output for human review

### Batch Processing

- [x] **BATCH-01**: Process all documents in a specified folder
- [x] **BATCH-02**: Display progress (documents completed/remaining)
- [x] **BATCH-03**: Resume processing after interruption
- [x] **BATCH-04**: Process multiple documents in parallel

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Document Parsing

- **PARSE-06**: Extract text content from DOCX files
- **PARSE-07**: Layout-aware extraction preserving tables and stat blocks

### IP Review

- **IP-04**: Suggest generic replacement terms for flagged IP

### Batch Processing

- **BATCH-05**: Detailed error reporting with per-document diagnostics

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| GUI/web interface | CLI scripts sufficient for batch processing workflow |
| Real-time/streaming processing | Batch processing adequate for dozens of documents |
| Local LLM inference | Claude API via Max subscription handles classification; CPU-only machine |
| Non-fantasy themes (Sci-Fi, Horror) | Fantasy first; theme expansion is future work |
| Custom NER model training | Claude handles classification; avoid infrastructure complexity |
| Automatic IP term replacement | Legal risk; human review required for IP decisions |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARSE-01 | Phase 1 | Complete |
| PARSE-02 | Phase 1 | Complete |
| PARSE-03 | Phase 1 | Complete |
| PARSE-04 | Phase 1 | Complete |
| PARSE-05 | Phase 1 | Complete |
| EXTRACT-01 | Phase 2 | Complete |
| EXTRACT-02 | Phase 2 | Complete |
| EXTRACT-03 | Phase 2 | Complete |
| CLASS-01 | Phase 2 | Complete |
| CLASS-02 | Phase 2 | Complete |
| CLASS-03 | Phase 2 | Complete |
| CLASS-04 | Phase 2 | Complete |
| CLASS-05 | Phase 2 | Complete |
| OUTPUT-01 | Phase 3 | Complete |
| OUTPUT-02 | Phase 3 | Complete |
| OUTPUT-03 | Phase 3 | Complete |
| OUTPUT-04 | Phase 3 | Complete |
| IP-01 | Phase 3 | Complete |
| IP-02 | Phase 3 | Complete |
| IP-03 | Phase 3 | Complete |
| BATCH-01 | Phase 4 | Complete |
| BATCH-02 | Phase 4 | Complete |
| BATCH-03 | Phase 4 | Complete |
| BATCH-04 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-02-03*
*Last updated: 2026-02-04 - v1 milestone complete (all 24 requirements)*
