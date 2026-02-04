# Phase 3: Output & IP Review - Research

**Researched:** 2026-02-03
**Domain:** JSON Output Generation, Vocabulary Consolidation, IP Flagging
**Confidence:** HIGH

## Summary

Phase 3 implements the output generation pipeline: converting classified terms (from Phase 2) into per-document `.vocab.json` files, consolidating multiple vocabularies into a master file, handling deduplication with variant linking, and flagging potentially IP-encumbered terms for human review.

The research confirms this phase can be implemented with the existing stack (Pydantic v2, standard library). The key technical decisions are:
1. **Schema-versioned output** with `schema_version` field for forward compatibility
2. **Content-hash change detection** for incremental updates (more reliable than timestamps)
3. **Confidence-weighted merging** for deduplicates (higher confidence wins, or average if equal)
4. **Dual IP flagging** via blocklist matching + classification tags, with both inline flags and separate review queue

**Primary recommendation:** Use Pydantic models for `.vocab.json` output with schema versioning, implement manifest-based change tracking with content hashes, and generate both `flagged.json` review queue and inline `ip_flag` fields.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0 | Schema definition, JSON serialization | Already in project; model_dump_json with indent |
| pathlib | stdlib | Path manipulation | Already used throughout project |
| hashlib | stdlib | File content hashing for change detection | Standard library, reliable MD5/SHA256 |
| shutil | stdlib | File backup (copy2) before consolidation | Preserves metadata on backup |
| datetime | stdlib | Timestamps for manifest and metadata | ISO format serialization built into Pydantic |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| deepmerge | >=1.1 | Deep dictionary merging | Could use for complex merges, but custom logic simpler for this use case |
| jsonmerge | >=1.9 | Schema-driven JSON merging | Overkill for our specific merge strategy |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Content hash | mtime timestamps | Timestamps unreliable across filesystems, copy operations |
| Custom merge | jsonmerge library | Library is flexible but our merge logic is domain-specific |
| shutil.copy2 | manual file copy | copy2 preserves metadata which helps with debugging |

**Installation:**
```bash
# No additional dependencies required - all stdlib + pydantic already installed
```

## Architecture Patterns

### Recommended Project Structure
```
src/corpora/
├── output/                    # NEW: Output generation module
│   ├── __init__.py
│   ├── vocab_writer.py        # Per-document .vocab.json generation
│   ├── consolidator.py        # Master vocabulary consolidation
│   ├── manifest.py            # Change tracking manifest
│   └── merger.py              # Duplicate merge strategies
├── ip/                        # NEW: IP review module
│   ├── __init__.py
│   ├── blocklist.py           # Blocklist loading and matching
│   ├── detector.py            # IP term detection (blocklist + classification)
│   └── reviewer.py            # Review queue generation
├── models/
│   ├── vocabulary.py          # UPDATE: Add schema_version, ip_flag
│   └── manifest.py            # NEW: Manifest models
└── cli/
    ├── output.py              # NEW: output subcommand
    └── review.py              # NEW: review subcommand (or in output.py)
```

### Pattern 1: Schema-Versioned Output Model
**What:** Include schema version in output for forward compatibility
**When to use:** All .vocab.json files
**Example:**
```python
# Source: Pydantic v2 docs + JSON Schema best practices
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

VOCAB_SCHEMA_VERSION = "1.0"

class VocabularyMetadata(BaseModel):
    """Metadata for a vocabulary output file."""
    schema_version: str = Field(default=VOCAB_SCHEMA_VERSION)
    source_path: str = Field(description="Original source document path")
    source_hash: str = Field(description="MD5 hash of source for change detection")
    extracted_at: datetime = Field(default_factory=datetime.now)
    term_count: int = Field(description="Number of terms in vocabulary")
    classified_count: int = Field(description="Terms with classification")
    flagged_count: int = Field(default=0, description="IP-flagged terms")

class VocabularyEntry(BaseModel):
    """A single vocabulary entry with optional IP flag."""
    # Existing ClassifiedTerm fields
    id: str
    text: str
    source: str
    genre: str = "fantasy"
    intent: str
    pos: str
    axes: dict = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    category: str
    canonical: str
    mood: str
    energy: str = ""
    confidence: float
    secondary_intents: List[str] = Field(default_factory=list)
    # NEW: IP flagging
    ip_flag: Optional[str] = Field(default=None, description="IP flag reason if flagged")

class VocabularyOutput(BaseModel):
    """Complete vocabulary output file schema."""
    metadata: VocabularyMetadata
    entries: List[VocabularyEntry]

    def to_file(self, path: Path) -> None:
        """Write vocabulary to .vocab.json file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
```

