"""Review queue generator for IP-flagged terms.

This module provides models and functions for generating a review queue
(flagged.json) from vocabulary output, containing terms that need human
review due to potential IP concerns.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from corpora.output.models import VocabularyOutput


class FlaggedTerm(BaseModel):
    """A term flagged for human IP review.

    Contains all information needed for a human reviewer to make a
    keep/remove/replace decision on an IP-flagged term.
    """

    canonical: str = Field(description="Canonical/normalized form")
    text: str = Field(description="Display text")
    source: str = Field(description="Source document identifier")
    flag_reason: str = Field(description="Why this term was flagged (e.g., blocklist:dnd)")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    category: str = Field(description="Term category (spell, creature, item, etc.)")
    reviewed: bool = Field(default=False, description="Whether human has reviewed")
    decision: str = Field(default="", description="Human decision: keep/remove/replace")
    notes: str = Field(default="", description="Human reviewer notes")


class ReviewQueue(BaseModel):
    """Review queue containing IP-flagged terms for human review.

    The generated flagged.json file allows humans to review potentially
    IP-encumbered terms and record their decisions.
    """

    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="When this review queue was generated"
    )
    total_flagged: int = Field(description="Total number of flagged terms")
    reviewed_count: int = Field(default=0, description="Number of terms reviewed")
    terms: List[FlaggedTerm] = Field(
        default_factory=list,
        description="Flagged terms awaiting review"
    )

    def to_file(self, path: Path) -> None:
        """Write review queue to JSON file with pretty formatting.

        Args:
            path: Path to write the flagged.json file to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))


def generate_review_queue(vocab: VocabularyOutput, output_path: Path) -> ReviewQueue:
    """Generate a review queue from vocabulary output.

    Filters vocabulary entries for those with ip_flag set and creates
    a review queue for human review.

    Args:
        vocab: VocabularyOutput containing entries to filter.
        output_path: Path to write the flagged.json file.

    Returns:
        ReviewQueue containing flagged terms, also written to output_path.
    """
    # Filter entries with ip_flag set
    flagged_terms = []
    for entry in vocab.entries:
        if entry.ip_flag:
            flagged = FlaggedTerm(
                canonical=entry.canonical,
                text=entry.text,
                source=entry.source,
                flag_reason=entry.ip_flag,
                confidence=entry.confidence,
                category=entry.category,
            )
            flagged_terms.append(flagged)

    # Sort by canonical for consistent output
    flagged_terms.sort(key=lambda t: t.canonical)

    # Create queue
    queue = ReviewQueue(
        total_flagged=len(flagged_terms),
        terms=flagged_terms,
    )

    # Write to file
    queue.to_file(output_path)

    return queue
