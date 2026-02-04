"""IP blocklist loading and matching for franchise-organized term detection.

This module provides the IPBlocklist class for loading blocklists from JSON
and checking terms against known IP-encumbered franchises.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class IPBlocklist:
    """IP blocklist manager for term flagging.

    Loads a JSON blocklist organized by franchise and provides case-insensitive
    matching for both single and multi-word terms.

    Example blocklist format:
    {
        "dnd": ["beholder", "mind flayer", "illithid", ...],
        "warhammer": ["space marine", "chaos marine", ...],
        "lotr": ["hobbit", "shire", ...]
    }
    """

    def __init__(self, blocklist_path: Optional[Path] = None):
        """Initialize blocklist, optionally loading from file.

        Args:
            blocklist_path: Path to JSON blocklist file. If provided and exists,
                           the blocklist is loaded immediately.
        """
        self.franchises: Dict[str, Set[str]] = {}
        self._patterns: Dict[str, List[re.Pattern]] = {}
        if blocklist_path and blocklist_path.exists():
            self.load(blocklist_path)

    def load(self, path: Path) -> None:
        """Load blocklist from JSON file.

        Expected format:
        {
            "dnd": ["beholder", "mind flayer", "illithid", ...],
            "warhammer": ["space marine", "chaos marine", ...],
            "lotr": ["hobbit", "shire", ...]
        }

        Args:
            path: Path to JSON blocklist file.
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for franchise, terms in data.items():
            # Store lowercase terms in set for O(1) lookup
            self.franchises[franchise] = set(t.lower() for t in terms)
            # Pre-compile regex patterns with word boundaries for multi-word matching
            self._patterns[franchise] = [
                re.compile(rf"\b{re.escape(t.lower())}\b", re.IGNORECASE)
                for t in terms
            ]

    def check(self, term: str, canonical: str) -> Optional[str]:
        """Check if term matches any blocklist entry.

        Checks both the raw term and its canonical form against all franchises.
        Matching is case-insensitive.

        Args:
            term: The raw term text as it appears in source.
            canonical: The normalized/canonical form of the term.

        Returns:
            Franchise name if matched, None otherwise.
        """
        term_lower = term.lower()
        canonical_lower = canonical.lower()

        for franchise, terms in self.franchises.items():
            # Direct exact match (fast path)
            if term_lower in terms or canonical_lower in terms:
                return franchise

            # Pattern match for multi-word terms contained within longer text
            for pattern in self._patterns[franchise]:
                if pattern.search(term_lower) or pattern.search(canonical_lower):
                    return franchise

        return None