### Pattern 2: Content-Hash Change Detection
**What:** Use file content hash for reliable change detection
**When to use:** Manifest tracking for incremental updates
**Example:**
```python
# Source: Python hashlib docs, manifestly patterns
import hashlib
from pathlib import Path
from typing import Dict
from datetime import datetime

from pydantic import BaseModel, Field

def compute_file_hash(path: Path, chunk_size: int = 65536) -> str:
    """Compute MD5 hash of file contents."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

class ManifestEntry(BaseModel):
    """Tracking entry for a processed document."""
    source_path: str
    source_hash: str
    vocab_path: str
    processed_at: datetime
    term_count: int

class CorporaManifest(BaseModel):
    """Manifest tracking processed documents."""
    schema_version: str = "1.0"
    last_updated: datetime = Field(default_factory=datetime.now)
    documents: Dict[str, ManifestEntry] = Field(default_factory=dict)

    def needs_processing(self, source_path: Path) -> bool:
        """Check if document needs (re)processing."""
        key = str(source_path)
        if key not in self.documents:
            return True  # New document
        current_hash = compute_file_hash(source_path)
        return current_hash != self.documents[key].source_hash

    def get_orphaned_vocabs(self, current_sources: list[Path]) -> list[str]:
        """Find vocab files whose sources no longer exist."""
        current_keys = {str(p) for p in current_sources}
        return [
            entry.vocab_path
            for key, entry in self.documents.items()
            if key not in current_keys
        ]
```

### Pattern 3: Confidence-Weighted Merge Strategy
**What:** Merge duplicate terms using confidence scores
**When to use:** Consolidation when same canonical form appears in multiple sources
**Example:**
```python
# Source: Project-specific pattern based on CONTEXT.md decisions
from typing import List
from corpora.models import VocabularyEntry

def merge_duplicates(entries: List[VocabularyEntry]) -> VocabularyEntry:
    """Merge duplicate terms (same canonical form).

    Strategy:
    1. If confidence differs significantly (>0.1), use higher confidence entry as base
    2. Collect all unique sources
    3. Union tags from all entries
    4. Average axis scores (weighted by confidence)
    5. Keep IP flag if any entry is flagged
    """
    if len(entries) == 1:
        return entries[0]

    # Sort by confidence descending
    sorted_entries = sorted(entries, key=lambda e: e.confidence, reverse=True)
    base = sorted_entries[0].model_copy()

    # Collect sources
    all_sources = list(set(e.source for e in entries))
    base.source = "; ".join(all_sources)  # Multiple sources

    # Union tags
    all_tags = set()
    for entry in entries:
        all_tags.update(entry.tags)
    base.tags = sorted(list(all_tags))

    # Weighted average of axes
    total_confidence = sum(e.confidence for e in entries)
    if total_confidence > 0:
        merged_axes = {}
        for axis in ["fire", "water", "earth", "air", "light", "shadow", "life", "void",
                     "force", "binding", "ward", "sight", "mind", "time", "space", "fate"]:
            weighted_sum = sum(
                e.axes.get(axis, 0) * e.confidence
                for e in entries
            )
            merged_axes[axis] = round(weighted_sum / total_confidence, 2)
        base.axes = {k: v for k, v in merged_axes.items() if v > 0}

    # Keep IP flag if any flagged
    for entry in entries:
        if entry.ip_flag:
            base.ip_flag = entry.ip_flag
            break

    # Update confidence to average
    base.confidence = round(sum(e.confidence for e in entries) / len(entries), 2)

    return base
```

