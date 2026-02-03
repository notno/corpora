# Technology Stack

**Project:** RPG Sourcebook Vocabulary Extraction Pipeline
**Researched:** 2026-02-03
**Overall Confidence:** HIGH

## Executive Summary

This stack is optimized for CPU-only document processing with Claude API integration. The choices prioritize production stability, minimal dependencies, and LLM-friendly output formats. PyMuPDF4LLM is the centerpiece for PDF extraction (specifically designed for LLM consumption), while Instructor handles structured output validation with Pydantic models.

---

## Recommended Stack

### Document Extraction Layer

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pymupdf4llm** | 0.2.9 | PDF text extraction | Purpose-built for LLM pipelines. Outputs clean Markdown, preserves document hierarchy, handles multi-column layouts. Faster than pdfplumber, better structure than pypdf. | HIGH |
| **python-docx** | 1.2.0 | DOCX parsing | Industry standard, MIT licensed, actively maintained (June 2025 release). Read-only extraction is straightforward. | HIGH |
| **EbookLib** | 0.20 | EPUB parsing | Only maintained EPUB library for Python. Handles EPUB2/3 format, extracts spine-ordered content. | HIGH |
| **beautifulsoup4** | 4.14.3 | HTML parsing (EPUB content) | Required for extracting text from EPUB HTML content. Use with lxml parser for speed. | HIGH |
| **lxml** | latest | XML/HTML parsing | Fast C-based parser, dependency of EbookLib, recommended parser for BeautifulSoup. | HIGH |

### AI/LLM Integration Layer

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **anthropic** | 0.77.1 | Claude API client | Official SDK, async support, streaming, batch API support. Direct from Anthropic. | HIGH |
| **instructor** | 1.14.5 | Structured output validation | Patches anthropic client to return Pydantic models. Auto-retries on validation failures. Built-in Anthropic support via `instructor[anthropic]` extra. | HIGH |
| **pydantic** | 2.12.5 | Data models & validation | Core dependency of instructor. Define vocabulary schemas, automatic JSON serialization. | HIGH |

### NLP Processing Layer (Optional)

| Technology | Version | Purpose | When to Use | Confidence |
|------------|---------|---------|-------------|------------|
| **spacy** | 3.8.11 | Linguistic analysis | Use IF you need pre-filtering before Claude (POS tagging, noun phrase extraction). Consider skipping if Claude handles all classification. | MEDIUM |
| **en_core_web_sm** | 3.8.0 | spaCy English model | CPU-optimized small model. 3.8k words/sec on CPU. Use for basic tokenization/POS if needed. | MEDIUM |

### Utilities

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **python-dotenv** | latest | Environment config | Load API keys from .env file. Anthropic SDK recommends this pattern. | HIGH |
| **tqdm** | latest | Progress bars | Visual feedback for batch document processing. | HIGH |
| **pathlib** | stdlib | Path handling | Built-in, cross-platform file path manipulation. | HIGH |

---

## Installation

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Unix

# Core document extraction
pip install pymupdf4llm==0.2.9
pip install python-docx==1.2.0
pip install EbookLib==0.20
pip install beautifulsoup4==4.14.3
pip install lxml

# AI/LLM integration
pip install anthropic==0.77.1
pip install instructor[anthropic]==1.14.5

# Utilities
pip install python-dotenv tqdm

