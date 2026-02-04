"""Output module for vocabulary file generation.

This module provides models and utilities for generating .vocab.json files
from classified terms, manifest tracking for incremental updates, and
consolidation of multiple vocabularies.
"""

from corpora.output.manifest import CorporaManifest, ManifestEntry
from corpora.output.models import (
    VOCAB_SCHEMA_VERSION,
    VocabularyEntry,
    VocabularyMetadata,
    VocabularyOutput,
)
from corpora.output.vocab_writer import compute_file_hash, write_vocab_file

__all__ = [
    "VOCAB_SCHEMA_VERSION",
    "VocabularyEntry",
    "VocabularyMetadata",
    "VocabularyOutput",
    "compute_file_hash",
    "write_vocab_file",
    "CorporaManifest",
    "ManifestEntry",
]