### Pattern 4: IP Blocklist Matching
**What:** JSON blocklist organized by franchise for IP detection
**When to use:** During vocabulary output generation
**Example:**
```python
# Source: Project CONTEXT.md decision
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

class IPBlocklist:
    """IP blocklist manager for term flagging."""

    def __init__(self, blocklist_path: Optional[Path] = None):
        self.franchises: Dict[str, Set[str]] = {}
        self._patterns: Dict[str, List[re.Pattern]] = {}
        if blocklist_path and blocklist_path.exists():
            self.load(blocklist_path)

    def load(self, path: Path) -> None:
        """Load blocklist from JSON file.

        Expected format:
        {
            "dnd": ["beholder", "mind flayer", "illithid", ...],
            "warhammer": ["space marine", "chaos", ...],
            "lotr": ["hobbit", "shire", ...]
        }
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for franchise, terms in data.items():
            self.franchises[franchise] = set(t.lower() for t in terms)
            # Pre-compile patterns for efficient matching
            self._patterns[franchise] = [
                re.compile(rf"\b{re.escape(t.lower())}\b")
                for t in terms
            ]

    def check(self, term: str, canonical: str) -> Optional[str]:
        """Check if term matches any blocklist.

        Returns franchise name if matched, None otherwise.
        """
        term_lower = term.lower()
        canonical_lower = canonical.lower()

        for franchise, terms in self.franchises.items():
            # Direct match
            if term_lower in terms or canonical_lower in terms:
                return franchise
            # Pattern match (for multi-word terms)
            for pattern in self._patterns[franchise]:
                if pattern.search(term_lower) or pattern.search(canonical_lower):
                    return franchise

        return None
```

### Pattern 5: Safe Backup Before Consolidation
**What:** Create .bak backup before modifying master vocabulary
**When to use:** Every consolidation operation
**Example:**
```python
# Source: shutil docs, atomic file patterns
import shutil
from pathlib import Path
from datetime import datetime

def backup_and_write(path: Path, content: str) -> Path:
    """Create backup and write new content atomically.

    Returns path to backup file (or None if no existing file).
    """
    backup_path = None

    if path.exists():
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(path, backup_path)

        # Also maintain .bak for easy restore
        latest_backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, latest_backup)

    # Write to temp file first, then rename (atomic on same filesystem)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Atomic replace
    temp_path.replace(path)

    return backup_path
```

### Pattern 6: Change Summary Output
**What:** Report +new, ~updated, -removed on consolidation
**When to use:** After every consolidation operation
**Example:**
```python
# Source: Project CONTEXT.md requirement
from dataclasses import dataclass
from typing import Set

@dataclass
class ConsolidationSummary:
    """Summary of consolidation changes."""
    added: Set[str]      # New canonical terms
    updated: Set[str]    # Terms with changed data
    removed: Set[str]    # Orphaned terms (if removing)
    flagged: Set[str]    # IP-flagged terms

    def __str__(self) -> str:
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} new")
        if self.updated:
            parts.append(f"~{len(self.updated)} updated")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        if self.flagged:
            parts.append(f"!{len(self.flagged)} flagged")
        return ", ".join(parts) if parts else "no changes"

    def is_empty(self) -> bool:
        return not (self.added or self.updated or self.removed)
```

