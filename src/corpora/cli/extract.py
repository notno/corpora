"""Extract subcommand for vocabulary extraction and classification.

Implements the `corpora extract` command for the vocabulary extraction pipeline:
- Input: Phase 1 JSON output from `corpora parse`
- Preview: --preview shows term count, sample, and estimated cost
- Progress: Progress bar by default, term-by-term in verbose mode (-v)
- Classification: --sync for synchronous API, default for batch API
- Output: JSON array of ClassifiedTerm objects
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from corpora.models import DocumentOutput, ClassifiedTerm, CandidateTerm
from corpora.extraction import TermExtractor
from corpora.classification import ClassificationClient, BatchClassifier

# Exit codes per RESEARCH.md recommendations (sysexits.h convention)
EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2
EXIT_INPUT_ERROR = 64
EXIT_DATA_ERROR = 65
EXIT_NO_INPUT = 66

# Rich console for colored output
console = Console(stderr=True)
output_console = Console()


def load_document(path: Path) -> DocumentOutput:
    """Load a Phase 1 JSON document.

    Args:
        path: Path to the JSON file.

    Returns:
        DocumentOutput parsed from the file.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If file cannot be parsed as DocumentOutput.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    try:
        return DocumentOutput.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid document format: {e}")


def _show_preview(
    candidates: List[CandidateTerm],
    source: str,
    use_batch: bool,
) -> None:
    """Show preview mode output with term count, sample, and cost estimate.

    Args:
        candidates: List of extracted term candidates.
        source: Source document identifier.
        use_batch: Whether batch mode would be used.
    """
    console.print(f"\n[bold]Preview: {source}[/bold]\n")
    console.print(f"[cyan]Terms extracted:[/cyan] {len(candidates)}")

    if candidates:
        console.print(f"\n[cyan]Sample terms:[/cyan]")
        sample_count = min(10, len(candidates))
        for term in candidates[:sample_count]:
            console.print(f"  - {term.text} ({term.pos})")
        if len(candidates) > sample_count:
            console.print(f"  ... and {len(candidates) - sample_count} more")

    # Cost estimate
    client = ClassificationClient()
    estimate = client.estimate_cost(len(candidates), use_batch=use_batch)

    console.print(f"\n[cyan]Estimated cost:[/cyan]")
    console.print(f"  Mode: {'Batch API (50% savings)' if use_batch else 'Sync API'}")
    console.print(f"  Input tokens: ~{estimate['est_input_tokens']:,}")
    console.print(f"  Output tokens: ~{estimate['est_output_tokens']:,}")
    console.print(f"  Estimated cost: [green]${estimate['est_cost_usd']:.4f}[/green]")
    console.print()


def _classify_sync(
    candidates: List[CandidateTerm],
    source: str,
    verbose: bool,
) -> List[ClassifiedTerm]:
    """Classify terms using synchronous API with progress bar.

    Args:
        candidates: List of term candidates to classify.
        source: Source document identifier.
        verbose: Whether to show term-by-term output.

    Returns:
        List of ClassifiedTerm objects.
    """
    client = ClassificationClient()
    results: List[ClassifiedTerm] = []
    errors: List[str] = []

    if verbose:
        console.print(f"\n[bold]Classifying {len(candidates)} terms...[/bold]\n")
        for i, term in enumerate(candidates, 1):
            console.print(f"[{i}/{len(candidates)}] {term.text}...", end=" ")
            try:
                result = client.classify_term(
                    term=term.text,
                    source=source,
                    lemma=term.lemma,
                    pos=term.pos,
                )
                results.append(result)
                console.print(f"[green]{result.category}[/green]")
            except Exception as e:
                console.print(f"[red]error: {e}[/red]")
                errors.append(f"{term.text}: {e}")
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Classifying terms...", total=len(candidates))
            for term in candidates:
                try:
                    result = client.classify_term(
                        term=term.text,
                        source=source,
                        lemma=term.lemma,
                        pos=term.pos,
                    )
                    results.append(result)
                except Exception as e:
                    errors.append(f"{term.text}: {e}")
                progress.update(task, advance=1)

    if errors:
        console.print(f"\n[yellow]Warning: {len(errors)} term(s) failed classification[/yellow]")
        if verbose:
            for error in errors:
                console.print(f"  - {error}")

    return results


