"""Output subcommands for vocabulary generation and consolidation.

Implements the `corpora output` and `corpora consolidate` commands:
- output: Convert Phase 2 extract JSON to .vocab.json with IP flagging
- consolidate: Merge multiple .vocab.json files into master vocabulary
"""

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from corpora.ip import IPBlocklist, flag_terms, generate_review_queue
from corpora.models import ClassifiedTerm
from corpora.output import (
    CorporaManifest,
    VocabularyOutput,
    consolidate_vocabularies,
    write_vocab_file,
)

# Exit codes per sysexits.h convention
EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2
EXIT_INPUT_ERROR = 64
EXIT_DATA_ERROR = 65
EXIT_NO_INPUT = 66

# Rich console for colored output
console = Console(stderr=True)


def _load_classified_terms(path: Path) -> List[ClassifiedTerm]:
    """Load classified terms from Phase 2 extract JSON output.

    Args:
        path: Path to the JSON file (array of ClassifiedTerm objects).

    Returns:
        List of ClassifiedTerm objects.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If file cannot be parsed.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Handle both array and object formats
    if isinstance(data, list):
        terms = [ClassifiedTerm.model_validate(item) for item in data]
    else:
        raise ValueError("Expected JSON array of classified terms")

    return terms


def _load_blocklist(blocklist_path: Optional[Path], verbose: bool) -> Optional[IPBlocklist]:
    """Load IP blocklist from file if provided.

    Args:
        blocklist_path: Path to blocklist JSON file, or None for default.
        verbose: Whether to show verbose output.

    Returns:
        IPBlocklist instance or None if blocklist doesn't exist.
    """
    if blocklist_path is None:
        # Use default blocklist location
        default_path = Path("data/ip-blocklist.json")
        if default_path.exists():
            blocklist = IPBlocklist(default_path)
            if verbose:
                console.print(f"[cyan]Using blocklist: {default_path}[/cyan]")
            return blocklist
        return None

    if not blocklist_path.exists():
        console.print(f"[yellow]Warning: Blocklist not found: {blocklist_path}[/yellow]")
        return None

    blocklist = IPBlocklist(blocklist_path)
    if verbose:
        console.print(f"[cyan]Using blocklist: {blocklist_path}[/cyan]")
    return blocklist


def output_command(
    input_file: Path = typer.Argument(
        ...,
        help="Phase 2 extract JSON file (array of classified terms)",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output .vocab.json path (default: same dir as input with .vocab.json extension)",
    ),
    blocklist: Optional[Path] = typer.Option(
        None,
        "--blocklist",
        "-b",
        help="IP blocklist JSON file (default: data/ip-blocklist.json)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """Generate vocabulary JSON from classified terms.

    Takes Phase 2 extract output (JSON array of ClassifiedTerm objects) and
    generates a .vocab.json file with IP flagging.

    If any terms are IP-flagged, also generates flagged.json in the same
    directory for human review.

    Examples:
        corpora output extract.json
        corpora output extract.json -o vocab/document.vocab.json
        corpora output extract.json --blocklist custom-blocklist.json -v
    """
    # Load classified terms
    try:
        terms = _load_classified_terms(input_file)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_NO_INPUT)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(EXIT_DATA_ERROR)

    if not terms:
        console.print("[yellow]Warning: No terms found in input file[/yellow]")
        raise typer.Exit(EXIT_SUCCESS)

    if verbose:
        console.print(f"[cyan]Loaded {len(terms)} classified terms[/cyan]")

    # Load blocklist
    blocklist_obj = _load_blocklist(blocklist, verbose)

    # Apply IP flagging
    if blocklist_obj:
        flagged_terms = flag_terms(terms, blocklist_obj)
        flagged_count = sum(1 for t in flagged_terms if t.ip_flag)
        if verbose and flagged_count > 0:
            console.print(f"[yellow]Flagged {flagged_count} terms for IP review[/yellow]")
    else:
        flagged_terms = terms
        flagged_count = sum(1 for t in flagged_terms if t.ip_flag)

    # Determine output path
    if output is None:
        output = input_file.with_suffix(".vocab.json")

    # We need a source path for write_vocab_file - use the input file
    # This is for metadata tracking
    source_path = input_file

    # Write vocabulary file
    vocab_output = write_vocab_file(flagged_terms, source_path, output)

    console.print(f"[green]Generated:[/green] {output}")
    console.print(f"  Terms: {len(terms)}")

    if flagged_count > 0:
        console.print(f"  [yellow]Flagged: {flagged_count}[/yellow]")

        # Generate flagged.json for review
        flagged_path = output.parent / "flagged.json"
        queue = generate_review_queue(vocab_output, flagged_path)
        console.print(f"[yellow]Review queue:[/yellow] {flagged_path} ({queue.total_flagged} terms)")


def consolidate_command(
    vocab_dir: Path = typer.Argument(
        ...,
        help="Directory containing .vocab.json files",
        exists=True,
    ),
    master: Optional[Path] = typer.Option(
        None,
        "--master",
        "-m",
        help="Master vocabulary output path (default: vocab_dir/master.vocab.json)",
    ),
    blocklist: Optional[Path] = typer.Option(
        None,
        "--blocklist",
        "-b",
        help="IP blocklist JSON file (default: data/ip-blocklist.json)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reprocessing of all files (ignore manifest)",
    ),
    remove_orphans: bool = typer.Option(
        False,
        "--remove-orphans",
        help="Remove terms from sources that no longer exist",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """Consolidate vocabulary files into master vocabulary.

    Merges multiple .vocab.json files from a directory into a single
    master.vocab.json with deduplication and IP flagging.

    Uses .corpora-manifest.json to track which files have been processed
    for incremental updates. Use --force to reprocess all files.

    Examples:
        corpora consolidate vocab/
        corpora consolidate vocab/ --master output/master.vocab.json
        corpora consolidate vocab/ --force --remove-orphans -v
    """
    # Find all .vocab.json files
    vocab_files = list(vocab_dir.glob("*.vocab.json"))

    # Exclude master.vocab.json from the list
    master_name = "master.vocab.json"
    vocab_files = [f for f in vocab_files if f.name != master_name]

    if not vocab_files:
        console.print(f"[yellow]No .vocab.json files found in {vocab_dir}[/yellow]")
        raise typer.Exit(EXIT_NO_INPUT)

    if verbose:
        console.print(f"[cyan]Found {len(vocab_files)} vocabulary files[/cyan]")

    # Load manifest for incremental processing
    manifest_path = vocab_dir / ".corpora-manifest.json"
    manifest = CorporaManifest.load(manifest_path)

    # Filter files that need processing (unless --force)
    if not force:
        # Check which vocab files have changed
        files_to_process = []
        for vf in vocab_files:
            # For vocab files, we check the vocab file hash directly
            key = str(vf)
            if key not in manifest.documents:
                files_to_process.append(vf)
            else:
                from corpora.output import compute_file_hash
                current_hash = compute_file_hash(vf)
                if current_hash != manifest.documents[key].source_hash:
                    files_to_process.append(vf)

        if not files_to_process and not remove_orphans:
            console.print("[green]No changes detected. Use --force to reprocess all.[/green]")
            raise typer.Exit(EXIT_SUCCESS)

        if verbose and files_to_process:
            console.print(f"[cyan]Processing {len(files_to_process)} changed files[/cyan]")
    else:
        files_to_process = vocab_files

    # Determine master path
    if master is None:
        master_path = vocab_dir / master_name
    else:
        master_path = master

    # Load blocklist
    blocklist_obj = _load_blocklist(blocklist, verbose)

    # Handle orphan removal
    if remove_orphans:
        # Get orphaned vocab paths
        orphaned = manifest.get_orphaned_vocabs([Path(f) for f in manifest.documents.keys()])
        if orphaned and verbose:
            console.print(f"[yellow]Found {len(orphaned)} orphaned vocabulary files[/yellow]")
        # Orphans will be removed during consolidation by not including them

    # Consolidate vocabularies
    summary = consolidate_vocabularies(
        vocab_files if force or not files_to_process else files_to_process + [f for f in vocab_files if f not in files_to_process],
        master_path,
        blocklist_obj,
    )

    # Update manifest
    from corpora.output import compute_file_hash
    for vf in vocab_files:
        with open(vf, encoding="utf-8") as f:
            vocab_data = json.load(f)
        term_count = len(vocab_data.get("entries", []))

        # Store vocab file itself in manifest (not original source)
        manifest.documents[str(vf)] = CorporaManifest.model_fields["documents"].default_factory().get(
            str(vf),
            type(manifest.documents.get(str(vf), None)) if str(vf) in manifest.documents else None
        )
        from corpora.output.manifest import ManifestEntry
        manifest.documents[str(vf)] = ManifestEntry(
            source_path=str(vf),
            source_hash=compute_file_hash(vf),
            vocab_path=str(vf),
            term_count=term_count,
        )

    manifest.save(manifest_path)

    # Show summary
    console.print(f"[green]Consolidated:[/green] {master_path}")
    console.print(f"  Change summary: {summary}")

    # Generate flagged.json from master if any flagged terms
    if summary.flagged:
        # Load the master vocabulary to generate review queue
        with open(master_path, encoding="utf-8") as f:
            master_data = json.load(f)
        from corpora.output.models import VocabularyMetadata, VocabularyEntry
        master_vocab = VocabularyOutput(
            metadata=VocabularyMetadata.model_validate(master_data["metadata"]),
            entries=[VocabularyEntry.model_validate(e) for e in master_data["entries"]],
        )

        flagged_path = master_path.parent / "flagged.json"
        queue = generate_review_queue(master_vocab, flagged_path)
        console.print(f"[yellow]Review queue:[/yellow] {flagged_path} ({queue.total_flagged} terms)")
