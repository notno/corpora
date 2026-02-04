"""Tests for the batch processing module.

Tests cover:
- Batch models (DocumentResult, BatchConfig, BatchSummary)
- BatchProcessor document discovery
- BatchProcessor manifest-based resumability
- CLI command integration
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from corpora.batch import (
    BatchConfig,
    BatchProcessor,
    BatchSummary,
    DocumentResult,
    DocumentStatus,
)
from corpora.cli.main import app


runner = CliRunner()


# ============================================================================
# Model Tests
# ============================================================================

class TestDocumentResult:
    """Tests for DocumentResult model."""

    def test_success_result(self):
        result = DocumentResult(
            source_path=Path("test.pdf"),
            status=DocumentStatus.SUCCESS,
            term_count=42,
            vocab_path=Path("test.vocab.json"),
            duration_seconds=1.5,
        )
        assert result.status == DocumentStatus.SUCCESS
        assert result.term_count == 42
        assert result.error is None

    def test_failed_result(self):
        result = DocumentResult(
            source_path=Path("test.pdf"),
            status=DocumentStatus.FAILED,
            error="Parse error",
        )
        assert result.status == DocumentStatus.FAILED
        assert result.error == "Parse error"
        assert result.term_count == 0

    def test_skipped_result(self):
        result = DocumentResult(
            source_path=Path("test.pdf"),
            status=DocumentStatus.SKIPPED,
        )
        assert result.status == DocumentStatus.SKIPPED


class TestBatchConfig:
    """Tests for BatchConfig model."""

    def test_default_workers(self, tmp_path):
        config = BatchConfig(
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
        )
        assert config.max_workers == 4
        assert config.force_reprocess is False

    def test_custom_workers(self, tmp_path):
        config = BatchConfig(
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
            max_workers=8,
        )
        assert config.max_workers == 8

    def test_worker_bounds_minimum(self, tmp_path):
        with pytest.raises(ValueError):
            BatchConfig(
                input_dir=tmp_path,
                output_dir=tmp_path / "output",
                max_workers=0,
            )

    def test_worker_bounds_maximum(self, tmp_path):
        with pytest.raises(ValueError):
            BatchConfig(
                input_dir=tmp_path,
                output_dir=tmp_path / "output",
                max_workers=20,
            )


class TestBatchSummary:
    """Tests for BatchSummary model."""

    def test_summary_creation(self):
        summary = BatchSummary(
            total_documents=10,
            processed=7,
            skipped=2,
            failed=1,
            total_terms=500,
            duration_seconds=30.5,
            errors=["test.pdf: error"],
        )
        assert summary.total_documents == 10
        assert summary.processed == 7
        assert summary.failed == 1

    def test_exit_code_success(self):
        summary = BatchSummary(
            total_documents=5,
            processed=5,
            skipped=0,
            failed=0,
            total_terms=100,
            duration_seconds=10.0,
        )
        assert summary.get_exit_code() == 0

    def test_exit_code_partial(self):
        summary = BatchSummary(
            total_documents=5,
            processed=3,
            skipped=0,
            failed=2,
            total_terms=60,
            duration_seconds=10.0,
        )
        assert summary.get_exit_code() == 75

    def test_exit_code_no_input(self):
        summary = BatchSummary(
            total_documents=0,
            processed=0,
            skipped=0,
            failed=0,
            total_terms=0,
            duration_seconds=0.0,
        )
        assert summary.get_exit_code() == 66


# ============================================================================
# Processor Tests
# ============================================================================

class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_discover_documents(self, tmp_path):
        """Test document discovery finds PDF and EPUB files."""
        # Create test files
        (tmp_path / "doc1.pdf").touch()
        (tmp_path / "doc2.epub").touch()
        (tmp_path / "doc3.txt").touch()  # Should be ignored
        (tmp_path / "doc4.PDF").touch()  # Case sensitivity

        config = BatchConfig(
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
        )
        processor = BatchProcessor(config)
        docs = processor.discover_documents()

        # Should find pdf and epub, not txt
        names = [d.name for d in docs]
        assert "doc1.pdf" in names
        assert "doc2.epub" in names
        assert "doc3.txt" not in names

    def test_discover_empty_directory(self, tmp_path):
        """Test discovery returns empty list for empty directory."""
        config = BatchConfig(
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
        )
        processor = BatchProcessor(config)
        docs = processor.discover_documents()
        assert docs == []

    def test_manifest_skip_unchanged(self, tmp_path):
        """Test that unchanged documents are skipped."""
        # Create a PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test content")

        # Create a manifest that already has this file
        manifest_path = tmp_path / ".corpora-manifest.json"

        # We need to compute the hash the same way the manifest does
        from corpora.output.vocab_writer import compute_file_hash
        file_hash = compute_file_hash(pdf_path)

        manifest_data = {
            "schema_version": "1.0",
            "last_updated": "2024-01-01T00:00:00",
            "documents": {
                str(pdf_path): {
                    "source_path": str(pdf_path),
                    "source_hash": file_hash,
                    "vocab_path": str(tmp_path / "test.vocab.json"),
                    "processed_at": "2024-01-01T00:00:00",
                    "term_count": 10,
                }
            }
        }
        manifest_path.write_text(json.dumps(manifest_data))

        config = BatchConfig(
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
            force_reprocess=False,
        )
        processor = BatchProcessor(config, manifest_path=manifest_path)

        results = list(processor.process())
        assert len(results) == 1
        assert results[0].status == DocumentStatus.SKIPPED

    def test_force_reprocess_ignores_manifest(self, tmp_path):
        """Test that --force reprocesses even with existing manifest entry."""
        # Create a PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test content")

        # Create manifest (same as above)
        manifest_path = tmp_path / ".corpora-manifest.json"
        from corpora.output.vocab_writer import compute_file_hash
        file_hash = compute_file_hash(pdf_path)

        manifest_data = {
            "schema_version": "1.0",
            "last_updated": "2024-01-01T00:00:00",
            "documents": {
                str(pdf_path): {
                    "source_path": str(pdf_path),
                    "source_hash": file_hash,
                    "vocab_path": str(tmp_path / "test.vocab.json"),
                    "processed_at": "2024-01-01T00:00:00",
                    "term_count": 10,
                }
            }
        }
        manifest_path.write_text(json.dumps(manifest_data))

        config = BatchConfig(
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
            force_reprocess=True,  # Force!
        )

        # Mock the processing to avoid real API calls
        with patch.object(BatchProcessor, '_process_single_document') as mock_process:
            mock_process.return_value = DocumentResult(
                source_path=pdf_path,
                status=DocumentStatus.SUCCESS,
                term_count=5,
                vocab_path=tmp_path / "output" / "test.vocab.json",
            )

            processor = BatchProcessor(config, manifest_path=manifest_path)
            results = list(processor.process())

            # Should process (not skip) because force=True
            assert len(results) == 1
            assert results[0].status == DocumentStatus.SUCCESS
            mock_process.assert_called()


# ============================================================================
# CLI Tests
# ============================================================================

class TestBatchCLI:
    """Tests for batch CLI command."""

    def test_help(self):
        """Test that help displays correctly."""
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "Process all documents in a folder" in result.output
        assert "--workers" in result.output
        assert "--quiet" in result.output
        assert "--force" in result.output

    def test_no_documents_found(self, tmp_path):
        """Test exit code when no documents found."""
        result = runner.invoke(app, ["batch", str(tmp_path)])
        assert result.exit_code == 66  # EXIT_NO_INPUT
        assert "No PDF or EPUB files found" in result.output

    def test_invalid_directory(self, tmp_path):
        """Test error on non-existent directory."""
        result = runner.invoke(app, ["batch", str(tmp_path / "nonexistent")])
        assert result.exit_code != 0

    @patch.object(BatchProcessor, 'process')
    @patch.object(BatchProcessor, 'discover_documents')
    def test_quiet_mode(self, mock_discover, mock_process, tmp_path):
        """Test quiet mode shows minimal output."""
        # Setup mocks
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        mock_discover.return_value = [pdf_path]
        mock_process.return_value = iter([
            DocumentResult(
                source_path=pdf_path,
                status=DocumentStatus.SUCCESS,
                term_count=10,
                duration_seconds=1.0,
            )
        ])

        result = runner.invoke(app, ["batch", str(tmp_path), "--quiet"])

        # Should show summary but not progress bar details
        assert "Batch Processing Complete" in result.output

    @patch.object(BatchProcessor, 'process')
    @patch.object(BatchProcessor, 'discover_documents')
    def test_partial_failure_exit_code(self, mock_discover, mock_process, tmp_path):
        """Test exit code 75 on partial failure."""
        pdf1 = tmp_path / "good.pdf"
        pdf2 = tmp_path / "bad.pdf"
        pdf1.touch()
        pdf2.touch()

        mock_discover.return_value = [pdf1, pdf2]
        mock_process.return_value = iter([
            DocumentResult(
                source_path=pdf1,
                status=DocumentStatus.SUCCESS,
                term_count=10,
            ),
            DocumentResult(
                source_path=pdf2,
                status=DocumentStatus.FAILED,
                error="Parse error",
            ),
        ])

        result = runner.invoke(app, ["batch", str(tmp_path), "--quiet"])
        assert result.exit_code == 75  # EXIT_PARTIAL


# ============================================================================
# Duration Format Tests
# ============================================================================

class TestDurationFormat:
    """Tests for duration formatting helper."""

    def test_format_seconds(self):
        from corpora.cli.batch import _format_duration
        assert _format_duration(30.5) == "30.5s"
        assert _format_duration(0.1) == "0.1s"

    def test_format_minutes(self):
        from corpora.cli.batch import _format_duration
        assert _format_duration(90) == "1m 30s"
        assert _format_duration(120) == "2m 0s"

    def test_format_hours(self):
        from corpora.cli.batch import _format_duration
        assert _format_duration(3600) == "1h 0m"
        assert _format_duration(5400) == "1h 30m"
