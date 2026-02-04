"""Pydantic models for document extraction output."""

from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    """A block of extracted content from a document."""

    type: str = Field(description="Block type: text, heading, etc.")
    text: str = Field(description="The extracted text content")
    page: Optional[int] = Field(default=None, description="Source page number (1-indexed)")
    chapter: Optional[int] = Field(default=None, description="Source chapter number (1-indexed)")


class DocumentOutput(BaseModel):
    """Output schema for parsed documents.

    This is the Phase 1 output format containing raw extracted text
    with metadata. The rich vocabulary schema (id, intent, mood, axes, etc.)
    comes from Phase 2 classification.
    """

    source: str = Field(description="Source file path")
    format: Literal["pdf", "epub"] = Field(description="Detected document format")
    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of extraction"
    )
    ocr_used: bool = Field(default=False, description="Whether OCR was used for extraction")
    metadata: dict = Field(
        default_factory=dict,
        description="Document metadata (title, author, etc.)"
    )
    content: List[ContentBlock] = Field(description="Extracted content blocks")

    def to_json_file(self, path: str) -> None:
        """Write output to JSON file.

        Args:
            path: Path to write the JSON file to.
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
