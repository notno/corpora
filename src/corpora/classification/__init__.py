"""Classification module for Claude API vocabulary classification."""

from corpora.classification.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_batch_user_prompt,
    build_user_prompt,
)
from corpora.classification.client import ClassificationClient

__all__ = [
    "CLASSIFICATION_SYSTEM_PROMPT",
    "ClassificationClient",
    "build_batch_user_prompt",
    "build_user_prompt",
]