def _classify_batch(
    candidates: List[CandidateTerm],
    source: str,
    verbose: bool,
    batch_size: int,
) -> List[ClassifiedTerm]:
    """Classify terms using Batch API with polling.

    Args:
        candidates: List of term candidates to classify.
        source: Source document identifier.
        verbose: Whether to show detailed output.
        batch_size: Number of terms per batch (for future chunking).

    Returns:
        List of ClassifiedTerm objects.
    """
    classifier = BatchClassifier()
    results: List[ClassifiedTerm] = []
    errors: List[str] = []

    # Prepare term tuples for batch API
    term_tuples = [
        (term.text, source, term.lemma, term.pos)
        for term in candidates
    ]

    if verbose:
        console.print(f"\n[bold]Creating batch request for {len(term_tuples)} terms...[/bold]")

    # Create batch
    batch_id = classifier.create_batch(term_tuples)

    if verbose:
        console.print(f"[cyan]Batch ID:[/cyan] {batch_id}")
        console.print("[cyan]Polling for results...[/cyan]\n")

    # Poll with progress callback
    def on_progress(completed: int, total: int) -> None:
        if verbose:
            console.print(f"  Progress: {completed}/{total}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Waiting for batch completion...", total=None)

        def progress_callback(completed: int, total: int) -> None:
            progress.update(task, total=total, completed=completed)
            if verbose:
                console.print(f"  Batch progress: {completed}/{total}")

        classifier.poll_batch(batch_id, poll_interval=10, on_progress=progress_callback)

    # Stream results
    if verbose:
        console.print("\n[cyan]Processing results...[/cyan]")

    for idx, result in classifier.stream_results(batch_id, source):
        if isinstance(result, ClassifiedTerm):
            results.append(result)
            if verbose:
                console.print(f"  [{idx}] {result.text}: {result.category}")
        else:
            # Error dict
            errors.append(f"Term {idx}: {result.get('error', 'unknown error')}")
            if verbose:
                console.print(f"  [{idx}] [red]error: {result.get('error')}[/red]")

    if errors:
        console.print(f"\n[yellow]Warning: {len(errors)} term(s) failed classification[/yellow]")

    return results


def _write_results(
    results: List[ClassifiedTerm],
    output: Optional[Path],
    verbose: bool,
) -> None:
    """Write classification results to output destination.

    Args:
        results: List of ClassifiedTerm objects.
        output: Output path or None for stdout.
        verbose: Whether to show verbose output.
    """
    # Convert to JSON-serializable format
    output_data = [term.model_dump() for term in results]

    if output is None:
        # Write to stdout
        output_console.print(json.dumps(output_data, indent=2))
    else:
        # Write to file
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        if verbose:
            console.print(f"\n[green]Results written to {output}[/green]")


def extract_command(
    input_file: Path = typer.Argument(
        ...,
        help="Phase 1 JSON file from 'corpora parse'",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        help="Show term count, sample, and cost estimate without API calls",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show term-by-term classification output",
    ),
    sync: bool = typer.Option(
        False,
        "--sync",
        help="Use synchronous API instead of Batch API",
    ),
    batch_size: int = typer.Option(
        50,
        "--batch-size",
        help="Terms per batch (for future chunking)",
    ),
) -> None:
    """Extract and classify vocabulary from parsed documents.

    Takes Phase 1 JSON output from 'corpora parse' and extracts vocabulary
    candidates using spaCy, then classifies them using Claude API.

    Examples:
        corpora extract document.json --preview
        corpora extract document.json -o vocab.json
        corpora extract document.json --sync -v
    """
    # Load document
    try:
        doc = load_document(input_file)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_NO_INPUT)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_DATA_ERROR)

    # Extract text from content blocks
    text_parts = [block.text for block in doc.content if block.text]
    full_text = "\n\n".join(text_parts)

    if not full_text.strip():
        console.print("[yellow]Warning: No text content in document[/yellow]")
        raise typer.Exit(EXIT_DATA_ERROR)

    # Extract candidates
    if verbose:
        console.print(f"[cyan]Extracting terms from {input_file}...[/cyan]")

    extractor = TermExtractor()
    candidates = extractor.extract(full_text)

    if not candidates:
        console.print("[yellow]No vocabulary candidates found in document[/yellow]")
        # Write empty result
        _write_results([], output, verbose)
        raise typer.Exit(EXIT_SUCCESS)

    # Preview mode - show stats and exit
    if preview:
        _show_preview(candidates, doc.source, use_batch=not sync)
        raise typer.Exit(EXIT_SUCCESS)

    # Classification mode
    if verbose:
        console.print(f"[cyan]Found {len(candidates)} candidate terms[/cyan]")

    if sync:
        results = _classify_sync(candidates, doc.source, verbose)
    else:
        results = _classify_batch(candidates, doc.source, verbose, batch_size)

    # Write results
    _write_results(results, output, verbose)

    if verbose:
        console.print(f"\n[green]Successfully classified {len(results)} terms[/green]")
