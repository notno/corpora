# Phase 4: Batch Processing - Research

**Researched:** 2026-02-04
**Domain:** Python Parallel Processing, Progress Tracking, Fault Tolerance
**Confidence:** HIGH

## Summary

Phase 4 implements batch document processing with parallelization, progress tracking, and fault tolerance. Users can point the CLI at a folder, process multiple PDF/EPUB documents in parallel, see live progress, and resume interrupted runs.

The research confirms:
1. **concurrent.futures.ThreadPoolExecutor** is the correct choice for I/O-bound document processing (API calls dominate runtime, not CPU)
2. **Rich progress bars** support multiple tasks natively and integrate well with threading
3. **Existing manifest system** (.corpora-manifest.json from Phase 3) provides resume capability without new infrastructure
4. **tenacity** already handles per-worker rate limiting with exponential backoff - no shared coordinator needed for small batches
5. **sysexits.h convention** provides clear exit code semantics including partial success

**Primary recommendation:** Use ThreadPoolExecutor with `min(8, os.cpu_count() or 4)` workers, Rich progress with multiple task bars, and the existing manifest for resume tracking. Each worker operates independently with tenacity backoff.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| concurrent.futures | stdlib | Thread pool for parallel document processing | Built-in, well-documented, perfect for I/O-bound work |
| rich | >=13.0 | Progress bars with multiple tasks | Already in project, supports threads natively |
| tenacity | >=8.0 | Per-worker rate limit handling | Already in project, exponential backoff with jitter |
| pydantic | >=2.0 | Manifest and result models | Already in project for Phase 3 manifest |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| os | stdlib | CPU count detection | Auto-detecting worker count |
| pathlib | stdlib | File discovery and path handling | Glob patterns for batch input |
| typing | stdlib | Type hints for batch results | BatchResult, ProcessingStats models |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadPoolExecutor | asyncio | asyncio requires more code changes, threads simpler for existing sync code |
| ThreadPoolExecutor | ProcessPoolExecutor | Overkill for I/O-bound work, harder to share state |
| Multiple progress bars | Single aggregate bar | Multiple shows per-document status, better UX |

**Installation:**
```bash
# No new dependencies - all already in project
pip install rich tenacity  # Already installed
```

## Architecture Patterns

### Recommended Project Structure
```
src/corpora/
├── cli/
│   ├── batch.py          # NEW: batch processing CLI command
│   └── main.py           # Add batch command registration
├── batch/                # NEW: Batch processing module
│   ├── __init__.py
│   ├── processor.py      # BatchProcessor class with parallel execution
│   ├── progress.py       # Progress tracking with Rich integration
│   └── models.py         # BatchResult, ProcessingStats, DocumentStatus
├── output/
│   └── manifest.py       # EXISTING: Reuse for resume tracking
└── utils/
    └── errors.py         # EXISTING: Error logging
```

### Pattern 1: ThreadPoolExecutor with as_completed
**What:** Submit all documents to thread pool, process results as they complete
**When to use:** Always for batch processing (yields results in completion order, enables live progress)
**Example:**
```python
# Source: Python docs - https://docs.python.org/3/library/concurrent.futures.html
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Iterator
import os

def process_batch(
    documents: List[Path],
    max_workers: int | None = None,
) -> Iterator[tuple[Path, Result | Exception]]:
    """Process documents in parallel, yielding results as they complete."""
    if max_workers is None:
        max_workers = min(8, os.cpu_count() or 4)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_doc = {
            executor.submit(process_single_document, doc): doc
            for doc in documents
        }

        # Yield results as they complete (not in submission order)
        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                result = future.result()
                yield (doc, result)
            except Exception as exc:
                yield (doc, exc)
```

