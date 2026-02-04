"""Parse subcommand for extracting text from documents.

Implements the `corpora parse` command with all flags specified in CONTEXT.md:
- Input: file, folder, or glob pattern
- Output: stdout or file/directory via -o
- OCR: auto-detect with prompting, or --ocr/--no-ocr overrides
- Error handling: continue by default, --fail-fast to stop
- Structure: --flat to flatten, default preserves pages/chapters
"""

import glob
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from corpora.models import DocumentOutput
from corpora.parsers import EPUBParser, PDFParser
from corpora.parsers.ocr import (
    extract_with_ocr,
    is_ocr_available,
    needs_ocr_document,
    needs_ocr_page,
)
from corpora.utils import log_error

# Exit codes per RESEARCH.md recommendations (sysexits.h convention)
EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2
EXIT_INPUT_ERROR = 64
EXIT_DATA_ERROR = 65
EXIT_NO_INPUT = 66

# Rich console for colored output
console = Console(stderr=True)
output_console = Console()


def get_parser(path: Path):
    """Get the appropriate parser for a file.

    Args:
        path: Path to the file.

    Returns:
        Parser instance if supported format, None otherwise.
    """
    parsers = [PDFParser(), EPUBParser()]
    for parser in parsers:
        if parser.can_parse(path):
            return parser
    return None


def resolve_input_files(input_path: Path) -> List[Path]:
    """Resolve input path to list of files.

    Handles:
    - Single file: returns [file]
    - Directory: returns all .pdf and .epub files
    - Glob pattern: returns matching files

    Args:
        input_path: File, directory, or glob pattern.

    Returns:
        List of resolved file paths.
    """
    # Check if it's a glob pattern (contains * or ?)
    path_str = str(input_path)
    if "*" in path_str or "?" in path_str:
        # Glob pattern
        matched = [Path(p) for p in glob.glob(path_str, recursive=True)]
        return [p for p in matched if p.is_file() and p.suffix.lower() in (".pdf", ".epub")]

    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        files = []
        for ext in (".pdf", ".epub", ".PDF", ".EPUB"):
            files.extend(input_path.glob(f"*{ext}"))
        return sorted(files)

    return []


def parse_command(
    input_path: Path = typer.Argument(
        ...,
        help="File, folder, or glob pattern to parse",
        exists=False,  # We handle existence check ourselves for glob support
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file or directory (default: stdout)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        help="Output format (currently only json supported)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output showing progress",
    ),
    ocr: Optional[bool] = typer.Option(
        None,
        "--ocr/--no-ocr",
        help="Force OCR on/off (default: auto-detect)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts (for OCR)",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        help="Stop on first error (default: continue)",
    ),
    partial: bool = typer.Option(
        False,
        "--partial",
        help="Output partial results on error",
    ),
    flat: bool = typer.Option(
        False,
        "--flat",
        help="Flatten document structure (no pages/chapters)",
    ),
) -> None:
    """Parse document(s) and extract text content.

    Extract text from PDF and EPUB files into structured JSON format.
    Supports single files, directories, and glob patterns.

    Examples:
        corpora parse document.pdf
        corpora parse ./docs/
        corpora parse "*.pdf" -o output/
        corpora parse scanned.pdf --ocr -y
    """
    # Resolve input files
    files = resolve_input_files(input_path)

    if not files:
        console.print(f"[red]Error:[/red] No files found matching '{input_path}'")
        raise typer.Exit(EXIT_NO_INPUT)

    if verbose:
        console.print(f"Found {len(files)} file(s) to process")

    # Determine output mode
    output_is_dir = output and (output.is_dir() or len(files) > 1)
    if output_is_dir and output and not output.exists():
        output.mkdir(parents=True, exist_ok=True)

    results: List[DocumentOutput] = []
    errors_occurred = False

    for file_path in files:
        if verbose:
            console.print(f"Processing: {file_path}")

        # Get parser
        parser = get_parser(file_path)
        if not parser:
            error_msg = f"Unsupported file format: {file_path.suffix}"
            console.print(f"[yellow]Warning:[/yellow] {error_msg}")
            log_error(ValueError(error_msg), str(file_path))
            errors_occurred = True
            if fail_fast:
                raise typer.Exit(EXIT_DATA_ERROR)
            continue

        try:
            # Check if file exists
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Handle OCR for PDFs
            use_ocr = False
            if file_path.suffix.lower() == ".pdf":
                use_ocr = _handle_ocr_decision(
                    file_path, ocr, yes, verbose
                )

            # Extract content
            result = _extract_with_ocr_support(
                parser, file_path, flat, use_ocr, verbose
            )
            results.append(result)

            # Write output if per-file output
            if output_is_dir and output:
                out_file = output / f"{file_path.stem}.json"
                result.to_json_file(str(out_file))
                if verbose:
                    console.print(f"  Written to: {out_file}")

        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            log_error(e, str(file_path))
            errors_occurred = True
            if fail_fast:
                raise typer.Exit(EXIT_INPUT_ERROR)

        except Exception as e:
            console.print(f"[red]Error processing {file_path}:[/red] {e}")
            log_error(e, str(file_path))
            errors_occurred = True

            if partial and results:
                # Output what we have so far
                if verbose:
                    console.print("[yellow]Outputting partial results[/yellow]")
                _write_results(results, output, output_is_dir)

            if fail_fast:
                raise typer.Exit(EXIT_DATA_ERROR)

    # Write final output
    if results:
        if not output_is_dir:
            _write_results(results, output, output_is_dir)
        if verbose:
            console.print(f"[green]Successfully processed {len(results)} file(s)[/green]")
    elif not errors_occurred:
        console.print("[yellow]No content extracted[/yellow]")

    if errors_occurred and not fail_fast:
        console.print("[yellow]Some files had errors. See corpora-errors.log[/yellow]")


