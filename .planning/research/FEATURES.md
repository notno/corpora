# Feature Landscape: Vocabulary Extraction Pipeline

**Domain:** Document processing and vocabulary extraction for RPG sourcebooks
**Researched:** 2026-02-03
**Overall Confidence:** MEDIUM-HIGH (verified via multiple sources, domain-specific fantasy NER research found)

---

## Table Stakes

Features users expect. Missing = pipeline feels incomplete or unusable.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Multi-format document parsing** | Core input requirement - PDFs, EPUBs, DOCX are standard sourcebook formats | Medium | None | Use PyMuPDF (handles PDF/EPUB/MOBI), python-docx for DOCX. Separate native text extraction from OCR path |
| **Native text extraction** | Digital PDFs/EPUBs have embedded text; OCR degrades quality (~95% vs 100%) | Low | Document parsing | Always prefer native extraction; fall back to OCR only for scanned documents |
| **OCR fallback for scanned documents** | Some sourcebooks are scanned images | Medium | Document parsing | OCRmyPDF or pytesseract; adds text layer while preserving layout |
| **Part-of-speech tagging** | Required to identify nouns, verbs, adjectives per spec | Low | Text extraction | SpaCy provides fast, accurate POS tagging out of the box |
| **Basic noun/verb/adjective extraction** | Core vocabulary requirement in spec | Low | POS tagging | Filter tokens by POS tags |
| **Multi-word expression detection** | "Fire giant", "magic missile" are single vocabulary items | Medium | POS tagging | Use noun-phrase chunking patterns (adj-noun, noun-noun) or SpaCy noun chunks |
| **Lemmatization / canonical form** | "Dragons" and "dragon" should consolidate to single entry | Low | POS tagging | SpaCy lemmatizer; essential for deduplication |
| **Structured JSON output** | Spec requires per-document JSON and master vocabulary | Low | All extraction | Define Pydantic models, use JSON Schema validation |
| **Document-level output** | One JSON per source document | Low | JSON output | Natural checkpoint for pipeline resumption |
| **Master vocabulary consolidation** | Combine all documents into deduplicated master list | Medium | Document-level output | Requires canonical form matching and merge logic |
| **Deduplication by canonical form** | "Fire giants" from multiple docs = one entry | Medium | Lemmatization, consolidation | Match on lemmatized form; track source documents |
| **Error handling and logging** | Know what failed and why | Low | None | Structured logging with document/page context |
| **Progress tracking** | Large sourcebooks take time; users need visibility | Low | None | Progress bars, status files |
| **Idempotent processing** | Re-running pipeline should not corrupt data | Medium | All stages | Checkpointing, upsert logic, idempotency keys |

---

## Differentiators

Features that set the pipeline apart. Not universally expected, but provide competitive advantage for this use case.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **LLM-powered rich classification** | Genre, intent, mood, axes, tags, category - far beyond keyword matching | High | Text extraction, Claude API | Core differentiator. Zero-shot classification via Claude. Structured output with JSON Schema validation |
| **Fantasy domain NER** | Standard NER misses "Tiamat", "Shadowfell", "Mind Flayer" | Medium | POS tagging | Research shows off-the-shelf NER fails on fantasy text. Flair/Trankit/SpaCy perform best but still need domain hints |
| **IP-encumbered term flagging** | Legal protection - trademark/copyright detection | High | Vocabulary extraction | Flag terms like "Beholder", "Illithid" for manual review. Phonetic + semantic similarity detection |
| **Batch API processing** | 50% cost savings on Claude API calls | Medium | LLM classification | OpenAI/Anthropic batch APIs for non-urgent processing; 24hr turnaround acceptable |
| **Prompt caching** | Up to 90% cost reduction for repeated context | Medium | LLM classification | Cache system prompts and common prefixes |
| **Rate limit management** | Prevent API failures at scale | Medium | LLM classification | Exponential backoff, request queuing, token budget tracking |
| **Cost estimation before run** | Know API costs before committing | Low | Token counting | Count tokens upfront; estimate based on current pricing |
| **Resumable pipeline** | Continue from failure point, not restart | Medium | Checkpointing | Store processing state per document/page; resume from last checkpoint |
| **Source document provenance** | Track which documents contributed each term | Low | Document processing | Essential for IP review and quality assessment |
| **Confidence scoring** | LLM classification confidence per term | Low | LLM classification | Request confidence scores in prompts; filter low-confidence for review |
| **Multi-word phrase boundary detection** | "Potion of healing" vs "potion" + "of" + "healing" | High | NLP pipeline | Collocation analysis, PMI scores, noun phrase patterns |
| **Human review queue** | Flag uncertain classifications for manual review | Medium | All extraction | UI/export for reviewing flagged terms (IP, low confidence, ambiguous) |
| **Incremental vocabulary updates** | Add new documents without full reprocessing | Medium | Master consolidation | Merge new extractions into existing master; track versions |

