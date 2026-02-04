# Phase 1: Document Parsing - Research

**Researched:** 2026-02-03
**Domain:** PDF/EPUB text extraction, CLI development, OCR integration
**Confidence:** HIGH

## Summary

This research investigates the standard Python stack for extracting text from PDF and EPUB documents, with optional OCR fallback for scanned content. The domain is well-served by mature, actively-maintained libraries with clear community consensus.

**PyMuPDF** emerges as the clear choice for both PDF and EPUB extraction. It handles both formats with a unified API, includes built-in OCR integration via Tesseract, and provides excellent performance. For EPUB specifically, it supports chapter-based navigation which aligns with the user's requirement for preserving document structure. The alternative approach of EbookLib + BeautifulSoup for EPUB adds complexity without benefit since PyMuPDF handles EPUB natively.

**Typer** is the recommended CLI framework. Built on Click but designed for modern Python with type hints, it provides automatic help generation, shell completion, and a clean subcommand structure that matches the user's `corpora parse <input>` design decision.

**Primary recommendation:** Use PyMuPDF for all document extraction (PDF and EPUB), Typer for CLI, and OCRmyPDF/Tesseract for OCR fallback when PyMuPDF's native extraction yields insufficient text.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF | 1.26.7 | PDF and EPUB text extraction | Unified API for both formats, built-in OCR support, high performance, chapter-aware EPUB handling |
| Typer | latest | CLI framework | Type-hint based, auto-generated help, built on mature Click foundation |
| Pydantic | 2.12.5 | Data validation and JSON serialization | Industry standard for Python data models, native JSON support |
| Rich | 14.3.2 | Terminal output formatting | Progress bars, styled output, logging; bundled with Typer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytesseract | latest | Python wrapper for Tesseract OCR | When PyMuPDF OCR integration needs direct control |
| OCRmyPDF | 17.1.0 | PDF OCR layer insertion | Alternative OCR approach, adds searchable layer to scanned PDFs |

### External Dependencies
| Tool | Purpose | Notes |
|------|---------|-------|
| Tesseract-OCR | OCR engine | Required for OCR features; optional dependency per user decision |
| Ghostscript | PDF processing | Required by OCRmyPDF if used |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF for EPUB | EbookLib + BeautifulSoup | More manual work, no unified API with PDF, HTML parsing required |
| PyMuPDF for PDF | pypdf, pdfminer.six | Less feature-rich, no built-in OCR, slower |
| Typer | Click | More boilerplate, less modern feel, but equivalent functionality |
| Typer | argparse | Standard library but verbose, no auto-completion |

**Installation:**
```bash
# Core dependencies
pip install pymupdf typer pydantic rich

# OCR dependencies (optional)
pip install pytesseract
# Plus system install of Tesseract-OCR
```

## Architecture Patterns

### Recommended Project Structure
```
corpora/
├── pyproject.toml
└── src/
    └── corpora/
        ├── __init__.py
        ├── __main__.py           # Entry point for python -m corpora
        ├── cli/
        │   ├── __init__.py
        │   ├── main.py           # Typer app, top-level commands
        │   └── parse.py          # `corpora parse` subcommand
        ├── parsers/
        │   ├── __init__.py
        │   ├── base.py           # Abstract parser interface
        │   ├── pdf.py            # PDF extraction logic
        │   ├── epub.py           # EPUB extraction logic
        │   └── ocr.py            # OCR detection and execution
        ├── models/
        │   ├── __init__.py
        │   └── output.py         # Pydantic models for JSON output
        └── utils/
            ├── __init__.py
            ├── normalization.py  # Text normalization utilities
            └── errors.py         # Custom exceptions, error handling
```