### Anti-Patterns to Avoid
- **Relying on mtime for change detection:** File modification times are unreliable across filesystems, git operations, and file copies. Use content hashes.
- **Modifying master.vocab.json in place:** Always create backup first; a crash mid-write could corrupt the file.
- **Case-sensitive blocklist matching:** IP terms should match case-insensitively ("Beholder" = "beholder").
- **Ignoring confidence during merges:** Without confidence weighting, low-quality classifications can overwrite good ones.
- **Hardcoding IP terms:** Use external JSON blocklist so users can customize without code changes.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Manual dict building | Pydantic model_dump_json | Handles datetime, validation, formatting |
| File hashing | Read entire file to memory | hashlib with chunked reading | Memory-efficient for large files |
| Deep dict merge | Nested loop logic | deepmerge library (if needed) | Edge cases in nested structures |
| Atomic file write | Direct file.write() | Temp file + os.replace | Crash-safe, prevents corruption |
| Path manipulation | String concatenation | pathlib.Path | Cross-platform, cleaner API |

**Key insight:** The standard library handles most output operations well. Pydantic provides robust JSON serialization. The main custom logic is the domain-specific merge strategy.

## Common Pitfalls

### Pitfall 1: Lost Data on Consolidation Crash
**What goes wrong:** Power loss or crash mid-write corrupts master.vocab.json
**Why it happens:** Writing directly to target file without atomic semantics
**How to avoid:** Write to .tmp file, then use os.replace() for atomic rename; create .bak before starting
**Warning signs:** Truncated JSON, empty files after unexpected shutdown

### Pitfall 2: Timestamp-Based Change Detection Failures
**What goes wrong:** Files detected as unchanged when content changed (or vice versa)
**Why it happens:** mtime doesn't update on some filesystems, git checkout resets mtime, copy operations
**How to avoid:** Use content hash (MD5 sufficient for this use case) instead of mtime
**Warning signs:** Incremental updates missing changes, or reprocessing everything

### Pitfall 3: Case-Sensitive IP Matching Missing Variants
**What goes wrong:** "Mind Flayer" not flagged when blocklist has "mind flayer"
**Why it happens:** Direct string comparison without normalization
**How to avoid:** Lowercase both sides before comparison
**Warning signs:** Known IP terms appearing in output unflagged

### Pitfall 4: Memory Issues with Large Vocabularies
**What goes wrong:** OOM when loading/merging many large vocab files
**Why it happens:** Loading all entries into memory at once
**How to avoid:** Stream entries, process in batches, use generators where possible
**Warning signs:** Slow consolidation, memory usage growing unbounded

### Pitfall 5: Orphan Terms Accumulating
**What goes wrong:** Master vocabulary grows with stale terms from deleted source documents
**Why it happens:** No tracking of which terms came from which sources
**How to avoid:** Track source in manifest; on consolidation, identify and handle orphans (flag/remove/keep per strategy)
**Warning signs:** Master vocabulary larger than sum of per-document vocabs

### Pitfall 6: Merge Conflicts Silently Resolved Wrong
**What goes wrong:** Same term classified differently in two sources; wrong classification kept
**Why it happens:** Simple "last write wins" merge strategy
**How to avoid:** Use confidence-weighted merging; log significant disagreements
**Warning signs:** Good classifications overwritten by worse ones

## Code Examples

Verified patterns from official sources:

### Complete Vocab Writer
```python
# Source: Pydantic v2 docs + project patterns
from pathlib import Path
from datetime import datetime
from typing import List

from corpora.models import ClassifiedTerm
from corpora.output.manifest import compute_file_hash

def write_vocab_file(
    classified_terms: List[ClassifiedTerm],
    source_path: Path,
    output_path: Path,
    blocklist: "IPBlocklist" = None,
) -> "VocabularyOutput":
    """Generate .vocab.json file from classified terms.

    Args:
        classified_terms: Terms from Phase 2 classification
        source_path: Original source document path
        output_path: Where to write .vocab.json
        blocklist: Optional IP blocklist for flagging

    Returns:
        VocabularyOutput model (also written to file)
    """
    entries = []
    flagged_count = 0

    for term in classified_terms:
        entry = VocabularyEntry(
            id=term.id,
            text=term.text,
            source=term.source,
            genre=term.genre,
            intent=term.intent,
            pos=term.pos,
            axes=term.axes.model_dump() if hasattr(term.axes, 'model_dump') else term.axes,
            tags=term.tags,
            category=term.category,
            canonical=term.canonical,
            mood=term.mood,
            energy=term.energy,
            confidence=term.confidence,
            secondary_intents=term.secondary_intents,
            ip_flag=None,
        )

        # Check IP blocklist
        if blocklist:
            franchise = blocklist.check(term.text, term.canonical)
            if franchise:
                entry.ip_flag = f"blocklist:{franchise}"
                flagged_count += 1

        entries.append(entry)

    metadata = VocabularyMetadata(
        source_path=str(source_path),
        source_hash=compute_file_hash(source_path),
        extracted_at=datetime.now(),
        term_count=len(entries),
        classified_count=len([e for e in entries if e.confidence > 0.3]),
        flagged_count=flagged_count,
    )

    output = VocabularyOutput(metadata=metadata, entries=entries)
    output.to_file(output_path)

    return output
```