# Optional: NLP pre-processing (only if needed)
# pip install spacy==3.8.11
# python -m spacy download en_core_web_sm
```

### requirements.txt

```
pymupdf4llm==0.2.9
python-docx==1.2.0
EbookLib==0.20
beautifulsoup4==4.14.3
lxml
anthropic==0.77.1
instructor[anthropic]==1.14.5
python-dotenv
tqdm
```

---

## Alternatives Considered

### PDF Extraction

| Recommended | Alternative | Why Not Use Alternative |
|-------------|-------------|------------------------|
| **pymupdf4llm** | pypdf | pypdf is lighter but produces raw text without structure. pymupdf4llm outputs Markdown with headers/lists preserved. |
| **pymupdf4llm** | pdfplumber | pdfplumber excels at tables but slower (0.10s vs 0.024s per page). Overkill for text-heavy RPG sourcebooks. |
| **pymupdf4llm** | PyPDF2 | **DEPRECATED**. PyPDF2 was merged into pypdf. Do not use PyPDF2 in new projects. |
| **pymupdf4llm** | unstructured | Heavy dependency chain, designed for RAG chunking. Overkill for vocabulary extraction. |

### LLM Integration

| Recommended | Alternative | Why Not Use Alternative |
|-------------|-------------|------------------------|
| **instructor** | Raw anthropic SDK | Manual JSON parsing, no automatic validation/retry. instructor adds ~50 lines of boilerplate savings per call. |
| **instructor** | LangChain | Massive dependency, overkill for single-provider usage. instructor is focused and lightweight. |
| **instructor** | outlines | outlines requires local model inference. Not applicable for Claude API usage. |

### NLP Processing

| Recommended | Alternative | Why Not Use Alternative |
|-------------|-------------|------------------------|
| **spacy (optional)** | NLTK | NLTK is 8x slower than spaCy for tokenization. NLTK better for research/education, not production. |
| **spacy (optional)** | transformers | Requires GPU for reasonable speed. CPU-only constraint makes this impractical. |
| **Skip NLP** | spacy | If Claude handles all classification, spacy adds complexity without value. Start without it. |

---

## What NOT to Use (And Why)

### Deprecated/Abandoned Libraries

| Library | Status | Use Instead |
|---------|--------|-------------|
| **PyPDF2** | Deprecated since 2023 | pypdf or pymupdf4llm |
| **textract** | Unmaintained, complex deps | Individual libraries per format |
| **slate** | Abandoned | pypdf |

### Overkill for This Use Case

| Library | Why Not |
|---------|---------|
| **LangChain** | Heavy framework, designed for chains/agents. Simple extraction doesn't need it. |
| **LlamaIndex** | Designed for RAG with vector stores. Vocabulary extraction is simpler. |
| **Apache Tika** | Java dependency, designed for enterprise. Heavyweight for Python scripts. |
| **Spark NLP** | Requires Spark cluster. Overkill for single-machine processing. |

### GPU-Required (Incompatible with CPU-only)

| Library | Why Not |
|---------|---------|
| **transformers (large models)** | Impractically slow on CPU. |
| **spacy en_core_web_trf** | Transformer model, 22x slower on CPU than en_core_web_sm. |
| **KeyBERT** | BERT-based, needs GPU for reasonable performance. |

---

## Architecture Notes

### Document Processing Flow

```
Input Files (PDF/EPUB/DOCX)
         |
         v
+------------------+
| Format Detection |  (by extension)
+------------------+
         |
    +----+----+----+
    |    |    |    |
    v    v    v    v
  PDF  EPUB DOCX  (other)
    |    |    |
    v    v    v
+------+ +------+ +--------+
|pymupdf| |ebook | |python- |
|4llm   | |lib+bs| |docx    |
+------+ +------+ +--------+
    |    |    |
    +----+----+
         |
         v
  Normalized Text (Markdown)
         |
         v
+------------------+
| Claude API       |  (via instructor)
| Classification   |
+------------------+
         |
         v
  Pydantic Models
         |
         v
  JSON Output
