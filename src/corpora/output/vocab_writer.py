"""Vocabulary file writer for generating .vocab.json output.

This module provides functions to convert classified terms from Phase 2
into per-document vocabulary JSON files.
"""

import hashlib
from pathlib import Path
from typing import List

from corpora.models.vocabulary import AxisScores, ClassifiedTerm
from corpora.output.models import (
    VocabularyEntry,
    VocabularyMetadata,
    VocabularyOutput,
)


def compute_file_hash(path: Path) -> str:
    """Compute MD5 hash of a file for change detection.

    Uses chunked reading for memory efficiency with large files.

    Args:
        path: Path to the file to hash.

    Returns:
        MD5 hexdigest of the file contents.
    """
    hash_md5 = hashlib.md5()
    chunk_size = 64 * 1024  # 64KB chunks

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def write_vocab_file(
    classified_terms: List[ClassifiedTerm],
    source_path: Path,
    output_path: Path,
) -> VocabularyOutput:
    """Convert classified terms to a .vocab.json file.

    Takes the output from Phase 2 classification and writes it to a
    per-document vocabulary JSON file with full metadata.

    Note: This function does NOT perform blocklist checking. It simply
    passes through any ip_flag already set on ClassifiedTerm (e.g., from
    Claude classification during Phase 2). Blocklist-based IP detection
    happens in the consolidation phase where both output foundation
    (03-01) and IP foundation (03-02) are available.

    Args:
        classified_terms: List of ClassifiedTerm objects from Phase 2.
        source_path: Path to the original source document.
        output_path: Path to write the .vocab.json file.

    Returns:
        The VocabularyOutput object that was written to file.
    """
    # Convert ClassifiedTerm objects to VocabularyEntry objects
    entries = []
    for term in classified_terms:
        # Handle axes - convert to dict if AxisScores, else use directly
        if isinstance(term.axes, AxisScores):
            axes_dict = term.axes.model_dump()
        else:
            axes_dict = dict(term.axes) if term.axes else {}

        entry = VocabularyEntry(
            id=term.id,
            text=term.text,
            source=term.source,
            genre=term.genre,
            intent=term.intent,
            pos=term.pos,
            axes=axes_dict,
            tags=term.tags,
            category=term.category,
            canonical=term.canonical,
            mood=term.mood,
            energy=term.energy,
            confidence=term.confidence,
            secondary_intents=term.secondary_intents,
            ip_flag=term.ip_flag,
        )
        entries.append(entry)

    # Count terms with confidence > 0.3
    classified_count = sum(1 for t in classified_terms if t.confidence > 0.3)

    # Count IP-flagged terms
    flagged_count = sum(1 for t in classified_terms if t.ip_flag is not None)

    # Create metadata
    metadata = VocabularyMetadata(
        source_path=str(source_path),
        source_hash=compute_file_hash(source_path),
        term_count=len(classified_terms),
        classified_count=classified_count,
        flagged_count=flagged_count,
    )

    # Build and write output
    output = VocabularyOutput(metadata=metadata, entries=entries)
    output.to_file(output_path)

    return output