### Consolidation with Change Summary
```python
# Source: Project patterns + CONTEXT.md requirements
import json
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

def consolidate_vocabularies(
    vocab_files: List[Path],
    master_path: Path,
) -> ConsolidationSummary:
    """Consolidate multiple .vocab.json files into master vocabulary.

    Args:
        vocab_files: List of per-document vocabulary files
        master_path: Path for master.vocab.json output

    Returns:
        ConsolidationSummary with change counts
    """
    # Load existing master if present
    existing_canonicals: Dict[str, VocabularyEntry] = {}
    if master_path.exists():
        with open(master_path, encoding="utf-8") as f:
            existing = json.load(f)
        for entry in existing.get("entries", []):
            existing_canonicals[entry["canonical"]] = entry

    # Group entries by canonical form
    by_canonical: Dict[str, List[VocabularyEntry]] = defaultdict(list)
    all_sources = set()

    for vocab_file in vocab_files:
        with open(vocab_file, encoding="utf-8") as f:
            vocab = json.load(f)
        all_sources.add(vocab["metadata"]["source_path"])
        for entry_data in vocab["entries"]:
            entry = VocabularyEntry.model_validate(entry_data)
            by_canonical[entry.canonical].append(entry)

    # Merge duplicates
    merged_entries = []
    added = set()
    updated = set()
    flagged = set()

    for canonical, entries in by_canonical.items():
        merged = merge_duplicates(entries)
        merged_entries.append(merged)

        if canonical not in existing_canonicals:
            added.add(canonical)
        elif merged.model_dump() != existing_canonicals[canonical]:
            updated.add(canonical)

        if merged.ip_flag:
            flagged.add(canonical)

    # Identify removed (orphans)
    new_canonicals = set(by_canonical.keys())
    removed = set(existing_canonicals.keys()) - new_canonicals

    # Create master output
    master_metadata = VocabularyMetadata(
        schema_version=VOCAB_SCHEMA_VERSION,
        source_path="consolidated",
        source_hash="",
        extracted_at=datetime.now(),
        term_count=len(merged_entries),
        classified_count=len([e for e in merged_entries if e.confidence > 0.3]),
        flagged_count=len(flagged),
    )

    master = VocabularyOutput(
        metadata=master_metadata,
        entries=sorted(merged_entries, key=lambda e: e.canonical),
    )

    # Backup and write
    backup_and_write(master_path, master.model_dump_json(indent=2))

    return ConsolidationSummary(
        added=added,
        updated=updated,
        removed=removed,
        flagged=flagged,
    )
```

