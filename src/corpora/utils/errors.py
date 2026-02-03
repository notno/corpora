"""Custom exceptions and error logging for corpora."""

from datetime import datetime
from pathlib import Path


class ExtractionError(Exception):
    """Base exception for document extraction failures.

    Raised when text extraction from a document fails for any reason,
    such as malformed documents, unsupported formats, or I/O errors.
    """

    pass


class OCRRequiredError(ExtractionError):
    """Raised when OCR is needed but unavailable.

    This occurs when a document (typically a scanned PDF) yields
    insufficient text via native extraction and OCR libraries
    are not installed or OCR is disabled.
    """

    pass


def log_error(
    error: Exception,
    source: str,
    log_path: str = "corpora-errors.log"
) -> None:
    """Append a timestamped error entry to the log file.

    Writes errors in a consistent format for later analysis:
    [ISO timestamp] [source] ErrorType: message

    Args:
        error: The exception that occurred.
        source: The source file or context where the error occurred.
        log_path: Path to the error log file (default: corpora-errors.log).
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    error_type = type(error).__name__
    message = str(error)

    log_entry = f"[{timestamp}] [{source}] {error_type}: {message}\n"

    log_file = Path(log_path)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