### Pattern 1: Unified Parser Interface
**What:** Abstract base class with format-specific implementations
**When to use:** Always - provides consistent API regardless of input format
**Example:**
```python
# Source: Architecture pattern from research
from abc import ABC, abstractmethod
from pathlib import Path
from corpora.models.output import DocumentOutput

class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file."""
        pass

    @abstractmethod
    def extract(self, path: Path) -> DocumentOutput:
        """Extract text and metadata from document."""
        pass

    @abstractmethod
    def needs_ocr(self, path: Path) -> bool:
        """Determine if OCR is needed for this document."""
        pass
```

### Pattern 2: OCR Detection Heuristics
**What:** Determine if OCR is needed before expensive processing
**When to use:** For all PDF files before extraction
**Example:**
```python
# Source: PyMuPDF GitHub discussion #1653
import pymupdf

def needs_ocr(page: pymupdf.Page, threshold: float = 0.95) -> bool:
    """
    Detect if a page is likely scanned (image-based).

    Heuristics:
    1. Check if images cover most of the page
    2. Check if extracted text is minimal
    """
    # Get page dimensions
    page_rect = page.rect
    page_area = abs(page_rect)

    # Check image coverage
    image_list = page.get_images()
    if image_list:
        for img in image_list:
            xref = img[0]
            img_rect = page.get_image_bbox(xref)
            if img_rect:
                coverage = abs(img_rect & page_rect) / page_area
                if coverage >= threshold:
                    # Large image covering page - likely scanned
                    text = page.get_text().strip()
                    # If minimal text despite large image, needs OCR
                    if len(text) < 50:  # Configurable threshold
                        return True
    return False
```

### Pattern 3: Chapter-Aware EPUB Extraction
**What:** Use PyMuPDF's location-based addressing for EPUBs
**When to use:** When preserving chapter structure in output
**Example:**
```python
# Source: PyMuPDF documentation - Document class
import pymupdf
from typing import Iterator, Tuple

def extract_epub_by_chapter(doc: pymupdf.Document) -> Iterator[Tuple[int, str]]:
    """
    Extract EPUB content chapter by chapter.

    Yields (chapter_number, chapter_text) tuples.
    Uses location-based addressing for performance with large EPUBs.
    """
    for chapter_num in range(doc.chapter_count):
        chapter_text_parts = []
        page_count = doc.chapter_page_count(chapter_num)

        for page_num in range(page_count):
            page = doc.load_page((chapter_num, page_num))
            chapter_text_parts.append(page.get_text())

        yield chapter_num, "\n".join(chapter_text_parts)
```

### Pattern 4: Typer Subcommand Structure
**What:** Organized CLI with subcommands matching user's decision
**When to use:** For the `corpora parse` command structure
**Example:**
```python
# Source: Typer documentation
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(help="Corpora: Extract vocabulary from documents")
parse_app = typer.Typer(help="Parse documents and extract text")
app.add_typer(parse_app, name="parse")

@parse_app.callback(invoke_without_command=True)
def parse(
    ctx: typer.Context,
    input_path: Path = typer.Argument(..., help="File, folder, or glob pattern"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file or directory"),
    format: str = typer.Option("json", "--format", help="Output format"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    ocr: Optional[bool] = typer.Option(None, "--ocr/--no-ocr", help="Force OCR on/off"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop on first error"),
    flat: bool = typer.Option(False, "--flat", help="Flatten document structure"),
):
    """Parse document(s) and extract text content."""
    pass
```

### Anti-Patterns to Avoid
- **Parsing EPUB as raw ZIP:** PyMuPDF handles EPUB natively; don't manually unzip and parse HTML
- **Re-running OCR on every access:** Store OCR results in TextPage objects for reuse
- **Ignoring chapter structure:** EPUB chapter boundaries are semantically meaningful; preserve them
- **Global state for parsers:** Use dependency injection for testability
- **Silent failures:** Always log errors to the error log file per user decision

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | PyMuPDF | PDF format is complex; font handling, encoding, layout are solved problems |
| EPUB parsing | Manual ZIP + HTML parse | PyMuPDF | Chapter ordering, spine navigation, metadata are handled correctly |
| OCR | Custom image processing | Tesseract via pytesseract/PyMuPDF | Decades of research in OCR engines |
| Text encoding detection | Heuristic guessing | chardet/charset-normalizer | Edge cases in encoding detection are extensive |
| CLI argument parsing | Manual sys.argv | Typer | Help generation, validation, completion are complex |
| JSON schema validation | Manual dict checking | Pydantic | Validation, serialization, error messages handled correctly |
| Progress bars | Print statements | Rich (via Typer) | Terminal width, refresh rate, nested progress handled |
| Unicode normalization | String replace chains | unicodedata.normalize | NFC/NFD/NFKC/NFKD forms require Unicode expertise |

