"""PDF text extraction using PyMuPDF."""

import warnings
from pathlib import Path
from typing import List

import pymupdf

from corpora.models import ContentBlock, DocumentOutput
from corpora.parsers.base import BaseParser
from corpora.utils import normalize_text


class PDFParser(BaseParser):
    """Parser for PDF documents using PyMuPDF.

    Extracts text from PDF files page-by-page, preserving page structure.
    Applies text normalization for consistent output.
    Handles encoding errors gracefully with warnings.
    """

    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file type.

        Args:
            path: Path to the file to check.

        Returns:
            True if the file has a .pdf extension (case-insensitive).
        """
        return path.suffix.lower() == ".pdf"

    def extract(self, path: Path, flat: bool = False) -> DocumentOutput:
        """Extract text and metadata from a PDF document.

        Uses PyMuPDF to extract text with proper reading order (sort=True).
        Each page becomes a ContentBlock unless flat=True.

        Args:
            path: Path to the PDF file.
            flat: If True, concatenate all pages into single ContentBlock.

        Returns:
            DocumentOutput with extracted content and metadata.
        """
        doc = pymupdf.open(str(path))

        try:
            # Extract metadata
            metadata = dict(doc.metadata) if doc.metadata else {}

            # Extract text from each page
            content_blocks: List[ContentBlock] = []
            all_text_parts: List[str] = []

            for page_num, page in enumerate(doc):
                try:
                    # Use sort=True for proper reading order
                    raw_text = page.get_text(sort=True)
                    normalized = normalize_text(raw_text)

                    if flat:
                        all_text_parts.append(normalized)
                    else:
                        content_blocks.append(
                            ContentBlock(
                                type="text",
                                text=normalized,
                                page=page_num + 1,  # 1-indexed
                            )
                        )
                except UnicodeDecodeError as e:
                    warnings.warn(
                        f"Encoding error on page {page_num + 1}: {e}. "
                        "Some text may be missing.",
                        stacklevel=2
                    )
                except Exception as e:
                    # Catch font/encoding issues that PyMuPDF may raise
                    warnings.warn(
                        f"Error extracting page {page_num + 1}: {e}. Continuing.",
                        stacklevel=2
                    )

            # If flat mode, create single ContentBlock
            if flat:
                combined_text = "\n\n".join(all_text_parts)
                content_blocks = [
                    ContentBlock(type="text", text=combined_text)
                ]

            return DocumentOutput(
                source=str(path),
                format="pdf",
                metadata=metadata,
                content=content_blocks,
            )

        finally:
            doc.close()

    def needs_ocr(self, path: Path) -> bool:
        """Determine if OCR is needed for this PDF.

        Uses heuristics to detect scanned/image-based PDFs:
        1. Check if images cover most of the page
        2. Check if extracted text is minimal

        Args:
            path: Path to the PDF file.

        Returns:
            True if OCR is likely needed, False otherwise.
        """
        doc = pymupdf.open(str(path))

        try:
            # Check first few pages (up to 3)
            pages_to_check = min(3, len(doc))

            for page_num in range(pages_to_check):
                page = doc[page_num]

                # Get page area
                page_rect = page.rect
                page_area = abs(page_rect)

                if page_area == 0:
                    continue

                # Check for images covering significant area
                image_list = page.get_images()
                if image_list:
                    for img in image_list:
                        try:
                            xref = img[0]
                            img_rect = page.get_image_bbox(xref)
                            if img_rect:
                                # Calculate what fraction of page the image covers
                                intersection = img_rect & page_rect
                                coverage = abs(intersection) / page_area

                                # If image covers >80% of page
                                if coverage >= 0.8:
                                    # Check if text is minimal
                                    text = page.get_text().strip()
                                    if len(text) < 50:
                                        return True
                        except Exception:
                            # Skip problematic images
                            continue

            return False

        finally:
            doc.close()
