"""IP flagging module for detecting potentially IP-encumbered terms.

This module provides:
- IPBlocklist: Load and match against franchise-organized blocklists
- detect_ip: Check a term against blocklist and classification flags
- flag_terms: Batch-process terms with IP detection
"""

from corpora.ip.blocklist import IPBlocklist
from corpora.ip.detector import detect_ip, flag_terms

__all__ = ["IPBlocklist", "detect_ip", "flag_terms"]