def _handle_ocr_decision(
    file_path: Path,
    ocr_flag: Optional[bool],
    yes: bool,
    verbose: bool,
) -> bool:
    """Determine whether to use OCR for a PDF file.

    Args:
        file_path: Path to the PDF file.
        ocr_flag: User's --ocr/--no-ocr flag (None = auto-detect).
        yes: If True, skip prompts.
        verbose: If True, show OCR detection info.

    Returns:
        True if OCR should be used, False otherwise.
    """
    # Explicit flags override auto-detection
    if ocr_flag is True:
        if not is_ocr_available():
            console.print(
                "[red]Error:[/red] --ocr specified but OCR is not available. "
                "Install pytesseract and Tesseract OCR."
            )
            raise typer.Exit(EXIT_DATA_ERROR)
        return True

    if ocr_flag is False:
        return False

    # Auto-detect: check if document needs OCR
    import pymupdf
    doc = pymupdf.open(str(file_path))
    try:
        needs_ocr = needs_ocr_document(doc)
    finally:
        doc.close()

    if not needs_ocr:
        return False

    # Document appears to need OCR
    if verbose:
        console.print("  [yellow]Document appears to be scanned/image-based[/yellow]")

    if not is_ocr_available():
        console.print(
            "[yellow]Warning:[/yellow] Document may need OCR but OCR is not available. "
            "Results may be incomplete. Install pytesseract and Tesseract OCR for better results."
        )
        return False

    # Prompt user unless --yes
    if yes:
        if verbose:
            console.print("  Using OCR (--yes flag)")
        return True

    # Interactive prompt
    if sys.stdin.isatty():
        use_ocr = typer.confirm(
            "This document appears scanned. Use OCR? (slower but better results)",
            default=False,
        )
        return use_ocr
    else:
        # Non-interactive, don't use OCR without explicit flag
        console.print(
            "[yellow]Warning:[/yellow] Document may need OCR. "
            "Use --ocr flag or --yes to enable OCR in non-interactive mode."
        )
        return False


def _extract_with_ocr_support(
    parser,
    file_path: Path,
    flat: bool,
    use_ocr: bool,
    verbose: bool,
) -> DocumentOutput:
    """Extract content from a document, optionally using OCR.

    Args:
        parser: Parser instance to use.
        file_path: Path to the document.
        flat: Whether to flatten structure.
        use_ocr: Whether to use OCR for pages that need it.
        verbose: Whether to show progress.

    Returns:
        DocumentOutput with extracted content.
    """
    if not use_ocr or file_path.suffix.lower() != ".pdf":
        # Standard extraction
        return parser.extract(file_path, flat=flat)

    # OCR-enabled extraction for PDFs
    import pymupdf
    from corpora.models import ContentBlock

    doc = pymupdf.open(str(file_path))
    try:
        metadata = dict(doc.metadata) if doc.metadata else {}
        content_blocks = []
        all_text_parts = []
        ocr_page_count = 0

        for page_num, page in enumerate(doc):
            if needs_ocr_page(page):
                # Use OCR for this page
                if verbose:
                    console.print(f"  OCR on page {page_num + 1}")
                text = extract_with_ocr(page)
                ocr_page_count += 1
            else:
                # Standard extraction
                from corpora.utils import normalize_text
                text = normalize_text(page.get_text(sort=True))

            if flat:
                all_text_parts.append(text)
            else:
                content_blocks.append(
                    ContentBlock(
                        type="text",
                        text=text,
                        page=page_num + 1,
                    )
                )

        if flat:
            combined_text = "\n\n".join(all_text_parts)
            content_blocks = [ContentBlock(type="text", text=combined_text)]

        if verbose and ocr_page_count > 0:
            console.print(f"  OCR applied to {ocr_page_count} page(s)")

        return DocumentOutput(
            source=str(file_path),
            format="pdf",
            ocr_used=ocr_page_count > 0,
            metadata=metadata,
            content=content_blocks,
        )

    finally:
        doc.close()


def _write_results(
    results: List[DocumentOutput],
    output: Optional[Path],
    output_is_dir: bool,
) -> None:
    """Write extraction results to output destination.

    Args:
        results: List of DocumentOutput objects.
        output: Output path (file or directory) or None for stdout.
        output_is_dir: Whether output is a directory.
    """
    if output is None:
        # Write to stdout
        if len(results) == 1:
            output_console.print(results[0].model_dump_json(indent=2))
        else:
            # Multiple results - output as JSON array
            import json
            combined = [r.model_dump() for r in results]
            output_console.print(json.dumps(combined, indent=2, default=str))
    elif not output_is_dir:
        # Single output file
        if len(results) == 1:
            results[0].to_json_file(str(output))
        else:
            # Multiple results to single file - output as JSON array
            import json
            combined = [r.model_dump() for r in results]
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                json.dump(combined, f, indent=2, default=str)
