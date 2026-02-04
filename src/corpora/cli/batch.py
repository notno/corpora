"""Batch processing subcommand for folder-level document processing.

Implements the `corpora batch` command for processing entire folders:
- Discovers all PDF/EPUB files in input directory
- Processes in parallel with configurable workers
- Shows Rich progress bar with document-level updates
- Resumes interrupted runs via manifest
- Outputs per-document .vocab.json files
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from corpora.batch import (
    BatchConfig,
    BatchProcessor,
    BatchSummary,
    DocumentResult,
    DocumentStatus,
)

# Exit codes per sysexits.h convention (from RESEARCH.md)
EXIT_SUCCESS = 0
EXIT_PARTIAL = 75      # EX_TEMPFAIL: Some documents failed
EXIT_NO_INPUT = 66     # EX_NOINPUT: No documents found
EXIT_INPUT_ERROR = 64  # EX_USAGE: Bad input path

# Rich consoles
console = Console(stderr=True)


def _format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    td = timedelta(seconds=seconds)
    if td.total_seconds() < 60:
        return f"{td.total_seconds():.1f}s"
    elif td.total_seconds() < 3600:
        minutes = int(td.total_seconds() // 60)
        secs = int(td.total_seconds() % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"


def _print_summary(summary: BatchSummary, quiet: bool = False) -> None:
    """Print batch processing summary."""
    console.print()
    console.print("[bold]Batch Processing Complete[/bold]")
    console.print()
    console.print(f"  [cyan]Documents:[/cyan] {summary.total_documents} total")
    console.print(f"    - Processed: [green]{summary.processed}[/green]")
    console.print(f"    - Skipped:   [yellow]{summary.skipped}[/yellow] (already processed)")
    if summary.failed > 0:
        console.print(f"    - Failed:    [red]{summary.failed}[/red]")
    console.print()
    console.print(f"  [cyan]Terms extracted:[/cyan] {summary.total_terms:,}")
    console.print(f"  [cyan]Duration:[/cyan] {_format_duration(summary.duration_seconds)}")

    if summary.errors and not quiet:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for error in summary.errors[:10]:  # Show first 10
            console.print(f"  - {error}")
        if len(summary.errors) > 10:
            console.print(f"  ... and {len(summary.errors) - 10} more")


def _write_error_log(summary: BatchSummary, output_dir: Path) -> None:
    """Write errors to log file if any failures occurred."""
    if not summary.errors:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "batch-errors.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Batch Processing Errors\n")
        f.write("=======================\n\n")
        for error in summary.errors:
            f.write(f"- {error}\n")

    console.print(f"\n[yellow]Error log written to: {log_path}[/yellow]")


def batch_command(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing PDF/EPUB documents to process",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for .vocab.json files (default: input_dir/output)",
    ),
    workers: int = typer.Option(
        0,
        "--workers",
        "-w",
        help="Number of parallel workers (0 = auto-detect based on CPU cores)",
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
        help="Quiet mode: show only errors and final summary",
    ),
    blocklist: Optional[Path] = typer.Option(
        None,
        "--blocklist",
        "-b",
        help="Path to IP blocklist JSON (default: data/ip-blocklist.json)",
    ),
) -> None:
    """Process all documents in a folder with parallel execution.

    Discovers PDF and EPUB files in INPUT_DIR, processes them in parallel,
    and outputs .vocab.json files. Progress is displayed with a Rich progress
    bar. Interrupted runs automatically resume from where they stopped.

    Examples:
        corpora batch ./documents
        corpora batch ./documents -o ./vocab --workers 4
        corpora batch ./documents --force --quiet
    """
    # Resolve output directory
    if output_dir is None:
        output_dir = input_dir / "output"

    # Auto-detect workers if not specified
    if workers <= 0:
        workers = min(8, os.cpu_count() or 4)

    # Default blocklist path
    if blocklist is None:
        default_blocklist = Path("data/ip-blocklist.json")
        if default_blocklist.exists():
            blocklist = default_blocklist

    # Create config
    config = BatchConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        max_workers=workers,
        force_reprocess=force,
        blocklist_path=blocklist,
    )

    # Discover documents first to show count
    processor = BatchProcessor(config)
    documents = processor.discover_documents()

    if not documents:
        console.print(f"[yellow]No PDF or EPUB files found in {input_dir}[/yellow]")
        raise typer.Exit(EXIT_NO_INPUT)

    if not quiet:
        console.print(f"[cyan]Found {len(documents)} document(s) in {input_dir}[/cyan]")
        console.print(f"[cyan]Output directory: {output_dir}[/cyan]")
        console.print(f"[cyan]Workers: {workers}[/cyan]")
        if force:
            console.print("[yellow]Force mode: reprocessing all documents[/yellow]")
        console.print()

    # Process with progress display
    results = []

    if quiet:
        # Quiet mode: no progress bar, just process
        for result in processor.process():
            results.append(result)
            if result.status == DocumentStatus.FAILED:
                console.print(f"[red]FAILED:[/red] {result.source_path.name}: {result.error}")
    else:
        # Normal mode: Rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing documents...", total=len(documents))

            def on_complete(result: DocumentResult) -> None:
                results.append(result)
                progress.update(task, advance=1)

                # Show per-document result
                if result.status == DocumentStatus.SUCCESS:
                    progress.console.print(
                        f"  [green]OK[/green] {result.source_path.name} "
                        f"({result.term_count} terms, {result.duration_seconds:.1f}s)"
                    )
                elif result.status == DocumentStatus.SKIPPED:
                    progress.console.print(
                        f"  [yellow]SKIP[/yellow] {result.source_path.name} (already processed)"
                    )
                else:
                    progress.console.print(
                        f"  [red]FAIL[/red] {result.source_path.name}: {result.error}"
                    )

            # Create new processor with callback
            processor = BatchProcessor(config, on_document_complete=on_complete)

            # Consume the generator
            for _ in processor.process():
                pass

    # Generate summary
    processed = sum(1 for r in results if r.status == DocumentStatus.SUCCESS)
    skipped = sum(1 for r in results if r.status == DocumentStatus.SKIPPED)
    failed = sum(1 for r in results if r.status == DocumentStatus.FAILED)
    total_terms = sum(r.term_count for r in results)
    errors = [f"{r.source_path.name}: {r.error}" for r in results if r.error]
    duration = sum(r.duration_seconds for r in results)

    summary = BatchSummary(
        total_documents=len(results),
        processed=processed,
        skipped=skipped,
        failed=failed,
        total_terms=total_terms,
        duration_seconds=duration,
        errors=errors,
    )

    # Print summary
    _print_summary(summary, quiet)

    # Write error log if any failures
    if summary.errors:
        _write_error_log(summary, output_dir)

    # Exit code based on results
    if failed > 0:
        raise typer.Exit(EXIT_PARTIAL)
    raise typer.Exit(EXIT_SUCCESS)
