# Project Research Summary

**Project:** RPG Sourcebook Vocabulary Extraction Pipeline
**Domain:** Document processing / NLP / LLM-powered classification
**Researched:** 2026-02-03
**Confidence:** HIGH

## Executive Summary

This is a document processing pipeline that extracts and classifies vocabulary from RPG sourcebooks (PDF, EPUB, DOCX formats). Expert builders approach this as a multi-stage pipeline: document parsing to normalized text, vocabulary extraction via NLP preprocessing, LLM-powered classification for rich metadata, and consolidation with IP review. The key differentiator is using Claude API for zero-shot classification of fantasy-domain vocabulary, which standard NER models consistently fail on.

The recommended approach is a staged pipeline with checkpointing: (1) PDF/EPUB/DOCX parsing using format-specific libraries to Markdown, (2) Claude API integration via instructor for structured vocabulary extraction, (3) IP review and flagging before output, (4) consolidation with deduplication by canonical form. Use PyMuPDF4LLM for PDF extraction (purpose-built for LLM consumption), the Message Batches API for 50% cost reduction, and prompt caching to minimize token usage. Start with PDF-only processing and expand to other formats once the core pipeline is proven.

The critical risks are: (1) garbled PDF text from font encoding issues requiring OCR fallback, (2) Claude API rate limits and exploding token costs without batching/caching, (3) fantasy NER failures where standard models miss invented proper nouns, (4) IP-encumbered terms contaminating output without review gates, and (5) JSON schema drift from LLM outputs. Mitigation strategies include font fallback detection with selective OCR, upfront token budgeting with Batches API, few-shot prompting with fantasy examples, IP blocklists and manual review queues, and Pydantic validation with retry loops.

## Key Findings

### Recommended Stack

The stack is optimized for CPU-only processing with Claude API integration. PyMuPDF4LLM is the centerpiece for PDF extraction—it's specifically designed for LLM consumption and outputs clean Markdown with preserved document structure. The instructor library wraps the anthropic SDK to return validated Pydantic models, eliminating manual JSON parsing and enabling automatic retry on validation failures.

**Core technologies:**
- **pymupdf4llm (0.2.9)**: PDF text extraction — purpose-built for LLM pipelines, outputs Markdown with structure, 4x faster than pdfplumber
- **anthropic (0.77.1)**: Claude API client — official SDK with async, streaming, and Message Batches API support
- **instructor (1.14.5)**: Structured output validation — patches anthropic client for automatic Pydantic model validation and retry
- **pydantic (2.12.5)**: Data models and validation — define vocabulary schemas, automatic JSON serialization
- **python-docx (1.2.0)**: DOCX parsing — industry standard, actively maintained
- **EbookLib (0.20)**: EPUB parsing — only viable EPUB library for Python, handles EPUB2/3
- **beautifulsoup4 (4.14.3)**: HTML parsing — required for extracting text from EPUB content

**Optional (defer decision):**
- **spacy (3.8.11)**: NLP preprocessing — only add if Claude struggles with noisy input; may not be needed if Claude handles all classification

**Python version:** 3.11 or 3.12 (minimum 3.10 due to pymupdf4llm constraint)

### Expected Features

Research identified clear boundaries between table stakes, differentiators, and anti-features for vocabulary extraction pipelines.

**Must have (table stakes):**
- Multi-format document parsing (PDF, EPUB, DOCX) with native text extraction
- OCR fallback for scanned documents (not blanket OCR—degrade quality)
- Part-of-speech tagging for noun/verb/adjective extraction
- Multi-word expression detection ("fire giant" as single term)
- Lemmatization for canonical form deduplication
- Structured JSON output (per-document and master vocabulary)
- Document-level provenance tracking
- Error handling and progress tracking
- Idempotent processing for safe retries

**Should have (competitive differentiators):**
- LLM-powered rich classification (genre, intent, mood, category) via Claude
- Fantasy domain NER (standard models fail on invented proper nouns like "Tiamat")
- IP-encumbered term flagging for legal protection
- Batch API processing (50% cost savings on Claude calls)
- Prompt caching (up to 90% cost reduction for repeated context)
- Rate limit management with exponential backoff
- Confidence scoring per term with human review queue for low-confidence items
- Resumable pipeline with checkpointing
- Source document provenance for IP review

