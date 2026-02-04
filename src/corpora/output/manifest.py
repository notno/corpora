"""Manifest module for tracking processed documents.

This module provides models and functions for .corpora-manifest.json,
which tracks which documents have been processed and their content hashes
for incremental update support.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from corpora.output.vocab_writer import compute_file_hash


class ManifestEntry(BaseModel):
    """Tracking entry for a processed document.

    Stores the information needed to detect when a document needs
    reprocessing (hash change) and to identify orphaned vocab files.
    """

    source_path: str = Field(description="Path to original source document")
    source_hash: str = Field(description="MD5 hash of source for change detection")
    vocab_path: str = Field(description="Path to generated .vocab.json")
    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="When the document was processed"
    )
    term_count: int = Field(description="Number of terms extracted")


class CorporaManifest(BaseModel):
    """Manifest tracking processed documents for incremental updates.

    Maintains a registry of processed documents with their content hashes
    to enable efficient incremental processing (only process new/changed files).
    """

    schema_version: str = Field(
        default="1.0",
        description="Manifest schema version"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last time manifest was updated"
    )
    documents: Dict[str, ManifestEntry] = Field(
        default_factory=dict,
        description="Mapping of source_path to ManifestEntry"
    )

    def needs_processing(self, source_path: Path) -> bool:
        """Check if a document needs (re)processing.

        A document needs processing if:
        1. It's not in the manifest (new document)
        2. Its content hash has changed (modified document)

        Args:
            source_path: Path to the source document.

        Returns:
            True if document needs processing, False if unchanged.
        """
        key = str(source_path)

        # New document - needs processing
        if key not in self.documents:
            return True

        # Check if content has changed
        current_hash = compute_file_hash(source_path)
        return current_hash != self.documents[key].source_hash

    def get_orphaned_vocabs(self, current_sources: List[Path]) -> List[str]:
        """Find vocab files whose source documents no longer exist.

        Identifies vocabulary files that were generated from source documents
        that are no longer in the current source list. These may be candidates
        for removal or archival.

        Args:
            current_sources: List of current source document paths.

        Returns:
            List of vocab file paths that are orphaned.
        """
        current_keys = {str(p) for p in current_sources}
        return [
            entry.vocab_path
            for key, entry in self.documents.items()
            if key not in current_keys
        ]

    def update_entry(
        self,
        source: Path,
        vocab: Path,
        term_count: int,
    ) -> None:
        """Add or update a manifest entry for a processed document.

        Args:
            source: Path to the source document.
            vocab: Path to the generated .vocab.json file.
            term_count: Number of terms in the vocabulary.
        """
        key = str(source)
        self.documents[key] = ManifestEntry(
            source_path=key,
            source_hash=compute_file_hash(source),
            vocab_path=str(vocab),
            processed_at=datetime.now(),
            term_count=term_count,
        )
        self.last_updated = datetime.now()

    def save(self, path: Path) -> None:
        """Write manifest to .corpora-manifest.json file.

        Args:
            path: Path to write the manifest file.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "CorporaManifest":
        """Load manifest from file or return empty manifest.

        If the file doesn't exist, returns a new empty manifest.

        Args:
            path: Path to the manifest file.

        Returns:
            CorporaManifest loaded from file or new empty manifest.
        """
        if not path.exists():
            return cls()

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)