**Key insight:** Document parsing involves decades of edge cases in format handling, encoding, and OCR. Libraries exist because these problems are deceptively complex. Custom solutions will fail on real-world documents.

## Common Pitfalls

### Pitfall 1: Assuming Text Extraction Always Works
**What goes wrong:** Empty or garbled output from PDFs that display correctly
**Why it happens:** PDF "text" may be vector graphics, embedded fonts without Unicode mappings, or images
**How to avoid:** Always check extraction results; implement OCR fallback; warn users about quality
**Warning signs:** Very short output, "<?>" characters, non-printable characters

### Pitfall 2: Wrong Reading Order
**What goes wrong:** Text appears jumbled or out of sequence
**Why it happens:** PDF stores text in creation order, not reading order (headers added after body)
**How to avoid:** Use PyMuPDF's `sort` parameter: `page.get_text(sort=True)`
**Warning signs:** Headers appearing at end of extracted text, columns interleaved

### Pitfall 3: Memory Exhaustion on Large PDFs
**What goes wrong:** OOM errors on documents with many pages or large images
**Why it happens:** Loading entire document into memory; uncompressed content streams
**How to avoid:** Process page-by-page; check content stream size before extraction; use generators
**Warning signs:** Slow processing, growing memory usage, crash on specific files

### Pitfall 4: OCR Performance Assumptions
**What goes wrong:** Processing takes hours unexpectedly
**Why it happens:** OCR is ~1000x slower than native extraction (per PyMuPDF docs)
**How to avoid:** Warn users about OCR time; implement progress indication; prompt before OCR (per user decision)
**Warning signs:** Single page taking >10 seconds

### Pitfall 5: Font Encoding Issues Crashing Pipeline
**What goes wrong:** Entire batch fails due to one problematic file
**Why it happens:** Unusual fonts, legacy encodings, malformed PDFs
**How to avoid:** Wrap extraction in try/except; log errors; continue processing (per user decision)
**Warning signs:** UnicodeDecodeError, KeyError on font lookup

### Pitfall 6: EPUB Chapter Boundaries Lost
**What goes wrong:** Output is flat text blob, losing document structure
**Why it happens:** Extracting all pages sequentially without tracking chapters
**How to avoid:** Use PyMuPDF's chapter_count and chapter_page_count; structure output by chapter
**Warning signs:** No logical breaks in output, table of contents doesn't map to content

### Pitfall 7: Ligatures and Special Characters
**What goes wrong:** "ﬁ" becomes single character instead of "fi", fractions remain as symbols
**Why it happens:** Unicode has composed forms (ligatures, fractions) that may not normalize
**How to avoid:** Apply NFKC normalization to decompose compatibility characters
**Warning signs:** Spell check failures, search misses, unexpected single characters

## Code Examples

Verified patterns from official sources:

### Basic PDF Text Extraction
```python
# Source: PyMuPDF documentation - Text recipes
import pymupdf

def extract_pdf_text(path: str) -> str:
    """Extract all text from a PDF file."""
    doc = pymupdf.open(path)
    text_parts = []

    for page in doc:
        # sort=True ensures top-to-bottom, left-to-right reading order
        text = page.get_text(sort=True)
        text_parts.append(text)

    doc.close()
    return "\n".join(text_parts)
```