### Pattern 2: Rich Progress with Multiple Task Bars
**What:** Show individual progress bar per document being processed
**When to use:** When processing multiple documents in parallel
**Example:**
```python
# Source: Rich docs - https://rich.readthedocs.io/en/stable/progress.html
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console

console = Console(stderr=True)

def process_with_progress(documents: List[Path], workers: int) -> dict:
    """Process documents with per-document progress bars."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        # Overall progress
        overall = progress.add_task("Processing documents...", total=len(documents))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_doc = {
                executor.submit(process_document, doc): doc
                for doc in documents
            }

            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    # Update overall progress
                    progress.update(overall, advance=1, description=f"Completed: {doc.name}")
                except Exception as e:
                    progress.update(overall, advance=1, description=f"[red]Failed: {doc.name}[/red]")
```

### Pattern 3: Manifest-Based Resume
**What:** Check manifest before processing, skip completed documents
**When to use:** Always (enables Ctrl+C and resume)
**Example:**
```python
# Source: Existing Phase 3 manifest implementation
from corpora.output import CorporaManifest

def get_documents_to_process(
    all_documents: List[Path],
    manifest: CorporaManifest,
    force: bool = False,
) -> List[Path]:
    """Filter documents that need processing based on manifest."""
    if force:
        return all_documents

    return [
        doc for doc in all_documents
        if manifest.needs_processing(doc)  # Checks hash change
    ]
```

### Pattern 4: Continue-on-Error with Retry
**What:** Retry failed documents once, continue with others if still failing
**When to use:** Default behavior (per CONTEXT.md decision)
**Example:**
```python
# Source: Project pattern + tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

def process_with_retry(doc: Path) -> DocumentResult:
    """Process a single document with one retry on failure."""
    try:
        return _process_document_impl(doc)
    except Exception as first_error:
        # Log first attempt failure
        log_error(first_error, str(doc), "corpora-errors.log")
        try:
            # Retry once
            return _process_document_impl(doc)
        except Exception as retry_error:
            # Log retry failure and return error result
            log_error(retry_error, str(doc), "corpora-errors.log")
            raise  # Let caller handle
```

### Anti-Patterns to Avoid
- **ProcessPoolExecutor for I/O-bound work:** Threads are better for API calls, processes add overhead
- **Shared rate limiter across workers:** Unnecessary complexity for small batches (5-20 docs), tenacity per-worker is sufficient
- **Single progress bar for batch:** Loses per-document visibility, harder to see what's happening
- **Stopping on first error:** Wastes time on batch runs, continue and report at end
- **Reprocessing partial documents:** Risk of inconsistent state, reprocess from scratch is safer

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel execution | Manual threading | concurrent.futures.ThreadPoolExecutor | Handles lifecycle, exceptions, results properly |
| Progress display | print() statements | Rich Progress | Live updates, multiple tasks, terminal handling |
| Resume tracking | Custom checkpoint file | Existing CorporaManifest | Already tracks hashes, timestamps, completion |
| Rate limiting | Shared semaphore | tenacity per-worker backoff | Jitter prevents thundering herd, simpler |
| Error logging | Custom logger | Existing log_error() | Already formats timestamps, handles append |
| CPU count detection | Hardcoded value | os.cpu_count() | Adapts to different machines |

**Key insight:** The existing codebase already has most of the infrastructure needed. Phase 4 is about orchestrating existing capabilities (manifest, error logging, progress) with parallel execution, not building new primitives.

## Common Pitfalls

### Pitfall 1: Deadlock from Nested Futures
**What goes wrong:** Worker submits another future and waits on it, pool exhaustion
**Why it happens:** Document processing calls API that uses its own executor
**How to avoid:** Never wait on futures within worker functions; API calls should be synchronous within workers
**Warning signs:** Batch hangs with some documents stuck at "processing"

### Pitfall 2: Progress Bar Flickering
**What goes wrong:** Progress display becomes unreadable with frequent updates
**Why it happens:** Updating progress from multiple threads too rapidly
**How to avoid:** Update overall progress only when documents complete, not on every API call
**Warning signs:** Terminal output is garbled, progress bar redraws constantly

### Pitfall 3: Memory Exhaustion on Large Batches
**What goes wrong:** OOM when processing many documents simultaneously
**Why it happens:** Loading all documents into memory at once
**How to avoid:** Stream documents through the pipeline, don't accumulate results in memory
**Warning signs:** Memory usage grows linearly with batch size

