"""EPUB text extraction using PyMuPDF."""

import warnings
from pathlib import Path
from typing import List

import pymupdf

from corpora.models import ContentBlock, DocumentOutput
from corpora.parsers.base import BaseParser
from corpora.utils import normalize_text


class EPUBParser(BaseParser):
    """Parser for EPUB documents using PyMuPDF.

    Extracts text from EPUB files chapter-by-chapter, preserving structure.
    Uses PyMuPDF's location-based addressing for chapter navigation.
    Falls back to page-by-page extraction for single-chapter EPUBs.
    """

    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file type.

        Args:
            path: Path to the file to check.

        Returns:
            True if the file has an .epub extension (case-insensitive).
        """
        return path.suffix.lower() == ".epub"

    def extract(self, path: Path, flat: bool = False) -> DocumentOutput:
        """Extract text and metadata from an EPUB document.

        Uses PyMuPDF's chapter-aware extraction when available.
        Falls back to page-by-page for EPUBs without chapter structure.

        Args:
            path: Path to the EPUB file.
            flat: If True, concatenate all chapters into single ContentBlock.

        Returns:
            DocumentOutput with extracted content and metadata.
        """
        doc = pymupdf.open(str(path))

        try:
            # Extract metadata
            metadata = dict(doc.metadata) if doc.metadata else {}

            # Include table of contents in metadata if available
            toc = doc.get_toc()
            if toc:
                metadata["toc"] = toc

            content_blocks: List[ContentBlock] = []
            all_text_parts: List[str] = []

            # Check if we have chapter structure
            chapter_count = doc.chapter_count

            if chapter_count > 1:
                # Chapter-aware extraction
                content_blocks, all_text_parts = self._extract_by_chapter(
                    doc, flat
                )
            else:
                # Fallback to page-by-page for single-chapter or no chapter info
                content_blocks, all_text_parts = self._extract_by_page(
                    doc, flat
                )

            # If flat mode, create single ContentBlock
            if flat:
                combined_text = "\n\n".join(all_text_parts)
                content_blocks = [
                    ContentBlock(type="text", text=combined_text)
                ]

            return DocumentOutput(
                source=str(path),
                format="epub",
                metadata=metadata,
                content=content_blocks,
            )

        finally:
            doc.close()

    def _extract_by_chapter(
        self, doc: pymupdf.Document, flat: bool
    ) -> tuple[List[ContentBlock], List[str]]:
        """Extract EPUB content chapter-by-chapter.

        Args:
            doc: Open PyMuPDF Document.
            flat: If True, collect text for later concatenation.

        Returns:
            Tuple of (content_blocks, all_text_parts).
        """
        content_blocks: List[ContentBlock] = []
        all_text_parts: List[str] = []

        for chapter_num in range(doc.chapter_count):
            try:
                chapter_text_parts = []
                page_count = doc.chapter_page_count(chapter_num)

                for page_num in range(page_count):
                    try:
                        # Use location-based addressing (chapter, page)
                        page = doc.load_page((chapter_num, page_num))
                        raw_text = page.get_text()
                        chapter_text_parts.append(raw_text)
                    except Exception as e:
                        warnings.warn(
                            f"Error extracting chapter {chapter_num + 1}, "
                            f"page {page_num + 1}: {e}. Continuing.",
                            stacklevel=2
                        )

                chapter_text = "\n".join(chapter_text_parts)
                normalized = normalize_text(chapter_text)

                if flat:
                    all_text_parts.append(normalized)
                else:
                    content_blocks.append(
                        ContentBlock(
                            type="text",
                            text=normalized,
                            chapter=chapter_num + 1,  # 1-indexed
                        )
                    )

            except Exception as e:
                warnings.warn(
                    f"Error processing chapter {chapter_num + 1}: {e}. "
                    "Skipping chapter.",
                    stacklevel=2
                )

        return content_blocks, all_text_parts

    def _extract_by_page(
        self, doc: pymupdf.Document, flat: bool
    ) -> tuple[List[ContentBlock], List[str]]:
        """Extract EPUB content page-by-page (fallback).

        Used when chapter structure is not available or for single-chapter EPUBs.

        Args:
            doc: Open PyMuPDF Document.
            flat: If True, collect text for later concatenation.

        Returns:
            Tuple of (content_blocks, all_text_parts).
        """
        content_blocks: List[ContentBlock] = []
        all_text_parts: List[str] = []

        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                raw_text = page.get_text()
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
            except Exception as e:
                warnings.warn(
                    f"Error extracting page {page_num + 1}: {e}. Continuing.",
                    stacklevel=2
                )

        return content_blocks, all_text_parts

    def needs_ocr(self, path: Path) -> bool:
        """Determine if OCR is needed for this EPUB.

        EPUBs are text-based formats and do not require OCR.

        Args:
            path: Path to the EPUB file.

        Returns:
            Always False - EPUBs are text-based.
        """
        return False