**Defer (v2+ or skip):**
- Custom NER model training (use off-the-shelf + LLM instead)
- Real-time processing (batch workflow is appropriate)
- GUI/web interface (CLI-first, JSON output for downstream tools)
- Fine-tuned LLM (careful prompting is sufficient)
- Semantic search/RAG features (different product)
- TF-IDF or word embeddings (obsolete with LLM classification)

### Architecture Approach

The architecture follows a staged pipeline pattern with persistent checkpoints at each stage boundary. Each component has a single responsibility and communicates through well-defined data structures. The adapter pattern isolates format-specific parsing logic, allowing uniform handling downstream.

**Major components:**
1. **File Discovery + Ingestion Queue** — scan folders, validate file types, build persistent work queue with status tracking
2. **Parser Router + Format Adapters** — route documents to PDF/EPUB/DOCX parsers, normalize to common TextBlock structure
3. **Extraction Engine + Rate Limiter** — orchestrate Claude API calls with rate limit management, chunk documents for context windows
4. **Vocabulary Classifier** — classify/categorize extracted terms via Claude with structured output validation
5. **IP Reviewer** — flag/sanitize potential trademark/copyright issues before output
6. **Consolidation Engine** — merge per-document JSONs, deduplicate by canonical form, build master vocabulary

**Critical patterns to follow:**
- **Checkpointing:** Save progress after each stage (parsing complete, extraction complete, classification complete) to enable recovery from failures
- **Rate-limited API client:** Wrap Claude calls in token bucket limiter respecting RPM/TPM limits, exponential backoff on 429 errors
- **Adapter pattern for parsers:** Common DocumentParser interface for all formats, uniform TextBlock output for downstream processing
- **Idempotent processing:** Each stage produces same output if run multiple times, atomic writes, skip-if-complete logic

**Data flow:** Documents → Format-specific parser → Normalized TextBlocks → Chunking → Claude API (rate-limited) → Raw vocabulary → Classification → IP review → Per-doc JSON → Consolidation → Master JSON

### Critical Pitfalls

Based on academic research (including fantasy NER studies) and production document processing best practices, five pitfalls stand out as pipeline-breaking.

1. **PDF text extraction produces garbled text** — Fantasy sourcebooks use decorative fonts and custom glyphs (dice symbols, damage types) which often lack ToUnicode mappings. Extraction returns U+FFFD replacement characters or empty strings. **Prevention:** Test extraction on samples first, detect U+FFFD in output, implement OCR fallback only for problematic pages (not blanket OCR), use PyMuPDF over pypdf for better font handling.

2. **Fantasy NER fails on invented vocabulary** — Standard NLP models and even LLMs misclassify terms like "Drizzt", "Shadowfell", "Mind Flayer" because training data lacks fantasy domain examples. Academic research confirms off-the-shelf NER performs poorly on D&D text. **Prevention:** Few-shot prompting with fantasy examples, explicit taxonomy in prompts (spell/creature/location/character/item/mechanic), classify with context windows not isolated terms, confidence thresholds with human review queue.

3. **Claude API rate limits and token costs explode** — RPG sourcebooks are text-dense (200+ pages, 100k words). Sending full pages without caching hits rate limits and costs can be 5-10x budget. **Prevention:** Use Message Batches API (50% cost reduction), implement prompt caching for system prompts, pre-segment documents to extract only vocabulary-rich sections, calculate token budgets upfront before processing, exponential backoff with monitoring at 80% threshold.

4. **JSON schema drift from LLM outputs** — LLMs drift when generating JSON, producing syntactically valid but schema-non-conformant output (missing fields, wrong types, extra conversational wrapper text). **Prevention:** Define JSON Schema explicitly in prompts, validate every response with Pydantic models, implement retry loop on validation failure, keep schema flat (not deeply nested), strip conversational wrappers, log violations to track which prompts cause drift.

5. **IP/trademark terms contaminate output** — RPG sourcebooks contain both generic game terms and protected IP (e.g., "Beholder" and "Mind Flayer" are WotC trademarks). Automated extraction has no legal awareness. **Prevention:** Build IP blocklist upfront from OGL Product Identity declarations, tag source publisher for each term, add ip_risk field to schema, process SRD/OGL content first, require human review gate before finalization, document source page numbers for traceability.

