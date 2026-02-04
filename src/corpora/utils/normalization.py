"""Text normalization utilities for document extraction."""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalize extracted text for consistent output.

    Applies the following transformations:
    - NFKC Unicode normalization (decomposes ligatures like "fi" -> "fi")
    - Normalize line endings to \\n
    - Collapse multiple spaces to single (preserving newlines)
    - Collapse 3+ newlines to max 2
    - Strip whitespace from each line
    - Strip leading/trailing whitespace

    Args:
        text: The raw extracted text to normalize.

    Returns:
        Normalized text with consistent formatting.
    """
    # Unicode normalization - NFKC for compatibility decomposition
    # This handles ligatures (fi, fl, ffi) and other composed characters
    text = unicodedata.normalize("NFKC", text)

    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse multiple newlines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