### Pitfall 4: Lost Work on Ctrl+C
**What goes wrong:** User interrupts, loses all progress
**Why it happens:** Manifest only saved at end of batch
**How to avoid:** Update manifest after each successful document, not at end of batch
**Warning signs:** Rerunning batch starts from scratch after interruption

### Pitfall 5: Overwhelming API Rate Limits
**What goes wrong:** All workers hit 429 simultaneously, exponential retry storms
**Why it happens:** Workers retry at same intervals
**How to avoid:** tenacity's wait_exponential has built-in jitter; use it with `jitter=(1, 3)` to desynchronize retries
**Warning signs:** Log shows multiple workers backing off at same timestamps

### Pitfall 6: Incorrect Exit Code for Partial Success
**What goes wrong:** Exit 0 when some documents failed, breaks CI pipelines
**Why it happens:** Only checking if any results, not if any errors
**How to avoid:** Track error count, use distinct exit codes for full success vs partial
**Warning signs:** CI passes but some vocabulary files missing

## Code Examples

Verified patterns from official sources and project conventions:

### Worker Count Calculation
```python
# Source: Python docs - concurrent.futures default formula
import os

def get_worker_count(user_specified: int | None = None) -> int:
    """Calculate worker count for batch processing.

    For I/O-bound API work:
    - User override takes precedence
    - Default: min(8, CPU count) - capped at 8 to avoid overwhelming API
    - Minimum: 1 for sequential fallback
    """
    if user_specified is not None:
        return max(1, user_specified)

    cpu_count = os.cpu_count() or 4
    return min(8, cpu_count)
```

### Exit Code Convention
```python
# Source: sysexits.h - https://man7.org/linux/man-pages/man3/sysexits.h.3head.html
# Exit codes per sysexits.h convention (matches existing CLI modules)
EXIT_SUCCESS = 0        # All documents processed successfully
EXIT_USAGE_ERROR = 2    # Invalid arguments
EXIT_PARTIAL = 75       # EX_TEMPFAIL: Some documents failed (partial success)
EXIT_INPUT_ERROR = 64   # EX_USAGE: Bad input path
EXIT_DATA_ERROR = 65    # EX_DATAERR: Invalid document format
EXIT_NO_INPUT = 66      # EX_NOINPUT: No documents found
EXIT_SOFTWARE = 70      # EX_SOFTWARE: Internal error

def determine_exit_code(total: int, succeeded: int, failed: int) -> int:
    """Determine exit code based on processing results."""
    if failed == 0:
        return EXIT_SUCCESS
    elif succeeded > 0:
        return EXIT_PARTIAL  # Some succeeded, some failed
    else:
        return EXIT_DATA_ERROR  # All failed
```

### Batch Command CLI Structure
```python
# Source: Project pattern from cli/parse.py and cli/output.py
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console(stderr=True)

def batch_command(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing PDF/EPUB documents to process",
        exists=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for .vocab.json files (default: same as input)",
    ),
    workers: Optional[int] = typer.Option(
        None,
        "--workers",
        "-w",
        help="Number of parallel workers (default: auto-detect from CPU cores)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Reprocess all documents, ignoring manifest",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress progress output, show only errors and summary",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed per-document output",
    ),
) -> None:
    """Process a folder of documents with parallel execution.

    Extracts vocabulary from all PDF and EPUB files in the input directory,
    with progress tracking and fault tolerance. Interrupted runs can be
    resumed automatically.

    Examples:
        corpora batch ./documents/
        corpora batch ./documents/ -o ./vocab/ --workers 4
        corpora batch ./documents/ --force --quiet
    """
    pass  # Implementation
```

### Error Log File Format
```python
# Source: Existing corpora/utils/errors.py pattern
# Error log location: corpora-errors.log in working directory
# Format: [ISO timestamp] [source] ErrorType: message

# Example log entries:
# [2026-02-04T15:30:45] [document.pdf] RateLimitError: 429 Too Many Requests
# [2026-02-04T15:30:47] [document.pdf] RateLimitError: Retry failed after backoff

def log_batch_error(
    error: Exception,
    document: Path,
    attempt: int = 1,
) -> None:
    """Log a batch processing error with attempt number."""
    from corpora.utils import log_error
    context = f"{document.name} (attempt {attempt})"
    log_error(error, context, "corpora-errors.log")
```