## Implications for Roadmap

Based on research, the natural phase structure follows both dependency order (what must exist before what) and risk mitigation (prove core value before expanding scope). The architecture research identified a clear build order; the features research separated table stakes from differentiators; the pitfalls research highlighted where to invest in prevention.

### Phase 1: Core Document Parsing (Foundation)
**Rationale:** Must have working text extraction before any downstream processing. PDF is the dominant RPG sourcebook format—prove extraction works before expanding to EPUB/DOCX. This phase addresses the most critical pitfall (garbled text extraction) upfront.

**Delivers:**
- PDF parsing with pymupdf4llm
- Font fallback detection and OCR hybrid approach
- Text normalization (Unicode, hyphenation, multi-column layout)
- TextBlock data structure for downstream processing
- Basic error handling and logging

**Addresses (from FEATURES.md):**
- Multi-format document parsing (PDF first)
- Native text extraction with OCR fallback
- Error handling and logging

**Avoids (from PITFALLS.md):**
- Pitfall #1: Garbled PDF text extraction
- Pitfall #6: Multi-column layout destroys reading order
- Pitfall #9: Hyphenated words split incorrectly

**Research flag:** LOW (PyMuPDF4LLM is well-documented, standard patterns)

---

### Phase 2: LLM Classification Pipeline (Core Value)
**Rationale:** This is the differentiator—Claude API for zero-shot fantasy vocabulary classification. Proves the core value proposition before investing in deduplication/consolidation complexity. Addresses rate limits and cost explosions early.

**Delivers:**
- Claude API integration via instructor
- Rate limiter with exponential backoff
- Prompt templates with few-shot fantasy examples
- Pydantic models for vocabulary schema
- JSON validation with retry loops
- Per-document JSON output
- Checkpointing for resume capability

**Addresses (from FEATURES.md):**
- LLM-powered rich classification (genre, intent, mood, category)
- Structured JSON output
- Confidence scoring per term
- Document-level provenance tracking
- Idempotent processing
- Resumable pipeline with checkpointing

**Uses (from STACK.md):**
- anthropic SDK
- instructor for structured outputs
- pydantic for validation
- Message Batches API for cost savings

**Avoids (from PITFALLS.md):**
- Pitfall #2: Fantasy NER failures
- Pitfall #3: Rate limits and token cost explosions
- Pitfall #4: JSON schema drift
- Pitfall #10: No resume capability

**Research flag:** MEDIUM (Prompt engineering for fantasy domain will need iteration; consider `/gsd:research-phase` if classification quality is poor)

---

### Phase 3: IP Review and Consolidation (Protection)
**Rationale:** Can't ship vocabulary without IP review—this is legally critical for RPG content. Consolidation depends on having multiple per-document outputs from Phase 2. Deduplication logic is complex (fuzzy matching, conflict resolution) so defer until core pipeline works.

**Delivers:**
- IP blocklist from OGL Product Identity
- IP review flagging in schema
- Human review queue output
- Master vocabulary consolidation
- Deduplication by canonical form with conflict resolution
- Source provenance tracking across documents

**Addresses (from FEATURES.md):**
- IP-encumbered term flagging
- Master vocabulary consolidation
- Deduplication by canonical form
- Human review queue

**Implements (from ARCHITECTURE.md):**
- IP Reviewer component
- Consolidation Engine component

**Avoids (from PITFALLS.md):**
- Pitfall #5: IP contamination without review
- Pitfall #8: Vocabulary deduplication creates merge conflicts

**Research flag:** MEDIUM (IP blocklist requires legal research into OGL/SRD boundaries; may need `/gsd:research-phase` for specific game systems)

---

### Phase 4: Multi-Format Support (Scale)
**Rationale:** Core pipeline proven with PDF. Expanding to EPUB/DOCX is lower risk since parser adapter pattern is already defined. EPUB complexity (publisher variance) is moderate but isolated to parsing stage.

**Delivers:**
- EPUB parser with EbookLib + BeautifulSoup
- DOCX parser with python-docx
- Format detection and routing
- Preservation of formatting cues from DOCX

**Addresses (from FEATURES.md):**
- Multi-format document parsing (complete coverage)

