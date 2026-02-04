"""Batch processing module for parallel document processing.

This module provides models and utilities for batch processing of documents
with parallel execution, retry logic, and manifest-based resumability.
"""

from corpora.batch.models import (
    EXIT_NO_INPUT,
    EXIT_PARTIAL,
    EXIT_SUCCESS,
    BatchConfig,
    BatchSummary,
    DocumentResult,
    DocumentStatus,
)
from corpora.batch.processor import BatchProcessor, SUPPORTED_EXTENSIONS

__all__ = [
    "BatchConfig",
    "BatchProcessor",
    "BatchSummary",
    "DocumentResult",
    "DocumentStatus",
    "EXIT_NO_INPUT",
    "EXIT_PARTIAL",
    "EXIT_SUCCESS",
    "SUPPORTED_EXTENSIONS",
]
