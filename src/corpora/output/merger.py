"""Merger module for confidence-weighted deduplication.

This module provides functions for merging duplicate vocabulary entries
(same canonical form) using a confidence-weighted strategy, and tracking
consolidation changes.
"""

from dataclasses import dataclass, field
from typing import List, Set

from corpora.models.vocabulary import AxisScores
from corpora.output.models import VocabularyEntry


# All 16 axis names for weighted averaging
AXIS_NAMES = [
    "fire", "water", "earth", "air",
    "light", "shadow", "life", "void",
    "force", "binding", "ward", "sight",
    "mind", "time", "space", "fate",
]


@dataclass
class ConsolidationSummary:
    """Summary of changes made during vocabulary consolidation.

    Tracks added, updated, removed, and IP-flagged terms for
    reporting to the user.
    """

    added: Set[str] = field(default_factory=set)
    updated: Set[str] = field(default_factory=set)
    removed: Set[str] = field(default_factory=set)
    flagged: Set[str] = field(default_factory=set)

    def __str__(self) -> str:
        """Format summary as human-readable string.

        Returns:
            String like "+5 new, ~3 updated, -1 removed, !2 flagged"
        """
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} new")
        if self.updated:
            parts.append(f"~{len(self.updated)} updated")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        if self.flagged:
            parts.append(f"!{len(self.flagged)} flagged")
        return ", ".join(parts) if parts else "no changes"

    def is_empty(self) -> bool:
        """Check if there are no changes.

        Returns:
            True if no additions, updates, or removals.
        """
        return not (self.added or self.updated or self.removed)


def merge_duplicates(entries: List[VocabularyEntry]) -> VocabularyEntry:
    """Merge duplicate vocabulary entries (same canonical form).

    Strategy:
    1. If single entry, return as-is
    2. Sort by confidence descending, use highest as base
    3. Collect all sources with "; ".join()
    4. Union all tags from all entries
    5. Weighted average of axis scores (weighted by confidence)
    6. Keep IP flag if any entry is flagged
    7. Average confidence across all entries

    Args:
        entries: List of VocabularyEntry with same canonical form.

    Returns:
        Single merged VocabularyEntry.
    """
    if len(entries) == 1:
        return entries[0]

    # Sort by confidence descending, use highest confidence entry as base
    sorted_entries = sorted(entries, key=lambda e: e.confidence, reverse=True)
    base = sorted_entries[0]

    # Collect all unique sources
    all_sources = []
    seen_sources = set()
    for entry in entries:
        if entry.source not in seen_sources:
            all_sources.append(entry.source)
            seen_sources.add(entry.source)
    merged_source = "; ".join(all_sources)

    # Union all tags
    all_tags = set()
    for entry in entries:
        all_tags.update(entry.tags)
    merged_tags = sorted(list(all_tags))

    # Weighted average of axis scores
    merged_axes = _merge_axis_scores(entries)

    # Keep IP flag if any entry is flagged
    merged_ip_flag = None
    for entry in entries:
        if entry.ip_flag:
            merged_ip_flag = entry.ip_flag
            break

    # Average confidence
    merged_confidence = round(
        sum(e.confidence for e in entries) / len(entries),
        2
    )

    # Build merged entry using base values for other fields
    return VocabularyEntry(
        id=base.id,
        text=base.text,
        source=merged_source,
        genre=base.genre,
        intent=base.intent,
        pos=base.pos,
        axes=merged_axes,
        tags=merged_tags,
        category=base.category,
        canonical=base.canonical,
        mood=base.mood,
        energy=base.energy,
        confidence=merged_confidence,
        secondary_intents=base.secondary_intents,
        ip_flag=merged_ip_flag,
    )


def _merge_axis_scores(entries: List[VocabularyEntry]) -> dict:
    """Compute weighted average of axis scores.

    Weights each entry's axis scores by its confidence value.

    Args:
        entries: List of VocabularyEntry to merge.

    Returns:
        Dictionary of axis name to averaged score.
    """
    total_confidence = sum(e.confidence for e in entries)
    if total_confidence == 0:
        return {}

    merged = {}
    for axis in AXIS_NAMES:
        weighted_sum = 0.0
        for entry in entries:
            # Handle AxisScores object or dict
            axes_dict = _get_axes_dict(entry.axes)
            score = axes_dict.get(axis, 0.0)
            weighted_sum += score * entry.confidence

        avg_score = round(weighted_sum / total_confidence, 2)
        if avg_score > 0:
            merged[axis] = avg_score

    return merged


def _get_axes_dict(axes) -> dict:
    """Convert axes to dict regardless of input type.

    Args:
        axes: Either an AxisScores object or a dict.

    Returns:
        Dictionary of axis scores.
    """
    if axes is None:
        return {}
    if isinstance(axes, AxisScores):
        return axes.model_dump()
    if hasattr(axes, "model_dump"):
        return axes.model_dump()
    return dict(axes)