**Uses (from STACK.md):**
- EbookLib + beautifulsoup4 for EPUB
- python-docx for DOCX

**Avoids (from PITFALLS.md):**
- Pitfall #7: EPUB structure variance across publishers
- Pitfall #11: DOCX loses formatting cues

**Research flag:** LOW (Libraries are well-documented, adapter pattern is standard)

---

### Phase 5: Cost Optimization and Polish (Production)
**Rationale:** Core functionality complete. Now optimize for production use—prompt caching, batch processing, better progress tracking. These are "nice to have" improvements that don't block core value delivery.

**Delivers:**
- Prompt caching implementation (90% token cost reduction)
- Batch API integration for background processing
- Enhanced progress tracking (tqdm, status files)
- Cost estimation before processing
- Empty page filtering (skip artwork-only pages)

**Addresses (from FEATURES.md):**
- Prompt caching
- Batch API processing
- Progress tracking
- Cost estimation

**Avoids (from PITFALLS.md):**
- Pitfall #13: Empty/artwork pages waste tokens

**Research flag:** LOW (Anthropic docs cover Batches API and prompt caching well)

---

### Phase Ordering Rationale

**Dependency chain:**
- Phase 2 depends on Phase 1 (needs parsed text to classify)
- Phase 3 depends on Phase 2 (needs per-doc outputs to consolidate)
- Phase 4 can start after Phase 2 (parallel to Phase 3 if needed)
- Phase 5 requires complete pipeline (optimization comes last)

**Risk mitigation:**
- Phase 1 addresses the most critical pitfall (garbled extraction) immediately
- Phase 2 proves core value (LLM classification) before expanding scope
- Phase 3 handles legal risk (IP review) before shipping any output
- Phase 4 and 5 are polish—pipeline is functional without them

**Architecture alignment:**
- Follows build order from ARCHITECTURE.md (infrastructure → parsing → API → extraction → output)
- Each phase delivers a complete component from the component boundary table
- Adapter pattern in Phase 1 makes Phase 4 expansion straightforward

**Feature prioritization:**
- All "table stakes" features covered by Phase 3
- "Differentiators" (LLM classification, IP review) in Phases 2-3
- "Defer" items (GUI, fine-tuning) correctly omitted from roadmap

### Research Flags

**Phases likely needing `/gsd:research-phase` during planning:**
- **Phase 2 (LLM Classification):** If initial prompt engineering produces poor classification quality on fantasy vocabulary, research prompt patterns specifically for fantasy NER and domain-specific classification. Academic papers exist but may need deeper study.
- **Phase 3 (IP Review):** If processing sourcebooks from specific game systems (D&D 5e, Pathfinder, etc.), research that system's OGL/SRD to build accurate IP blocklist. Legal boundary between generic and protected terms varies by publisher.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Document Parsing):** PyMuPDF4LLM, python-docx, EbookLib all have comprehensive documentation. Layout detection and OCR fallback are well-established patterns.
- **Phase 4 (Multi-Format Support):** EPUB and DOCX parsing libraries are mature with clear examples.
- **Phase 5 (Cost Optimization):** Anthropic docs cover Batches API and prompt caching thoroughly.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified on PyPI with recent releases. pymupdf4llm specifically designed for this use case. Anthropic SDK is official. instructor has proven Anthropic integration. |
| Features | MEDIUM-HIGH | Table stakes well-established via multiple document processing sources. Fantasy NER challenges confirmed by academic research (arXiv papers on D&D NER). Differentiators grounded in LLM best practices. |
| Architecture | MEDIUM | Pipeline patterns and component boundaries are standard (AWS/Azure doc processing architectures). Rate limiting and checkpointing are proven patterns. Specific application (RPG sourcebooks) is novel but components are not. |
| Pitfalls | MEDIUM-HIGH | PDF extraction issues extensively documented. Fantasy NER failures confirmed by academic study. Claude rate limits and JSON drift are known issues with documented solutions. IP concerns specific to RPG domain but legal research exists. |

**Overall confidence:** HIGH

The core technology choices (PyMuPDF4LLM, instructor, anthropic SDK) are well-validated. The pipeline architecture follows established patterns from AWS/Azure document processing examples. The fantasy NER challenge is the most novel aspect, but academic research directly addresses it and confirms Claude-style LLMs outperform traditional NER for this domain.