### Review Queue Generation
```python
# Source: Project CONTEXT.md decision
from pathlib import Path
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

class FlaggedTerm(BaseModel):
    """A term flagged for IP review."""
    canonical: str
    text: str
    source: str
    flag_reason: str
    confidence: float
    category: str
    reviewed: bool = False
    decision: str = ""  # "keep", "remove", "replace"
    notes: str = ""

class ReviewQueue(BaseModel):
    """Review queue for IP-flagged terms."""
    generated_at: datetime = Field(default_factory=datetime.now)
    total_flagged: int
    reviewed_count: int = 0
    terms: List[FlaggedTerm]

    def to_file(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

def generate_review_queue(
    vocab: VocabularyOutput,
    output_path: Path,
) -> ReviewQueue:
    """Generate flagged.json review queue from vocabulary."""
    flagged_terms = []

    for entry in vocab.entries:
        if entry.ip_flag:
            flagged_terms.append(FlaggedTerm(
                canonical=entry.canonical,
                text=entry.text,
                source=entry.source,
                flag_reason=entry.ip_flag,
                confidence=entry.confidence,
                category=entry.category,
            ))

    queue = ReviewQueue(
        total_flagged=len(flagged_terms),
        terms=sorted(flagged_terms, key=lambda t: t.canonical),
    )

    queue.to_file(output_path)
    return queue
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Timestamp-based change detection | Content hash detection | Always better | Reliable incremental processing |
| Simple "last wins" merge | Confidence-weighted merge | Domain best practice | Better classification preservation |
| In-place file modification | Atomic temp+replace | Always better | Crash-safe writes |
| Pydantic v1 .json() | Pydantic v2 .model_dump_json() | 2023 | Better performance, new API |
| Hardcoded IP lists | External JSON blocklist | User configurability | Customizable without code changes |

**Deprecated/outdated:**
- **Pydantic v1 syntax:** Use model_dump(), model_dump_json(), model_validate() not dict(), json(), parse_obj()
- **Manual JSON building:** Pydantic handles serialization including datetime, enums, nested models

## Open Questions

Things that couldn't be fully resolved:

1. **Output location strategy**
   - What we know: CONTEXT.md says "Claude's discretion"
   - Options: Same folder as source (e.g., `book.pdf` -> `book.vocab.json`) vs dedicated `output/` folder
   - Recommendation: Same folder by default with `--output-dir` override; simpler mental model

2. **Orphan handling strategy**
   - What we know: CONTEXT.md says "Claude's discretion"
   - Options: Keep (accumulate), remove (clean), flag (log but keep)
   - Recommendation: Flag by default (log warning, keep terms); `--remove-orphans` for cleanup

3. **Reprocessing trigger logic**
   - What we know: CONTEXT.md says "Claude's discretion"
   - Options: Auto-detect changes vs require `--force`
   - Recommendation: Auto-detect by default (check hash); `--force` to reprocess all

4. **Review decision file format**
   - What we know: CONTEXT.md says "Claude's discretion"
   - What's unclear: How users record review decisions
   - Recommendation: Edit `flagged.json` inline (set reviewed=true, decision=keep/remove/replace); merge back on next consolidation

## Sources

### Primary (HIGH confidence)
- [Pydantic v2 Serialization](https://docs.pydantic.dev/latest/concepts/serialization/) - model_dump_json, custom serializers
- [Python hashlib](https://docs.python.org/3/library/hashlib.html) - File hashing patterns
- [Python shutil](https://docs.python.org/3/library/shutil.html) - copy2 for backups
- [Python pathlib](https://docs.python.org/3/library/pathlib.html) - Path manipulation

### Secondary (MEDIUM confidence)
- [jsonmerge PyPI](https://pypi.org/project/jsonmerge/) - Merge strategy patterns (verified concepts)
- [deepmerge docs](https://deepmerge.readthedocs.io/) - Deep dictionary merging
- [Atomic file writes gist](https://gist.github.com/therightstuff/cbdcbef4010c20acc70d2175a91a321f) - Temp+replace pattern
- [Manifestly GitHub](https://github.com/gdoermann/manifestly) - Manifest-based change detection patterns

### Tertiary (LOW confidence)
- WebSearch results for IP blocklist patterns - general concepts
- Community discussions on JSON schema versioning - common practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib + Pydantic already in project
- Architecture: HIGH - Patterns derived from official docs and project needs
- Pitfalls: HIGH - Common file I/O and data merging issues well documented
- IP flagging: MEDIUM - Domain-specific, but straightforward pattern

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - stable domain, no fast-moving dependencies)
