"""Output module for vocabulary file generation.

This module provides models and utilities for generating .vocab.json files
from classified terms.
"""

from corpora.output.models import (
    VOCAB_SCHEMA_VERSION,
    VocabularyEntry,
    VocabularyMetadata,
    VocabularyOutput,
)

__all__ = [
    "VOCAB_SCHEMA_VERSION",
    "VocabularyEntry",
    "VocabularyMetadata",
    "VocabularyOutput",
]
