"""Data models for corpora."""

from corpora.models.output import ContentBlock, DocumentOutput
from corpora.models.vocabulary import AxisScores, CandidateTerm, ClassifiedTerm

__all__ = [
    "AxisScores",
    "CandidateTerm",
    "ClassifiedTerm",
    "ContentBlock",
    "DocumentOutput",
]
