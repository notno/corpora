"""IP term detection combining blocklist and classification flags.

This module provides functions for detecting potentially IP-encumbered terms
using both blocklist matching and classification-time detection.
"""

from typing import List, Optional

from corpora.ip.blocklist import IPBlocklist
from corpora.models.vocabulary import ClassifiedTerm


def detect_ip(
    term: ClassifiedTerm,
    blocklist: Optional[IPBlocklist] = None,
) -> Optional[str]:
    """Detect if a term is potentially IP-encumbered.

    Combines two detection methods:
    1. Blocklist matching (if blocklist provided)
    2. Classification-time detection (if term.ip_flag already set)

    Args:
        term: The classified term to check.
        blocklist: Optional IPBlocklist for franchise matching.

    Returns:
        Combined flag reason if detected, None otherwise.
        Format: "blocklist:dnd" or "classification:ip-suspect"
        or "blocklist:dnd;classification:ip-suspect" for both.
    """
    reasons = []

    # Check blocklist if provided
    if blocklist:
        franchise = blocklist.check(term.text, term.canonical)
        if franchise:
            reasons.append(f"blocklist:{franchise}")

    # Check if term already has ip_flag from classification
    if term.ip_flag:
        # If already has blocklist prefix, avoid duplication
        if not term.ip_flag.startswith("blocklist:"):
            reasons.append(f"classification:{term.ip_flag}")
        elif term.ip_flag not in reasons:
            reasons.append(term.ip_flag)

    if not reasons:
        return None

    return ";".join(reasons)


def flag_terms(
    terms: List[ClassifiedTerm],
    blocklist: Optional[IPBlocklist] = None,
) -> List[ClassifiedTerm]:
    """Batch-process terms with IP detection.

    Applies detect_ip to each term and returns new list with ip_flag set
    where IP concerns are detected.

    Args:
        terms: List of classified terms to process.
        blocklist: Optional IPBlocklist for franchise matching.

    Returns:
        New list of terms with ip_flag field updated where detected.
        Original terms are not modified (immutable updates).
    """
    flagged_terms = []

    for term in terms:
        ip_result = detect_ip(term, blocklist)
        if ip_result:
            # Use model_copy for immutable update
            flagged_term = term.model_copy(update={"ip_flag": ip_result})
            flagged_terms.append(flagged_term)
        else:
            flagged_terms.append(term)

    return flagged_terms