### Gaps to Address

**spaCy necessity:** Research flags spaCy as "optional"—may not be needed if Claude handles all classification. **Decision point:** Start without spaCy in Phase 2. If Claude produces too many false positives or struggles with noisy input, add spaCy for POS tagging pre-filter in a Phase 2.5 iteration. Don't commit to spaCy upfront.

**Prompt engineering for fantasy domain:** While research confirms LLMs outperform traditional NER, specific prompt patterns for fantasy vocabulary aren't well-documented. **Plan:** Budget iteration time in Phase 2 for prompt testing. Use few-shot examples from D&D SRD (legally clear content). If quality is poor after initial attempts, trigger `/gsd:research-phase` for fantasy-specific classification research.

**IP blocklist completeness:** Research identified the need for IP review but didn't produce a comprehensive blocklist. OGL Product Identity varies by publisher and edition. **Plan:** Phase 3 should start with D&D 5e SRD (most documented OGL). If processing other systems (Pathfinder, OSR games), research that system's license before processing. Consider manual review queue initially rather than fully automated IP filtering.

**OCR quality vs. cost tradeoff:** Research recommends OCR fallback but doesn't quantify when it's worth the quality degradation (95% accuracy vs. 100% native text). **Plan:** Phase 1 should include OCR threshold testing. Measure text extraction quality across sample documents, flag only pages with >10% replacement characters for OCR. Track OCR'd pages separately in provenance for downstream quality assessment.

**Token cost estimation:** Research provides per-book cost estimates (~$0.35 for 200-page sourcebook with Batches API) but these are based on assumptions about prompt size and vocabulary density. **Plan:** Phase 2 should include cost tracking and validation against estimates. If actual costs exceed 2x estimates, investigate prompt optimization or more aggressive pre-filtering before API calls.

## Sources

### Primary (HIGH confidence)
- **PyPI package verification** — All versions and release dates confirmed via PyPI (pymupdf4llm 0.2.9, anthropic 0.77.1, instructor 1.14.5, python-docx 1.2.0, EbookLib 0.20)
- **Official documentation** — PyMuPDF4LLM docs, Anthropic Python SDK, Instructor docs, spaCy models documentation
- **Academic research** — [Comparative Analysis of Named Entity Recognition in the Dungeons and Dragons Domain](https://arxiv.org/abs/2309.17171) — directly addresses fantasy NER failures with quantitative evaluation
- **AWS/Azure architecture blogs** — Building Scalable Document Pre-Processing Pipeline (AWS), AI Document Processing Pipeline (Microsoft) — established patterns for document processing architectures

### Secondary (MEDIUM confidence)
- **PDF extraction benchmarks** — Procycons PDF Data Extraction Benchmark 2025, Unstract Python PDF evaluation — comparative performance data for PyMuPDF vs. alternatives
- **LLM cost optimization** — Taming the Beast: Cost Optimization Strategies for LLM API Calls (Medium), Rate Limits for LLM Providers (Requesty.ai) — battle-tested patterns for production LLM usage
- **NLP pipeline patterns** — Multiword Expression Processing Survey (MIT), spaCy vs NLTK comparison (DSStream) — established techniques for tokenization, POS tagging, phrase extraction
- **IP/legal concerns** — Copyrightability of RPG Stat Blocks (GSL blog), Intellectual Property for Gamers (Cannibal Halfling) — OGL and Product Identity boundaries for D&D content

### Tertiary (LOW confidence, needs validation)
- **Cost estimates** — Per-sourcebook token costs based on assumptions about page density and vocabulary extraction rate. Need validation with real documents in Phase 2.
- **spaCy necessity** — Multiple sources recommend spaCy for NLP preprocessing but disagree on whether it's needed with modern LLMs. Marked as "optional" pending Phase 2 testing.

---

**Research completed:** 2026-02-03
**Ready for roadmap:** Yes

All four research dimensions (STACK, FEATURES, ARCHITECTURE, PITFALLS) completed with HIGH overall confidence. Phase structure clearly derived from research findings. Research flags identified for Phases 2 and 3. No blocking gaps—pipeline is feasible with known technology and established patterns.
