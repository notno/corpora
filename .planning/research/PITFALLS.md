# Domain Pitfalls: Vocabulary Extraction from RPG Sourcebooks

**Domain:** Document processing and NLP vocabulary extraction for fantasy RPG sourcebooks
**Researched:** 2026-02-03
**Confidence:** MEDIUM-HIGH (based on verified research + domain-specific academic papers)

---

## Critical Pitfalls

Mistakes that cause rewrites, pipeline failures, or unusable output.

---

### Pitfall 1: PDF Text Extraction Produces Garbled or Missing Text

**What goes wrong:** PDF extraction returns replacement characters (U+FFFD / `?`), garbled text, or empty strings instead of actual content. Fantasy sourcebooks often use decorative fonts, custom glyphs for game symbols (dice, damage types), and embedded artwork with text overlays.

**Why it happens:**
- PDFs store visual layout, not semantic text structure
- Missing ToUnicode mappings (CMAP) in embedded fonts
- Font subsetting removes character mapping tables
- Decorative/custom fonts used for headers and special terms
- RPG sourcebooks frequently use stylized fonts for flavor text

**Consequences:**
- Fantasy vocabulary (the exact content you need) is lost
- Pipeline produces unusable JSON with corrupted entries
- Manual intervention required for every problematic document

**Warning signs:**
- Unicode replacement character (U+FFFD) appearing in extracted text
- Output contains sequences like `???` or empty strings where text should be
- Extracted word count significantly lower than expected
- Chinese/symbol characters appearing in English documents

**Prevention:**
1. **Test extraction on representative samples first** - before building the full pipeline, extract 5-10 pages from each sourcebook type and validate output
2. **Implement font fallback detection** - check for U+FFFD in output and flag files needing OCR
3. **Use PyMuPDF over pypdf** - research shows PyMuPDF handles font encoding issues better
4. **OCR fallback for problematic pages** - use Tesseract only where needed, not blanket OCR (expensive)
5. **Normalize Unicode on extraction** - apply character translation to standardize spaces, hyphens, quotes

**Detection code pattern:**
```python
if '\ufffd' in extracted_text or extracted_text.strip() == '':
    flag_for_ocr_fallback(page)
```

**Phase to address:** Phase 1 (Document Parsing) - must be solved before any downstream processing

---

### Pitfall 2: Fantasy Named Entity Recognition Fails on Invented Vocabulary

**What goes wrong:** Standard NLP models and even general-purpose LLMs misclassify fantasy terms, fail to recognize invented proper nouns, or incorrectly categorize domain-specific vocabulary.

**Why it happens:**
- Fantasy literature has invented names with no standard patterns (e.g., "Drizzt", "Tiamat", "Eberron")
- Terms can be ambiguous between categories (is "Fireball" a spell name or a description?)
- Training data doesn't include sufficient fantasy domain examples
- Polysemy - same word has different meanings in fantasy vs. general English ("ranger", "bard", "school")

**Consequences:**
- Vocabulary misclassified (proper nouns tagged as common words)
- Duplicate entries with inconsistent classifications
- IP-sensitive terms mixed with generic vocabulary
- Manual review burden explodes

**Warning signs:**
- Classification confidence scores clustering around 50% (uncertain)
- Same term classified differently across documents
- Common English words being flagged as fantasy-specific
- Obvious proper nouns (character names) not being recognized

**Prevention:**
1. **Provide classification examples in prompts** - few-shot prompting with verified fantasy vocabulary examples
2. **Define explicit taxonomy upfront** - spell, creature, location, character, item, game mechanic, setting term
3. **Use context windows** - classify terms with surrounding sentences, not in isolation
4. **Implement confidence thresholds** - route low-confidence items to human review queue
5. **Build iterative feedback loop** - human corrections feed back into prompt examples

**Phase to address:** Phase 2 (Vocabulary Extraction) - taxonomy must be defined before extraction begins

---

### Pitfall 3: Claude API Rate Limits and Token Costs Explode

**What goes wrong:** Batch processing hits rate limits, causes 429 errors, or token costs far exceed budget. Pipeline stalls or becomes economically unviable.

**Why it happens:**
- Token bucket algorithm means burst strategies don't work
- Sending full pages when only paragraphs needed
- Redundant context in every request (no caching)
- RPG sourcebooks are text-dense - a single book can be 200+ pages
- Multiple passes over same content without caching

