"""IP flagging module for detecting potentially IP-encumbered terms.

This module provides:
- IPBlocklist: Load and match against franchise-organized blocklists
- detect_ip: Check a term against blocklist and classification flags
- flag_terms: Batch-process terms with IP detection
- FlaggedTerm, ReviewQueue: Models for review queue output
- generate_review_queue: Generate flagged.json for human review
"""

from corpora.ip.blocklist import IPBlocklist
from corpora.ip.detector import detect_ip, flag_terms
from corpora.ip.reviewer import FlaggedTerm, ReviewQueue, generate_review_queue

__all__ = [
    "IPBlocklist",
    "detect_ip",
    "flag_terms",
    "FlaggedTerm",
    "ReviewQueue",
    "generate_review_queue",
]
