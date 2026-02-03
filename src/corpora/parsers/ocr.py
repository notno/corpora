"""OCR detection and extraction for scanned documents.

This module provides utilities to detect when OCR is needed for PDF pages
and to perform OCR extraction using PyMuPDF's built-in Tesseract integration.

OCR is an optional feature - the functions gracefully handle missing dependencies.
"""

from typing import TYPE_CHECKING

import pymupdf

from corpora.utils import normalize_text

if TYPE_CHECKING:
    pass


def is_ocr_available() -> bool:
    """Check if OCR dependencies are available.

    Verifies both pytesseract Python package and Tesseract OCR engine
    are installed and functional.

    Returns:
        True if OCR is available, False otherwise.
    """
    try:
        import pytesseract

        # Verify Tesseract is actually installed (not just pytesseract)
        pytesseract.get_tesseract_version()
        return True
    except ImportError:
        # pytesseract not installed
        return False
    except pytesseract.TesseractNotFoundError:
        # pytesseract installed but Tesseract not found
        return False
    except Exception:
        # Other errors (permissions, etc.)
        return False


def needs_ocr_page(
    page: pymupdf.Page,
    text_threshold: int = 50,
    coverage_threshold: float = 0.8,
) -> bool:
    """Determine if a single page needs OCR.

    Uses heuristics to detect scanned/image-based pages:
    1. Check if extracted text is sufficient
    2. Check if images cover most of the page
    3. If large image coverage AND minimal text, OCR is needed

    Args:
        page: PyMuPDF Page object to check.
        text_threshold: Minimum characters to consider "has text" (default: 50).
        coverage_threshold: Image coverage ratio to trigger OCR check (default: 0.8).

    Returns:
        True if page likely needs OCR, False if native extraction is sufficient.
    """
    # First, check if we already have enough text
    text = page.get_text().strip()
    if len(text) >= text_threshold:
        return False  # Has enough text, no OCR needed

    # Get page dimensions
    page_rect = page.rect
    page_area = abs(page_rect)

    if page_area == 0:
        return False  # Invalid page

    # Check for images covering significant area
    image_list = page.get_images()
    if not image_list:
        return False  # No images, just sparse text

    for img in image_list:
        try:
            xref = img[0]
            img_rect = page.get_image_bbox(xref)
            if img_rect:
                # Calculate what fraction of page the image covers
                intersection = img_rect & page_rect
                coverage = abs(intersection) / page_area

                # If image covers >threshold of page AND text is minimal
                if coverage >= coverage_threshold:
                    return True
        except Exception:
            # Skip problematic images
            continue

    return False


def needs_ocr_document(
    doc: pymupdf.Document,
    sample_pages: int = 3,
    text_threshold: int = 50,
    coverage_threshold: float = 0.8,
) -> bool:
    """Check if a document likely needs OCR by sampling pages.

    Performs a pre-flight check before prompting the user about OCR.
    Checks the first N pages (or all if fewer) and returns True if
    any sampled page appears to need OCR.

    Args:
        doc: Open PyMuPDF Document.
        sample_pages: Number of pages to sample (default: 3).
        text_threshold: Minimum characters per page (passed to needs_ocr_page).
        coverage_threshold: Image coverage ratio (passed to needs_ocr_page).

    Returns:
        True if ANY sampled page likely needs OCR, False otherwise.
    """
    pages_to_check = min(sample_pages, len(doc))

    for page_num in range(pages_to_check):
        page = doc[page_num]
        if needs_ocr_page(page, text_threshold, coverage_threshold):
            return True

    return False


def extract_with_ocr(page: pymupdf.Page, language: str = "eng") -> str:
    """Extract text from a page using OCR.

    Uses PyMuPDF's built-in OCR integration which leverages Tesseract.
    The extracted text is normalized for consistent output.

    Args:
        page: PyMuPDF Page object to extract text from.
        language: Tesseract language code (default: "eng" for English).

    Returns:
        Normalized extracted text from OCR.

    Raises:
        RuntimeError: If OCR is not available.
    """
    if not is_ocr_available():
        raise RuntimeError(
            "OCR is not available. Please install pytesseract and Tesseract OCR. "
            "On Windows: choco install tesseract, pip install pytesseract. "
            "On macOS: brew install tesseract, pip install pytesseract. "
            "On Linux: apt install tesseract-ocr, pip install pytesseract."
        )

    # Use PyMuPDF's OCR integration
    # This creates a TextPage with OCR results
    textpage = page.get_textpage_ocr(language=language)
    text = page.get_text(textpage=textpage)

    return normalize_text(text)