**Consequences:**
- Pipeline stalls mid-batch with no graceful recovery
- Token costs 5-10x higher than budgeted
- Processing time measured in days instead of hours
- Incomplete runs with partial data

**Warning signs:**
- Hitting 429 errors within first hour of processing
- Cost estimates showing >$100 for a single sourcebook
- Processing rate declining over time (rate limit backoff)
- Identical system prompts being sent repeatedly

**Prevention:**
1. **Use the Message Batches API** - 50% token cost reduction, designed for this use case
2. **Implement prompt caching** - cache system prompts and repeated context (cached tokens don't count against ITPM limits)
3. **Pre-segment documents** - extract only text sections likely to contain vocabulary, skip artwork-heavy pages
4. **Calculate token budgets upfront** - estimate tokens per document before processing
5. **Implement exponential backoff** - graceful retry with increasing delays
6. **Monitor at 80% threshold** - alert before hitting limits, not after

**Budget estimation pattern:**
```python
estimated_input_tokens = len(document_text) / 4  # rough estimate
cost_per_1k = 0.003  # Claude Haiku for classification
estimated_cost = (estimated_input_tokens / 1000) * cost_per_1k
```

**Phase to address:** Phase 2 (Claude Integration) - must be designed into API wrapper from day one

---

### Pitfall 4: JSON Output Drift and Schema Non-Conformance

**What goes wrong:** Claude produces JSON that is syntactically valid but doesn't match the expected schema, contains extra fields, missing required fields, or inconsistent data types across batches.

**Why it happens:**
- LLMs are prone to "drift" when generating JSON
- Long context causes model to forget schema constraints
- Subtle prompt variations cause different output structures
- No schema enforcement at generation time

**Consequences:**
- Downstream consolidation fails on malformed records
- Data loss when fields are silently missing
- Type errors when aggregating across documents
- Inconsistent vocabulary entries that can't be merged

**Warning signs:**
- JSON parse errors appearing mid-batch
- Fields present in some outputs but not others
- Data types changing (string vs array vs null)
- Extra conversational text wrapping the JSON

**Prevention:**
1. **Define JSON Schema explicitly** - provide schema in every prompt
2. **Use Pydantic validation** - validate every response against schema before storing
3. **Implement retry loop** - if validation fails, retry with explicit correction prompt
4. **Keep schema simple** - flat structures over deeply nested objects
5. **Extract JSON from response** - strip any conversational wrapper text
6. **Log schema violations** - track which documents/prompts cause drift

**Validation pattern:**
```python
from pydantic import BaseModel, ValidationError

class VocabularyEntry(BaseModel):
    term: str
    category: str
    source_document: str
    context: str
    confidence: float

try:
    entry = VocabularyEntry.parse_obj(llm_output)
except ValidationError as e:
    retry_with_correction(prompt, e.errors())
```

**Phase to address:** Phase 2 (Output Structuring) - schema design is prerequisite to extraction

---

### Pitfall 5: IP/Trademark Terms Contaminate Output Without Review

**What goes wrong:** Extracted vocabulary includes trademarked terms, copyrighted character names, or product identity that cannot legally be used, and this isn't discovered until late in the process (or after).

**Why it happens:**
- RPG sourcebooks contain both generic game terms and protected IP
- Trademark vs. generic boundary is not clear from text alone
- "Dungeons & Dragons" terms have complex licensing (OGL, SRD, Product Identity)
- Automated extraction has no legal awareness
- Fantasy vocabulary often sounds generic but is actually trademarked

**Consequences:**
- Legal liability if extracted terms are used commercially
- Entire vocabulary sets must be discarded post-review
- Manual review at the end instead of filtering during extraction
- Wasted processing on unusable content

**Warning signs:**
- Proper nouns from specific settings appearing frequently
- Publisher-specific terminology (e.g., "Forgotten Realms" is WotC Product Identity)
- Monster names that are trademarked (e.g., "Beholder", "Mind Flayer")
- Setting-specific locations and characters

**Prevention:**
1. **Build IP blocklist upfront** - known trademarked terms, Product Identity from OGL declarations
2. **Tag source publisher** - track which publisher/game system each term comes from
3. **Add IP-risk field to schema** - flag terms needing legal review
4. **Process SRD/OGL content first** - start with legally clear content
5. **Require human review gate** - no term goes to final output without IP check
6. **Document source page numbers** - traceability for legal verification

**Phase to address:** Phase 1 (Design) and Phase 4 (IP Review) - blocklist before extraction, review gate before finalization

---

## Moderate Pitfalls

Mistakes that cause delays, rework, or technical debt.

---

### Pitfall 6: Multi-Column Layout Destroys Reading Order

**What goes wrong:** Text from multi-column pages (standard in RPG sourcebooks) is extracted in wrong order, mixing content from different columns, tables, and sidebars.

**Prevention:**
1. Use layout-aware extraction (PyMuPDF's `get_text("blocks")` or `get_text("dict")`)
2. Implement column detection heuristics based on x-coordinates
3. Process sidebars and callout boxes separately
4. Test on stat block pages (notorious for complex layouts)

**Phase to address:** Phase 1 (Document Parsing)

---

### Pitfall 7: EPUB Structure Varies Wildly Across Publishers

**What goes wrong:** EPUB parsing code works for one publisher's format but fails or produces wrong output for another. Chapter ordering, metadata completeness, and internal structure differ significantly.

**Prevention:**
1. Parse container.xml, .opf, and .ncx files to understand each EPUB's structure
2. Don't assume consistent metadata fields across books
3. Use spine ordering, not file system ordering, for chapter sequence
4. Handle DRM-protected files gracefully (fail with clear message, don't corrupt)

**Phase to address:** Phase 1 (Document Parsing)

---

### Pitfall 8: Vocabulary Deduplication Creates Merge Conflicts

**What goes wrong:** Same term extracted from multiple sources has conflicting metadata (different categories, contexts, or confidence levels). Naive deduplication loses information or creates inconsistent records.

**Prevention:**
1. Design survivorship rules upfront - which source wins for each field?
2. Store all instances, dedupe at consolidation time (not extraction time)
3. Use fuzzy matching for spelling variations
4. Preserve provenance - track all sources where term appeared
5. Implement conflict resolution: prefer higher confidence, more specific category, or manual tiebreaker

**Phase to address:** Phase 3 (Consolidation)

---

### Pitfall 9: Hyphenated Words Split Incorrectly

**What goes wrong:** Line-break hyphenation in PDFs causes words to be extracted as fragments ("drag-" + "on" instead of "dragon"), or fantasy compound words are incorrectly rejoined.

**Prevention:**
1. Implement hyphen-at-line-end detection and rejoining
2. Build fantasy-aware dictionary for validation
3. Don't auto-join hyphens that are meaningful (e.g., "half-elf" should stay hyphenated)
4. Post-process extracted text before vocabulary identification

**Phase to address:** Phase 1 (Text Normalization)

---

### Pitfall 10: Batch Processing Has No Resume Capability

**What goes wrong:** Processing fails mid-batch (API error, crash, rate limit). Entire batch must restart from beginning, re-processing already-completed documents and re-incurring costs.

**Prevention:**
1. Implement checkpointing - save progress after each document
2. Store processing state separate from output
3. Use idempotent operations - safe to re-run
4. Generate unique batch IDs for tracking
5. Log completion status per document

**Phase to address:** Phase 2 (Pipeline Infrastructure)

---

## Minor Pitfalls

Annoyances that are fixable but waste time if not anticipated.

---

### Pitfall 11: DOCX Conversion Loses Formatting Cues

**What goes wrong:** Converting DOCX to plain text loses bold/italic/header formatting that distinguishes term names from descriptions.

**Prevention:** Extract with python-docx preserving paragraph styles, or convert to structured intermediate format first.

**Phase to address:** Phase 1 (Document Parsing)

---

### Pitfall 12: Unicode Normalization Inconsistencies

**What goes wrong:** Same visual term stored with different Unicode representations (e.g., composed vs. decomposed accents, different dash characters).

**Prevention:** Apply Unicode normalization (NFC) immediately after extraction, standardize quote marks, dashes, and spaces.

**Phase to address:** Phase 1 (Text Normalization)

---

### Pitfall 13: Empty/Artwork Pages Waste API Tokens

**What goes wrong:** Full-page artwork, blank pages, or table-of-contents pages are sent to Claude for classification, wasting tokens on content with no vocabulary.

**Prevention:** Pre-filter pages by text density before API calls. Skip pages with <50 words or >90% non-text content.

**Phase to address:** Phase 1 (Pre-processing)

---

## Phase-Specific Warning Matrix

| Phase | Likely Pitfall | Severity | Mitigation |
|-------|---------------|----------|------------|
| Phase 1: Document Parsing | Garbled text extraction | Critical | Font fallback + OCR hybrid |
| Phase 1: Document Parsing | Multi-column layout | Moderate | Layout-aware extraction |
| Phase 1: Document Parsing | EPUB structure variance | Moderate | Publisher-specific handlers |
| Phase 2: Vocabulary Extraction | Fantasy NER failures | Critical | Few-shot prompting + taxonomy |
| Phase 2: Vocabulary Extraction | Rate limit explosions | Critical | Batches API + caching |
| Phase 2: Vocabulary Extraction | JSON schema drift | Critical | Pydantic validation + retry |
| Phase 3: Consolidation | Deduplication conflicts | Moderate | Survivorship rules + provenance |
| Phase 4: IP Review | Trademark contamination | Critical | Blocklist + manual review gate |

---

## Sources

### PDF Parsing and Document Processing
- [Challenges You Will Face When Parsing PDFs With Python](https://www.theseattledataguy.com/challenges-you-will-face-when-parsing-pdfs-with-python-how-to-parse-pdfs-with-python/)
- [What's so Hard about PDF Text Extraction?](https://www.compdf.com/blog/what-is-so-hard-about-pdf-text-extraction)
- [A Comparative Study of PDF Parsing Tools Across Diverse Document Categories](https://arxiv.org/html/2410.09871v1)
- [How to Parse a PDF, Part 1 | Unstructured](https://unstructured.io/blog/how-to-parse-a-pdf-part-1)
- [Text Extraction with PyMuPDF | Artifex](https://artifex.com/blog/text-extraction-with-pymupdf)

### NLP and Vocabulary Challenges
- [Comparative Analysis of Named Entity Recognition in the Dungeons and Dragons Domain](https://arxiv.org/abs/2309.17171) - Academic paper directly addressing fantasy NER
- [Out-of-Vocabulary (OOV) Words Explained](https://spotintelligence.com/2024/10/08/out-of-vocabulary-oov-words/)
- [Lexicons In NLP: Challenges, Evaluation And Lexicon Method](https://onlinetutorialhub.com/nlp/lexicons-in-nlp-challenge-evaluation/)

### Claude API and LLM Best Practices
- [Rate limits - Claude API Docs](https://platform.claude.com/docs/en/api/rate-limits)
- [Claude API Rate Limits: Production Scaling Guide](https://www.hashbuilds.com/articles/claude-api-rate-limits-production-scaling-guide-for-saas)
- [How to Fix Claude API 429 Rate Limit Error](https://www.aifreeapi.com/en/posts/fix-claude-api-429-rate-limit-error)

### Structured Output and JSON Validation
- [The guide to structured outputs and function calling with LLMs](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms)
- [How To Ensure LLM Output Adheres to a JSON Schema](https://modelmetry.com/blog/how-to-ensure-llm-output-adheres-to-a-json-schema)
- [Handling LLM Output Parsing Errors](https://apxml.com/courses/prompt-engineering-llm-application-development/chapter-7-output-parsing-validation-reliability/handling-parsing-errors)

### IP and Legal Concerns
- [Part 1: Copyrightability of RPG Stat Blocks](https://gsllcblog.com/2019/08/12/part1statblocks/)
- [Intellectual Property for Gamers](https://cannibalhalflinggaming.com/2023/01/12/intellectual-property-for-gamers/)
- [The Board Game Designers Guide to US Intellectual Property Law](https://www.meeplemountain.com/articles/the-board-game-designers-guide-to-intellectual-property-law/)

### Batch Processing and Data Consolidation
- [The Top 20 Problems with Batch Processing](https://www.kai-waehner.de/blog/2025/04/01/the-top-20-problems-with-batch-processing-and-how-to-fix-them-with-data-streaming/)
- [Building an On-Premise Intelligent Document Processing Pipeline](https://medium.com/@Samir.D/building-an-on-premise-intelligent-document-processing-pipeline-for-regulated-industries-9ca8a1e69070)
- [The Ultimate Data Deduplication Guide](https://winpure.com/data-deduplication-guide/)
