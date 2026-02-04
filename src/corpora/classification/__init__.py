"""Classification module for Claude API vocabulary classification."""

from corpora.classification.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_batch_user_prompt,
    build_user_prompt,
)

__all__ = [
    "CLASSIFICATION_SYSTEM_PROMPT",
    "build_batch_user_prompt",
    "build_user_prompt",
]