---

## Anti-Features

Features to explicitly NOT build. Common mistakes or scope creep in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Custom NER model training** | Requires labeled data, training infrastructure, ongoing maintenance; diminishing returns for vocabulary extraction | Use off-the-shelf NER (SpaCy/Flair) + LLM classification. LLM handles domain knowledge without training |
| **Real-time processing** | Sourcebook processing is batch workflow; real-time adds complexity for no value | Batch processing with progress tracking. Accept multi-minute/hour processing times |
| **OCR for all documents** | Degrades quality from 100% to ~95% for native-text documents | Detect document type; native extraction first, OCR only for scanned |
| **Full document translation** | Scope creep; most RPG sourcebooks are English | Handle English only initially; add language detection as gate if needed later |
| **Semantic search/RAG** | Different product - vocabulary extraction is discrete items, not document retrieval | Output vocabulary JSON; let downstream systems build search if needed |
| **GUI/web interface** | Over-engineering for a pipeline tool; adds maintenance burden | CLI-first with clear JSON output. GUI can be separate project consuming output |
| **Fine-tuned LLM** | Expensive, requires training data, version management | Use Claude API with carefully crafted prompts; structured outputs handle consistency |
| **Complex taxonomy management** | Dynamic taxonomies add cognitive load and maintenance | Fixed taxonomy defined upfront (genre, intent, mood, etc.); extend only when evidence demands |
| **Automatic copyright determination** | Legal liability; can't automatically decide what's copyrighted | Flag for human review only; never auto-approve or auto-reject |
| **TF-IDF-based term importance** | Obsolete for this use case; LLM classification supersedes statistical importance | Use LLM to classify relevance/importance directly; skip TF-IDF entirely |
| **Word embeddings/Word2Vec** | Over-engineering for vocabulary extraction; useful for similarity search not classification | LLM handles semantic understanding; embeddings add complexity without clear value |

---

## Feature Dependencies

```
Document Parsing (PDF/EPUB/DOCX)
    |
    +---> Native Text Extraction
    |         |
    +---> OCR Fallback (scanned docs only)
              |
              v
         Raw Text
              |
              v
         POS Tagging (SpaCy)
              |
              +---> Basic Token Extraction (nouns, verbs, adj)
              |
              +---> Noun Phrase Chunking (multi-word expressions)
              |
              +---> Lemmatization (canonical form)
                        |
                        v
                   Candidate Terms
                        |
                        v
                   LLM Classification (Claude API)
                        |
                        +---> Rate Limiting
                        +---> Batch Processing
                        +---> Prompt Caching
                        +---> JSON Schema Validation
                        |
                        v
                   Classified Terms
                        |
                        +---> IP Flag Detection
                        +---> Confidence Scoring
                        |
                        v
                   Document JSON Output
                        |
                        v
                   Master Vocabulary Consolidation
                        |
                        +---> Deduplication (by canonical form)
                        +---> Source Provenance Tracking
                        +---> Human Review Queue (flagged items)
                        |
                        v
                   Master Vocabulary JSON
```

---

## MVP Recommendation

For MVP, prioritize in this order:

### Phase 1: Core Extraction (Table Stakes)
1. **PDF parsing with native text extraction** - Use PyMuPDF
2. **POS tagging and basic token extraction** - SpaCy
3. **Multi-word expression detection** - SpaCy noun chunks
4. **Lemmatization** - SpaCy lemmatizer
5. **Document-level JSON output** - Pydantic models
6. **Basic error handling and logging**

### Phase 2: LLM Classification (Core Differentiator)
1. **Claude API integration for classification**
2. **Structured output with JSON Schema validation**
3. **Rate limiting and basic retry logic**
4. **Per-term confidence scoring**