### Structured Text Extraction with Metadata
```python
# Source: PyMuPDF documentation - get_text("dict")
import pymupdf
from typing import List, Dict, Any

def extract_with_structure(path: str) -> List[Dict[str, Any]]:
    """Extract text with block structure information."""
    doc = pymupdf.open(path)
    pages = []

    for page_num, page in enumerate(doc):
        data = page.get_text("dict", sort=True)
        blocks = []

        for block in data["blocks"]:
            if block["type"] == 0:  # Text block
                block_text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"]
                    block_text += "\n"
                blocks.append({
                    "type": "text",
                    "bbox": block["bbox"],
                    "text": block_text.strip()
                })

        pages.append({
            "page_number": page_num + 1,
            "blocks": blocks
        })

    doc.close()
    return pages
```

### EPUB Extraction with Chapter Structure
```python
# Source: PyMuPDF documentation - Document class, EPUB features
import pymupdf
from typing import List, Dict

def extract_epub(path: str) -> Dict:
    """Extract EPUB with chapter structure preserved."""
    doc = pymupdf.open(path)

    # Get metadata
    metadata = doc.metadata
    toc = doc.get_toc()  # Table of contents

    chapters = []
    for chapter_num in range(doc.chapter_count):
        chapter_pages = []
        for page_num in range(doc.chapter_page_count(chapter_num)):
            page = doc.load_page((chapter_num, page_num))
            chapter_pages.append(page.get_text())

        chapters.append({
            "chapter": chapter_num + 1,
            "content": "\n".join(chapter_pages)
        })

    doc.close()

    return {
        "metadata": metadata,
        "toc": toc,
        "chapters": chapters
    }
```

### OCR Integration
```python
# Source: PyMuPDF documentation - OCR recipes
import pymupdf

def extract_with_ocr(path: str, language: str = "eng") -> str:
    """Extract text, falling back to OCR for image-based pages."""
    doc = pymupdf.open(path)
    text_parts = []

    for page in doc:
        # Try native extraction first
        text = page.get_text().strip()

        if len(text) < 50:  # Likely needs OCR
            # Create TextPage with OCR
            tp = page.get_textpage_ocr(language=language)
            text = page.get_text(textpage=tp)

        text_parts.append(text)

    doc.close()
    return "\n".join(text_parts)
```

### Pydantic Output Model
```python
# Source: Pydantic documentation - serialization
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ContentBlock(BaseModel):
    """A block of extracted content."""
    type: str = Field(description="Block type: text, heading, etc.")
    text: str = Field(description="The extracted text content")
    page: Optional[int] = Field(None, description="Source page number")
    chapter: Optional[int] = Field(None, description="Source chapter number")

class DocumentOutput(BaseModel):
    """Output schema for parsed documents."""
    source: str = Field(description="Source file path")
    format: str = Field(description="Detected format: pdf, epub")
    extracted_at: datetime = Field(default_factory=datetime.now)
    ocr_used: bool = Field(False, description="Whether OCR was used")
    metadata: dict = Field(default_factory=dict, description="Document metadata")
    content: List[ContentBlock] = Field(description="Extracted content blocks")

    def to_json_file(self, path: str) -> None:
        """Write output to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
```

