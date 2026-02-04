"""Consolidator module for merging vocabularies into master file.

This module provides functions for consolidating multiple per-document
.vocab.json files into a single master.vocab.json with deduplication,
IP flagging, backup, and change tracking.
"""

import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from corpora.ip.blocklist import IPBlocklist
from corpora.output.merger import ConsolidationSummary, merge_duplicates
from corpora.output.models import (
    VOCAB_SCHEMA_VERSION,
    VocabularyEntry,
    VocabularyMetadata,
    VocabularyOutput,
)


def backup_and_write(path: Path, content: str) -> Optional[Path]:
    """Create backup and write new content atomically.

    If the file already exists:
    1. Creates a timestamped backup (e.g., master.20260204_061500.bak)
    2. Creates a simple .bak for easy restore (e.g., master.vocab.json.bak)
    3. Writes to temp file first, then atomic replace

    Args:
        path: Path to write the file to.
        content: Content to write.

    Returns:
        Path to timestamped backup file, or None if no backup was needed.
    """
    backup_path = None

    if path.exists():
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(path, backup_path)

        # Also create simple .bak for easy restore
        latest_backup = Path(str(path) + ".bak")
        shutil.copy2(path, latest_backup)

    # Write to temp file first
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Atomic replace (as atomic as possible on Windows)
    temp_path.replace(path)

    return backup_path


def consolidate_vocabularies(
    vocab_files: List[Path],
    master_path: Path,
    blocklist: Optional[IPBlocklist] = None,
) -> ConsolidationSummary:
    """Consolidate multiple .vocab.json files into a master vocabulary.

    Process:
    1. Load existing master if present (for change detection)
    2. Load all vocab files and group entries by canonical form
    3. Apply merge_duplicates to each group
    4. Apply IP detection if blocklist provided
    5. Track added/updated/removed/flagged
    6. Use backup_and_write for safe master update
    7. Sort entries by canonical for consistent output

    Args:
        vocab_files: List of per-document vocabulary files to consolidate.
        master_path: Path for the master.vocab.json output.
        blocklist: Optional IPBlocklist for IP term flagging.

    Returns:
        ConsolidationSummary with change counts.
    """
    # Load existing master if present (for change detection)
    existing_entries: Dict[str, dict] = {}
    if master_path.exists():
        with open(master_path, encoding="utf-8") as f:
            existing = json.load(f)
        for entry in existing.get("entries", []):
            existing_entries[entry["canonical"]] = entry

    # Group entries by canonical form
    by_canonical: Dict[str, List[VocabularyEntry]] = defaultdict(list)

    for vocab_file in vocab_files:
        with open(vocab_file, encoding="utf-8") as f:
            vocab = json.load(f)
        for entry_data in vocab["entries"]:
            entry = VocabularyEntry.model_validate(entry_data)
            by_canonical[entry.canonical].append(entry)

    # Merge duplicates
    merged_entries: List[VocabularyEntry] = []
    added: set = set()
    updated: set = set()
    flagged: set = set()

    for canonical, entries in by_canonical.items():
        # Merge all entries with same canonical form
        merged = merge_duplicates(entries)

        # Apply IP detection if blocklist provided
        if blocklist:
            franchise = blocklist.check(merged.text, merged.canonical)
            if franchise and not merged.ip_flag:
                merged = VocabularyEntry.model_validate({
                    **merged.model_dump(),
                    "ip_flag": f"blocklist:{franchise}",
                })

        merged_entries.append(merged)

        # Track changes
        if canonical not in existing_entries:
            added.add(canonical)
        else:
            # Compare serialized form for changes
            existing_dict = existing_entries[canonical]
            merged_dict = merged.model_dump()
            # Don't count IP flag changes as "updated" if that's the only difference
            if _has_changes(existing_dict, merged_dict):
                updated.add(canonical)

        if merged.ip_flag:
            flagged.add(canonical)

    # Identify removed (orphans)
    new_canonicals = set(by_canonical.keys())
    removed = set(existing_entries.keys()) - new_canonicals

    # Sort entries by canonical for consistent output
    merged_entries.sort(key=lambda e: e.canonical)

    # Create master metadata
    classified_count = sum(1 for e in merged_entries if e.confidence > 0.3)

    master_metadata = VocabularyMetadata(
        schema_version=VOCAB_SCHEMA_VERSION,
        source_path="consolidated",
        source_hash="",  # Not applicable for consolidated output
        term_count=len(merged_entries),
        classified_count=classified_count,
        flagged_count=len(flagged),
    )

    # Build master output
    master = VocabularyOutput(
        metadata=master_metadata,
        entries=merged_entries,
    )

    # Backup and write
    backup_and_write(master_path, master.model_dump_json(indent=2))

    return ConsolidationSummary(
        added=added,
        updated=updated,
        removed=removed,
        flagged=flagged,
    )


def _has_changes(old: dict, new: dict) -> bool:
    """Check if entry has meaningful changes (ignoring ip_flag).

    Args:
        old: Existing entry as dict.
        new: New entry as dict.

    Returns:
        True if there are changes beyond just ip_flag.
    """
    # Make copies without ip_flag for comparison
    old_copy = {k: v for k, v in old.items() if k != "ip_flag"}
    new_copy = {k: v for k, v in new.items() if k != "ip_flag"}
    return old_copy != new_copy
