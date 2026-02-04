"""Document parsers for corpora."""

from corpora.parsers.base import BaseParser
from corpora.parsers.epub import EPUBParser
from corpora.parsers.ocr import (
    extract_with_ocr,
    is_ocr_available,
    needs_ocr_document,
    needs_ocr_page,
)
from corpora.parsers.pdf import PDFParser

__all__ = [
    "BaseParser",
    "EPUBParser",
    "PDFParser",
    "extract_with_ocr",
    "is_ocr_available",
    "needs_ocr_document",
    "needs_ocr_page",
]