```

### Why Markdown as Intermediate Format

pymupdf4llm outputs Markdown by design. Normalize EPUB/DOCX to Markdown too:
- Consistent format for Claude prompt templates
- Headers preserved (useful for section context)
- Lists/bullets maintained
- Easy to chunk by headers if needed

### Batch Processing Strategy

Use `anthropic` Message Batches API for cost optimization:
- Batch up to 10,000 requests
- 50% cost reduction
- 24-hour processing window
- Ideal for processing entire sourcebook collections

---

## Version Compatibility Matrix

| Component | Min Python | Max Python | Notes |
|-----------|-----------|-----------|-------|
| pymupdf4llm | 3.10 | 3.14 | **Constrains minimum** |
| anthropic | 3.9 | 3.14 | |
| instructor | 3.9 | 3.x | |
| python-docx | 3.9 | 3.11+ | |
| EbookLib | 3.9 | 3.13 | |
| spacy | 3.9 | 3.14 | |
| pydantic | 3.9 | 3.14 | |

**Recommended Python Version: 3.11 or 3.12**

- 3.10 is minimum (pymupdf4llm constraint)
- 3.11 has significant performance improvements
- 3.12 is stable and widely supported
- Avoid 3.13/3.14 for max compatibility

---

## Cost Considerations

### Claude API Pricing (as of early 2026)

For vocabulary classification tasks:
- **Claude 3.5 Sonnet**: Best balance of cost/quality for classification
- **Batch API**: 50% discount, use for bulk processing
- **Token optimization**: Send Markdown (compact) not raw text

### Estimated Costs

Assuming 200-page RPG sourcebook, ~500 words/page:
- ~100,000 words per book
- ~130,000 tokens input (with prompts)
- ~20,000 tokens output (classifications)

Per sourcebook (Sonnet, batch pricing):
- Input: ~$0.20
- Output: ~$0.15
- **Total: ~$0.35 per book**

---

## Sources

### PyPI (Version Verification) - HIGH Confidence
- [pymupdf4llm 0.2.9](https://pypi.org/project/pymupdf4llm/) - Released 2026-01-10
- [anthropic 0.77.1](https://pypi.org/project/anthropic/) - Released 2026-02-03
- [instructor 1.14.5](https://pypi.org/project/instructor/) - Released 2026-01-29
- [python-docx 1.2.0](https://pypi.org/project/python-docx/) - Released 2025-06-16
- [EbookLib 0.20](https://pypi.org/project/EbookLib/) - Released 2025-10-26
- [spacy 3.8.11](https://pypi.org/project/spacy/) - Released 2025-11-17
- [pydantic 2.12.5](https://pypi.org/project/pydantic/) - Released 2025-11-26
- [beautifulsoup4 4.14.3](https://pypi.org/project/beautifulsoup4/) - Released 2025-11-30
- [pypdf 6.6.2](https://pypi.org/project/pypdf/) - Released 2026-01-26

### Documentation - HIGH Confidence
- [PyMuPDF4LLM Documentation](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Instructor Documentation](https://python.useinstructor.com/)
- [spaCy Models](https://spacy.io/models)

### Ecosystem Research - MEDIUM Confidence
- [PDF Extractors Comparison (2025)](https://dev.to/onlyoneaman/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-akm)
- [spaCy vs NLTK Comparison](https://www.dsstream.com/post/the-grand-tour-of-nlp-spacy-vs-nltk)
- [Instructor for Structured Output](https://blog.kusho.ai/from-chaos-to-order-structured-json-with-pydantic-and-instructor-in-llms/)

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| PDF Extraction (pymupdf4llm) | HIGH | Verified on PyPI, designed for LLM use, actively maintained |
| DOCX Extraction (python-docx) | HIGH | Industry standard, recent release, well-documented |
| EPUB Extraction (EbookLib) | HIGH | Only viable option, actively maintained |
| Claude Integration (anthropic) | HIGH | Official SDK from Anthropic |
| Structured Output (instructor) | HIGH | Verified Anthropic support, active development |
| NLP Layer (spacy) | MEDIUM | Recommendation is "optional" - may not be needed if Claude handles all classification |
| Version Numbers | HIGH | All verified via PyPI on research date |

---

## Open Questions for Implementation

1. **spaCy needed?** Start without it. If Claude struggles with noisy input, add spaCy for pre-filtering.
2. **Batch size tuning?** Test with 10 documents first, then scale to batch API.
3. **OCR requirement?** If sourcebooks have scanned pages, add `pytesseract`. Most modern PDFs have embedded text.
4. **Section chunking?** May need to split large chapters for Claude context window. Test with full documents first.