### Phase 3: Consolidation & IP Protection
1. **Master vocabulary consolidation**
2. **Deduplication by canonical form**
3. **IP-encumbered term flagging** (keyword list first, similarity later)
4. **Source provenance tracking**

### Phase 4: Scale & Polish
1. **Batch API processing for cost savings**
2. **Prompt caching**
3. **Resumable pipeline with checkpointing**
4. **EPUB and DOCX support**
5. **OCR fallback for scanned documents**

### Defer to Post-MVP
- **Human review UI**: Output flagged terms to JSON; build UI separately if needed
- **Incremental updates**: Full reprocessing acceptable initially; optimize when library grows
- **Advanced IP similarity**: Start with keyword list; add phonetic/semantic matching if needed

---

## Complexity Estimates

| Complexity | Definition | Examples |
|------------|------------|----------|
| **Low** | < 1 day, well-understood patterns, library support | POS tagging, lemmatization, JSON output, logging |
| **Medium** | 1-3 days, some integration complexity, edge cases | Multi-format parsing, rate limiting, deduplication, checkpointing |
| **High** | 3+ days, novel problem space, external dependencies | LLM classification prompt engineering, IP detection, multi-word boundary detection |

---

## Sources

### Document Processing
- [Best Python PDF to Text Parser Libraries: A 2026 Evaluation](https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/)
- [PDF Data Extraction Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)
- [Document Parsing vs. OCR](https://blog.filestack.com/document-parsing-vs-ocr/)
- [OCR Benchmark: Text Extraction Accuracy 2026](https://research.aimultiple.com/ocr-accuracy/)

### NLP Pipeline
- [NLP Pipeline: Key Steps to Process Text Data](https://airbyte.com/data-engineering-resources/natural-language-processing-pipeline)
- [Multiword Expression Processing: A Survey](https://direct.mit.edu/coli/article/43/4/837/1581/Multiword-Expression-Processing-A-Survey)
- [Stemming and Lemmatization](https://nlp.stanford.edu/IR-book/html/htmledition/stemming-and-lemmatization-1.html)

### Fantasy Domain NER
- [Comparative Analysis of Named Entity Recognition in the Dungeons and Dragons Domain](https://arxiv.org/html/2309.17171)
- [Fine Tuning Named Entity Extraction Models for the Fantasy Domain](https://arxiv.org/abs/2402.10662)
- [Evaluating NER Tools for Extracting Social Networks from Novels](https://pmc.ncbi.nlm.nih.gov/articles/PMC7924459/)

### LLM Classification
- [The Guide to Structured Outputs and Function Calling with LLMs](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms)
- [Structured Outputs Guide - OpenAI](https://platform.openai.com/docs/guides/structured-outputs)
- [Text Classification with LLMs](https://www.helicone.ai/blog/text-classification-with-llms)

### Cost Optimization
- [Taming the Beast: Cost Optimization Strategies for LLM API Calls](https://medium.com/@ajayverma23/taming-the-beast-cost-optimization-strategies-for-llm-api-calls-in-production-11f16dbe2c39)
- [Rate Limits for LLM Providers](https://www.requesty.ai/blog/rate-limits-for-llm-providers-openai-anthropic-and-deepseek)
- [Reduce LLM Costs: Token Optimization Strategies](https://www.glukhov.org/post/2025/11/cost-effective-llm-applications/)

### IP Detection
- [The Role of Natural Language Processing in Trademark Searches](https://patentpc.com/blog/the-role-of-natural-language-processing-in-trademark-searches)
- [How AI-Powered Trademark Search Tools Work](https://patentpc.com/blog/how-ai-powered-trademark-search-tools-work-a-deep-dive)

### Pipeline Reliability
- [Understanding Idempotency in Data Pipelines](https://airbyte.com/data-engineering-resources/idempotency-in-data-pipelines)
- [Mastering Data Pipeline Error Handling](https://www.numberanalytics.com/blog/mastering-data-pipeline-error-handling)
- [Error Handling in Distributed Systems](https://temporal.io/blog/error-handling-in-distributed-systems)

---

## Quality Gate Checklist

- [x] Categories are clear (table stakes vs differentiators vs anti-features)
- [x] Complexity noted for each feature (Low/Medium/High)
- [x] Dependencies between features identified (dependency diagram included)
