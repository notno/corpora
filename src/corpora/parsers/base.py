"""Abstract base class for document parsers."""

from abc import ABC, abstractmethod
from pathlib import Path

from corpora.models import DocumentOutput


class BaseParser(ABC):
    """Abstract base class defining the parser interface.

    All document parsers (PDF, EPUB, etc.) must implement this interface
    to ensure consistent handling across different document formats.
    """

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file type.

        Args:
            path: Path to the file to check.

        Returns:
            True if this parser can handle the file, False otherwise.
        """
        pass

    @abstractmethod
    def extract(self, path: Path, flat: bool = False) -> DocumentOutput:
        """Extract text and metadata from document.

        Args:
            path: Path to the document file.
            flat: If True, concatenate all content into a single block.
                  If False, preserve structure (pages/chapters).

        Returns:
            DocumentOutput containing extracted text and metadata.

        Raises:
            ExtractionError: If extraction fails.
        """
        pass

    @abstractmethod
    def needs_ocr(self, path: Path) -> bool:
        """Determine if OCR is needed for this document.

        Args:
            path: Path to the document file.

        Returns:
            True if OCR is needed for proper text extraction,
            False if native extraction is sufficient.
        """
        pass
