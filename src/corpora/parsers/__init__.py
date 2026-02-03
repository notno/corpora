"""Document parsers for corpora."""

from corpora.parsers.base import BaseParser
from corpora.parsers.epub import EPUBParser
from corpora.parsers.pdf import PDFParser

__all__ = ["BaseParser", "EPUBParser", "PDFParser"]
