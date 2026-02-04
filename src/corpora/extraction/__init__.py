"""Term extraction module for vocabulary extraction.

This module provides NLP-based extraction of fantasy-relevant vocabulary
candidates from text using spaCy.
"""

from corpora.extraction.extractor import TermExtractor, extract_candidates
from corpora.extraction.filters import TermFilter

__all__ = ["TermExtractor", "TermFilter", "extract_candidates"]
