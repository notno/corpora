"""Batch processor for parallel document processing.

This module provides the BatchProcessor class for processing multiple documents
in parallel with fault tolerance, retry logic, and manifest-based resumability.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterator, List, Optional

from corpora.batch.models import BatchConfig, BatchSummary, DocumentResult, DocumentStatus
from corpora.output.manifest import CorporaManifest


# Supported file extensions for batch processing
SUPPORTED_EXTENSIONS = {".pdf", ".epub"}


class BatchProcessor:
    """Processes multiple documents in parallel with fault tolerance.

    Uses ThreadPoolExecutor for parallel processing, updates manifest after
    each document for safe interruption, and retries failed documents once.

    Example:
        config = BatchConfig(input_dir=Path("./docs"), output_dir=Path("./output"))
        processor = BatchProcessor(config)

        for result in processor.process():
            print(f"{result.source_path}: {result.status} ({result.term_count} terms)")

        summary = processor.run()
        print(f"Processed {summary.processed}/{summary.total_documents}")
    """

    def __init__(
        self,
        config: BatchConfig,
        manifest_path: Optional[Path] = None,
        on_document_complete: Optional[Callable[[DocumentResult], None]] = None,
    ):
        """Initialize the batch processor.

        Args:
            config: Batch processing configuration.
            manifest_path: Path to manifest file. Defaults to output_dir/.corpora-manifest.json
            on_document_complete: Optional callback invoked after each document completes.
        """
        self.config = config
        self.manifest_path = manifest_path or (
            config.output_dir / ".corpora-manifest.json"
        )
        self.manifest = CorporaManifest.load(self.manifest_path)
        self.on_document_complete = on_document_complete

    def discover_documents(self) -> List[Path]:
        """Find all supported documents in input directory.

        Returns:
            Sorted list of paths to PDF and EPUB files.
        """
        documents = []
        for ext in SUPPORTED_EXTENSIONS:
            documents.extend(self.config.input_dir.glob(f"*{ext}"))
        return sorted(documents)

    def _process_single_document(self, source: Path) -> DocumentResult:
        """Process a single document through the full pipeline.

        Pipeline: parse -> extract -> classify -> output
        Returns DocumentResult with status and term count.

        Args:
            source: Path to the source document.

        Returns:
            DocumentResult with processing outcome.
        """
        start_time = time.time()

        # Import here to avoid circular imports
        from corpora.classification import ClassificationClient
        from corpora.extraction import TermExtractor
        from corpora.ip import IPBlocklist
        from corpora.output import write_vocab_file
        from corpora.parsers import EPUBParser, PDFParser

        try:
            # 1. Parse document
            ext = source.suffix.lower()
            if ext == ".pdf":
                parser = PDFParser()
            elif ext == ".epub":
                parser = EPUBParser()
            else:
                raise ValueError(f"Unsupported format: {ext}")

            doc_output = parser.parse(source)

            # 2. Extract text
            text_parts = [block.text for block in doc_output.content if block.text]
            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                # No text content - return success with 0 terms
                return DocumentResult(
                    source_path=source,
                    status=DocumentStatus.SUCCESS,
                    term_count=0,
                    duration_seconds=time.time() - start_time,
                )

            # 3. Extract term candidates
            extractor = TermExtractor()
            candidates = extractor.extract(full_text)

            if not candidates:
                # No candidates found - return success with 0 terms
                return DocumentResult(
                    source_path=source,
                    status=DocumentStatus.SUCCESS,
                    term_count=0,
                    duration_seconds=time.time() - start_time,
                )

            # 4. Classify terms using sync API (parallel-friendly)
            client = ClassificationClient()
            classified_terms = []
            for term in candidates:
                try:
                    result = client.classify_term(
                        term=term.text,
                        source=doc_output.source,
                        lemma=term.lemma,
                        pos=term.pos,
                    )
                    classified_terms.append(result)
                except Exception:
                    # Skip failed terms, continue with others
                    pass

            # 5. Apply IP blocklist detection if configured
            if self.config.blocklist_path and self.config.blocklist_path.exists():
                blocklist = IPBlocklist(self.config.blocklist_path)
                for term in classified_terms:
                    if term.ip_flag is None:
                        # Only check if not already flagged by Claude
                        franchise = blocklist.check(term.text, term.canonical)
                        if franchise:
                            term.ip_flag = f"blocklist:{franchise}"

            # 6. Write vocabulary file
            vocab_path = self.config.output_dir / f"{source.stem}.vocab.json"
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

            vocab_output = write_vocab_file(
                classified_terms=classified_terms,
                source_path=source,
                output_path=vocab_path,
            )

            return DocumentResult(
                source_path=source,
                status=DocumentStatus.SUCCESS,
                term_count=len(vocab_output.entries),
                vocab_path=vocab_path,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            return DocumentResult(
                source_path=source,
                status=DocumentStatus.FAILED,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _process_with_retry(self, source: Path) -> DocumentResult:
        """Process document with one retry on failure.

        Args:
            source: Path to the source document.

        Returns:
            DocumentResult from first successful attempt or second attempt.
        """
        result = self._process_single_document(source)
        if result.status == DocumentStatus.FAILED:
            # Retry once
            result = self._process_single_document(source)
        return result

    def process(self) -> Iterator[DocumentResult]:
        """Process all documents, yielding results as they complete.

        Uses ThreadPoolExecutor for parallel processing.
        Updates manifest after EACH document completes.

        Yields:
            DocumentResult for each document as it completes.
        """
        documents = self.discover_documents()

        if not documents:
            return

        # Determine which documents need processing
        to_process = []
        for doc in documents:
            if self.config.force_reprocess or self.manifest.needs_processing(doc):
                to_process.append(doc)
            else:
                # Yield skipped result immediately
                result = DocumentResult(
                    source_path=doc,
                    status=DocumentStatus.SKIPPED,
                )
                if self.on_document_complete:
                    self.on_document_complete(result)
                yield result

        if not to_process:
            return

        # Process in parallel
        max_workers = min(self.config.max_workers, os.cpu_count() or 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_doc = {
                executor.submit(self._process_with_retry, doc): doc
                for doc in to_process
            }

            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = DocumentResult(
                        source_path=doc,
                        status=DocumentStatus.FAILED,
                        error=str(e),
                    )

                # Update manifest IMMEDIATELY after each document
                if result.status == DocumentStatus.SUCCESS and result.vocab_path:
                    self.manifest.update_entry(
                        source=result.source_path,
                        vocab=result.vocab_path,
                        term_count=result.term_count,
                    )
                    self.manifest.save(self.manifest_path)

                if self.on_document_complete:
                    self.on_document_complete(result)

                yield result

    def run(self) -> BatchSummary:
        """Process all documents and return summary.

        Convenience method that collects all results and returns
        aggregate statistics.

        Returns:
            BatchSummary with processing statistics.
        """
        start_time = time.time()
        results = list(self.process())

        processed = sum(1 for r in results if r.status == DocumentStatus.SUCCESS)
        skipped = sum(1 for r in results if r.status == DocumentStatus.SKIPPED)
        failed = sum(1 for r in results if r.status == DocumentStatus.FAILED)
        total_terms = sum(r.term_count for r in results)
        errors = [r.error for r in results if r.error]

        return BatchSummary(
            total_documents=len(results),
            processed=processed,
            skipped=skipped,
            failed=failed,
            total_terms=total_terms,
            duration_seconds=time.time() - start_time,
            errors=errors,
        )
