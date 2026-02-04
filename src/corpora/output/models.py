"""Pydantic models for vocabulary output files.

This module defines the output schema for .vocab.json files:
- VocabularyMetadata: Source document info and processing statistics
- VocabularyEntry: Individual term entry in output
- VocabularyOutput: Complete output document with metadata and entries
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from corpora.models.vocabulary import AxisScores


# Schema version for forward compatibility
VOCAB_SCHEMA_VERSION = "1.0"


class VocabularyMetadata(BaseModel):
    """Metadata for a vocabulary output file.

    Contains source document information, processing timestamps,
    and statistics about the extracted terms.
    """

    schema_version: str = Field(
        default=VOCAB_SCHEMA_VERSION,
        description="Schema version for forward compatibility"
    )
    source_path: str = Field(description="Original document path")
    source_hash: str = Field(description="MD5 hash of source for change detection")
    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of extraction"
    )
    term_count: int = Field(description="Total number of terms extracted")
    classified_count: int = Field(
        description="Number of terms with confidence > 0.3"
    )
    flagged_count: int = Field(
        default=0,
        description="Number of IP-flagged terms"
    )


class VocabularyEntry(BaseModel):
    """A vocabulary entry in the output file.

    Contains all classification data for a single term,
    matching the ClassifiedTerm schema with output-specific additions.
    """

    id: str = Field(description="Unique identifier (e.g., 'src-fireball')")
    text: str = Field(description="Display text")
    source: str = Field(description="Source document identifier")
    genre: str = Field(default="fantasy", description="Genre classification")
    intent: str = Field(description="Primary intent (offensive, defensive, utility, etc.)")
    pos: str = Field(description="Part of speech")
    axes: dict = Field(
        default_factory=dict,
        description="16-axis relevance scores"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Additional classification tags"
    )
    category: str = Field(description="Term category (spell, creature, item, etc.)")
    canonical: str = Field(description="Canonical/normalized form")
    mood: str = Field(description="Mood/tone (arcane, dark, heroic, etc.)")
    energy: str = Field(default="", description="Energy type if applicable")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score"
    )
    secondary_intents: List[str] = Field(
        default_factory=list,
        description="Alternative/secondary intents"
    )
    ip_flag: Optional[str] = Field(
        default=None,
        description="IP flag reason if term is potentially IP-encumbered"
    )


class VocabularyOutput(BaseModel):
    """Complete vocabulary output document.

    Contains metadata about the source document and extraction process,
    plus all extracted vocabulary entries.
    """

    metadata: VocabularyMetadata = Field(description="Document and extraction metadata")
    entries: List[VocabularyEntry] = Field(
        default_factory=list,
        description="Vocabulary entries"
    )

    def to_file(self, path: Path) -> None:
        """Write output to JSON file with pretty formatting.

        Args:
            path: Path to write the JSON file to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