### Text Normalization
```python
# Source: Python unicodedata documentation, textnorm patterns
import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    Normalize extracted text for consistent output.

    - NFKC normalization (decomposes ligatures, normalizes compatibility chars)
    - Collapse multiple whitespace to single space
    - Normalize line endings
    - Strip leading/trailing whitespace
    """
    # Unicode normalization - NFKC for compatibility decomposition
    text = unicodedata.normalize("NFKC", text)

    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse multiple newlines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPDF2 | pypdf (renamed) | 2022 | Active development resumed |
| pdfminer.six for all PDFs | PyMuPDF as default | ~2023 | Better performance, unified API |
| EbookLib + BeautifulSoup for EPUB | PyMuPDF for EPUB | PyMuPDF always supported | Simpler stack, chapter-aware |
| Click for CLI | Typer (built on Click) | 2019+ | Type hints, less boilerplate |
| Pydantic v1 | Pydantic v2 | 2023 | Major performance improvement, new API |
| Manual OCR pipelines | PyMuPDF built-in OCR | 1.18.0+ | Integrated, no external orchestration |

**Deprecated/outdated:**
- **PyPDF2:** Renamed to pypdf; use pypdf if choosing that library
- **Pydantic v1 syntax:** v2 uses model_dump() not dict(), model_dump_json() not json()
- **Python 3.9 for PyMuPDF:** Requires Python 3.10+ as of v1.26

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal OCR threshold for "insufficient text"**
   - What we know: 50 characters per page is a common heuristic
   - What's unclear: May need tuning for specific document types
   - Recommendation: Make configurable, start with 50 chars, document as Claude's discretion item

2. **Chapter title extraction from EPUB TOC**
   - What we know: PyMuPDF provides get_toc() returning outline
   - What's unclear: Mapping TOC entries to chapter content may be imprecise
   - Recommendation: Include TOC in output metadata; let users reference it

3. **Handling password-protected PDFs**
   - What we know: PyMuPDF supports password parameter in open()
   - What's unclear: Whether to prompt for password or skip
   - Recommendation: Add --password flag; skip with warning if not provided

## Sources

### Primary (HIGH confidence)
- [PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/) - Text extraction, OCR, Document class, supported formats
- [PyMuPDF PyPI](https://pypi.org/project/PyMuPDF/) - Version 1.26.7, Python 3.10+ requirement
- [Typer documentation](https://typer.tiangolo.com/) - CLI patterns, subcommands, options
- [Pydantic documentation](https://docs.pydantic.dev/) - Serialization patterns
- [Pydantic PyPI](https://pypi.org/project/pydantic/) - Version 2.12.5, Python 3.9+
- [Rich PyPI](https://pypi.org/project/rich/) - Version 14.3.2, terminal output
- [OCRmyPDF PyPI](https://pypi.org/project/ocrmypdf/) - Version 17.1.0, OCR tool
- [EbookLib PyPI](https://pypi.org/project/EbookLib/) - Version 0.20, alternative for EPUB
- [BeautifulSoup4 PyPI](https://pypi.org/project/beautifulsoup4/) - Version 4.14.3, HTML parsing

### Secondary (MEDIUM confidence)
- [PyMuPDF GitHub Discussion #1653](https://github.com/pymupdf/PyMuPDF/discussions/1653) - Scanned PDF detection heuristics
- [Unstract PDF evaluation](https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/) - Library comparison 2026
- [Typer alternatives page](https://typer.tiangolo.com/alternatives/) - Click comparison
- [Python Packaging Guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) - src layout recommendation

### Tertiary (LOW confidence)
- Various Medium articles on PDF extraction - general patterns, not authoritative
- Stack Overflow discussions - encoding issues, workarounds

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official PyPI and documentation
- Architecture: HIGH - Patterns derived from official documentation examples
- Pitfalls: MEDIUM - Combination of official docs and community experience

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - stable domain, mature libraries)

## Exit Codes Recommendation

Per user decision (Claude's discretion), recommended exit codes following Linux conventions:

| Code | Meaning | When Used |
|------|---------|-----------|
| 0 | Success | All documents processed successfully |
| 1 | General error | Unspecified error |
| 2 | Usage error | Invalid arguments, missing required flags |
| 64 | Input error | Input file not found, not readable |
| 65 | Data error | Malformed document, extraction failed |
| 66 | No input | No files matched glob pattern |
| 70 | Internal error | Unexpected exception |
| 73 | Cannot create output | Output path not writable |
| 74 | I/O error | Error reading/writing files |
| 130 | Interrupted | User cancelled (Ctrl+C) |

These codes are from sysexits.h convention (64-78 range) plus standard signals.
