"""Batch processing models for configuration and results.

This module provides Pydantic models for batch processing:
- BatchConfig: Configuration for batch processing runs
- DocumentResult: Result of processing a single document
- DocumentStatus: Enum for document processing status
- BatchSummary: Summary of batch processing run
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


# Exit codes per sysexits.h convention
EXIT_SUCCESS = 0        # All documents processed successfully
EXIT_PARTIAL = 75       # EX_TEMPFAIL: Some documents failed (partial success)
EXIT_NO_INPUT = 66      # EX_NOINPUT: No documents found


class DocumentStatus(str, Enum):
    """Status of document processing."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # Already processed, unchanged


class DocumentResult(BaseModel):
    """Result of processing a single document.

    Captures the outcome of processing including success/failure status,
    term count, output path, and any error message.
    """

    source_path: Path = Field(description="Path to the source document")
    status: DocumentStatus = Field(description="Processing status")
    term_count: int = Field(default=0, description="Number of terms extracted")
    vocab_path: Optional[Path] = Field(
        default=None,
        description="Path to generated .vocab.json"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    duration_seconds: float = Field(
        default=0.0,
        description="Time taken to process document in seconds"
    )


class BatchConfig(BaseModel):
    """Configuration for batch processing.

    Controls input/output directories, parallelism settings,
    and processing behavior.
    """

    input_dir: Path = Field(description="Directory containing documents to process")
    output_dir: Path = Field(description="Directory for .vocab.json output files")
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of parallel workers"
    )
    force_reprocess: bool = Field(
        default=False,
        description="Reprocess all documents, ignoring manifest"
    )
    blocklist_path: Optional[Path] = Field(
        default=None,
        description="Path to IP blocklist JSON file"
    )


class BatchSummary(BaseModel):
    """Summary of batch processing run.

    Aggregates results across all documents processed in a batch.
    """

    total_documents: int = Field(description="Total number of documents found")
    processed: int = Field(description="Number of documents successfully processed")
    skipped: int = Field(description="Number of documents skipped (already processed)")
    failed: int = Field(description="Number of documents that failed processing")
    total_terms: int = Field(description="Total terms extracted across all documents")
    duration_seconds: float = Field(description="Total time for batch processing")
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages from failed documents"
    )

    def get_exit_code(self) -> int:
        """Determine exit code based on processing results.

        Returns:
            EXIT_SUCCESS if all succeeded, EXIT_PARTIAL if some failed,
            EXIT_NO_INPUT if no documents found.
        """
        if self.total_documents == 0:
            return EXIT_NO_INPUT
        elif self.failed == 0:
            return EXIT_SUCCESS
        elif self.processed > 0:
            return EXIT_PARTIAL
        else:
            return EXIT_PARTIAL  # All failed but some were attempted