### Summary Statistics Display
```python
# Source: Project pattern + Rich formatting
from rich.table import Table

def show_batch_summary(
    total: int,
    succeeded: int,
    failed: int,
    terms_extracted: int,
    terms_flagged: int,
    elapsed_seconds: float,
) -> None:
    """Display batch processing summary."""
    console.print("\n[bold]Batch Processing Summary[/bold]")
    console.print(f"  Documents: {succeeded}/{total} succeeded")
    if failed > 0:
        console.print(f"  [red]Failed: {failed}[/red]")
    console.print(f"  Terms extracted: {terms_extracted:,}")
    if terms_flagged > 0:
        console.print(f"  [yellow]Terms flagged: {terms_flagged}[/yellow]")
    console.print(f"  Time: {elapsed_seconds:.1f}s")
    if failed > 0:
        console.print(f"  [yellow]See corpora-errors.log for failure details[/yellow]")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sequential processing | ThreadPoolExecutor parallel | Always available | 2-8x faster for I/O-bound |
| print() progress | Rich Progress with tasks | Rich 10+ (2020) | Professional UX |
| Custom checkpoint files | Existing manifest system | Phase 3 | No new code needed |
| Shared rate limiter | Per-worker tenacity backoff | tenacity 8+ | Simpler, jitter prevents storms |

**Deprecated/outdated:**
- `multiprocessing.Pool` for I/O-bound work: Use `concurrent.futures` instead (cleaner API)
- Custom progress bar implementations: Use Rich (handles terminal edge cases)

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal worker count cap**
   - What we know: Default formula is `min(8, cpu_count)`, API rate limits are per-account
   - What's unclear: Whether 8 workers might still overwhelm API for some accounts
   - Recommendation: Start with 8, monitor, reduce if 429s are excessive

2. **Pipeline execution style (per CONTEXT.md Claude's discretion)**
   - What we know: Two options - full pipeline per document OR step batching (all parse, then all extract, etc.)
   - Full pipeline per document: Simpler, results stream in, lower memory
   - Step batching: Could use Anthropic Batch API more efficiently across documents
   - Recommendation: **Full pipeline per document** - simpler, works with existing code, typical batch is 5-20 docs so Batch API efficiency gain is marginal

3. **API rate coordination strategy (per CONTEXT.md Claude's discretion)**
   - What we know: Tenacity per-worker backoff with jitter works well for avoiding thundering herd
   - Shared semaphore across workers adds complexity for marginal benefit
   - Recommendation: **Independent backoff per worker** - tenacity's jitter desynchronizes retries naturally

## Sources

### Primary (HIGH confidence)
- [Python concurrent.futures docs](https://docs.python.org/3/library/concurrent.futures.html) - ThreadPoolExecutor, as_completed
- [Rich Progress docs](https://rich.readthedocs.io/en/stable/progress.html) - Multiple tasks, threading support
- [sysexits.h man page](https://man7.org/linux/man-pages/man3/sysexits.h.3head.html) - Exit code conventions
- [tenacity docs](https://tenacity.readthedocs.io/) - Exponential backoff with jitter

### Secondary (MEDIUM confidence)
- [Super Fast Python ThreadPoolExecutor guide](https://superfastpython.com/threadpoolexecutor-in-python/) - Best practices
- [Project Phase 3 manifest implementation](file://src/corpora/output/manifest.py) - Resume infrastructure

### Tertiary (LOW confidence)
- WebSearch results on batch processing patterns - various sources, cross-verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, documented patterns
- Architecture: HIGH - Based on existing codebase patterns and official docs
- Pitfalls: MEDIUM - Combination of official docs and experience patterns
- Exit codes: HIGH - sysexits.h is well-documented standard

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - stable domain, libraries mature)
