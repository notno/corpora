"""Tests for extract CLI command.

Uses mocked API calls for CI testing without actual API access.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from corpora.cli.main import app
from corpora.models import AxisScores, ClassifiedTerm

runner = CliRunner()


class TestExtractHelp:
    """Tests for extract command help and basic behavior."""

    def test_extract_help(self):
        """Extract command should show help."""
        result = runner.invoke(app, ["extract", "--help"])
        assert result.exit_code == 0
        assert "Extract and classify vocabulary" in result.output
        assert "--preview" in result.output
        assert "--verbose" in result.output
        assert "--sync" in result.output
        assert "--output" in result.output
        assert "--batch-size" in result.output

    def test_extract_missing_file(self):
        """Extract should error on missing file."""
        result = runner.invoke(app, ["extract", "nonexistent.json"])
        assert result.exit_code != 0
        # Typer shows "Invalid value" for missing file with exists=True
        assert "Invalid value" in result.output or "nonexistent" in result.output


class TestExtractPreviewMode:
    """Tests for preview mode functionality."""

    def test_extract_preview_mode(self):
        """Preview mode should show term count and cost estimate."""
        # Create a minimal Phase 1 JSON document
        doc_content = {
            "source": "test.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {},
            "content": [
                {
                    "type": "text",
                    "text": "The wizard cast a powerful fireball at the dragon.",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--preview"])

            assert result.exit_code == 0
            assert "Terms extracted:" in result.output
            assert "Sample terms:" in result.output
            assert "Estimated cost:" in result.output
        finally:
            Path(temp_path).unlink()


class TestExtractSyncMode:
    """Tests for synchronous classification mode."""

    @patch("corpora.cli.extract.ClassificationClient")
    def test_extract_sync_mode(self, mock_client_class):
        """Sync mode should classify terms via API."""
        # Mock the classification response
        mock_client = Mock()
        mock_client.classify_term.return_value = ClassifiedTerm(
            id="test-wizard",
            text="wizard",
            source="test.pdf",
            intent="utility",
            pos="noun",
            axes=AxisScores(mind=0.8),
            category="character",
            canonical="wizard",
            mood="arcane",
            confidence=0.9,
        )
        mock_client_class.return_value = mock_client

        # Create test document
        doc_content = {
            "source": "test.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {},
            "content": [
                {
                    "type": "text",
                    "text": "The wizard cast a spell.",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--sync"])

            assert result.exit_code == 0
            # Output should be JSON with classified terms
            assert "wizard" in result.output
            assert "character" in result.output or "id" in result.output
        finally:
            Path(temp_path).unlink()

    @patch("corpora.cli.extract.ClassificationClient")
    def test_extract_sync_verbose(self, mock_client_class):
        """Verbose mode should show term-by-term progress."""
        mock_client = Mock()
        mock_client.classify_term.return_value = ClassifiedTerm(
            id="test-spell",
            text="spell",
            source="test.pdf",
            intent="utility",
            pos="noun",
            axes=AxisScores(mind=0.7),
            category="concept",
            canonical="spell",
            mood="arcane",
            confidence=0.85,
        )
        mock_client_class.return_value = mock_client

        doc_content = {
            "source": "test.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {},
            "content": [
                {"type": "text", "text": "A magical spell was cast."}
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--sync", "-v"])

            assert result.exit_code == 0
            # Verbose shows category for each term
            assert "concept" in result.output or "Classifying" in result.output
        finally:
            Path(temp_path).unlink()


class TestExtractNoCandidates:
    """Tests for edge cases with no candidates."""

    def test_extract_no_candidates(self):
        """Should handle documents with no extractable terms."""
        # Document with only stopwords/common words
        doc_content = {
            "source": "test.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {},
            "content": [
                {"type": "text", "text": "The a an is was were be been."}
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--sync"])

            assert result.exit_code == 0
            # Should output empty array or warning
            assert "[]" in result.output or "No vocabulary candidates" in result.output
        finally:
            Path(temp_path).unlink()

    def test_extract_empty_content(self):
        """Should handle documents with empty content."""
        doc_content = {
            "source": "empty.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {},
            "content": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--sync"])

            # Should exit with data error
            assert result.exit_code != 0
            assert "No text content" in result.output or "Warning" in result.output
        finally:
            Path(temp_path).unlink()


class TestExtractIntegration:
    """Integration tests with real extraction, mocked classification."""

    @patch("corpora.cli.extract.ClassificationClient")
    def test_real_extraction_mock_classification(self, mock_client_class):
        """Integration test: real spaCy extraction, mocked Claude."""
        # Track calls to classify_term
        classified_terms = []

        def mock_classify(term, source, lemma="", pos=""):
            result = ClassifiedTerm(
                id=f"test-{term.lower()}",
                text=term,
                source=source,
                intent="utility",
                pos=pos if pos else "noun",
                axes=AxisScores(mind=0.5),
                category="concept",
                canonical=term.lower(),
                mood="neutral",
                confidence=0.8,
            )
            classified_terms.append(result)
            return result

        mock_client = Mock()
        mock_client.classify_term.side_effect = mock_classify
        mock_client_class.return_value = mock_client

        # Fantasy-rich content for extraction
        doc_content = {
            "source": "fantasy.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {"title": "Magic Manual"},
            "content": [
                {
                    "type": "text",
                    "text": "The ancient wizard summoned a powerful dragon using arcane magic. "
                           "The fireball spell illuminated the dark dungeon.",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--sync"])

            assert result.exit_code == 0

            # Should have extracted and classified terms
            assert len(classified_terms) > 0

            # Parse output JSON - need to find the JSON array in the output
            # which may include progress bar output before it
            output = result.output
            json_start = output.find("[")
            json_end = output.rfind("]") + 1
            assert json_start >= 0 and json_end > json_start, f"No JSON array in output: {output}"
            output_json = json.loads(output[json_start:json_end])
            assert isinstance(output_json, list)
            assert len(output_json) > 0

            # Verify structure of classified terms
            for term in output_json:
                assert "id" in term
                assert "text" in term
                assert "source" in term
                assert "axes" in term
                assert "category" in term

        finally:
            Path(temp_path).unlink()

    @patch("corpora.cli.extract.ClassificationClient")
    def test_output_to_file(self, mock_client_class):
        """Should write results to output file."""
        mock_client = Mock()
        mock_client.classify_term.return_value = ClassifiedTerm(
            id="test-phoenix",
            text="phoenix",
            source="test.pdf",
            intent="utility",
            pos="noun",
            axes=AxisScores(fire=0.9, life=0.8),
            category="creature",
            canonical="phoenix",
            mood="mythic",
            confidence=0.95,
        )
        mock_client_class.return_value = mock_client

        doc_content = {
            "source": "test.pdf",
            "format": "pdf",
            "extracted_at": "2026-02-04T00:00:00",
            "ocr_used": False,
            "metadata": {},
            "content": [
                {"type": "text", "text": "The phoenix rose from the ashes."}
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(doc_content, f)
            input_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = runner.invoke(
                app, ["extract", input_path, "--sync", "-o", output_path]
            )

            assert result.exit_code == 0

            # Verify output file was written
            with open(output_path) as f:
                output_data = json.load(f)

            assert isinstance(output_data, list)
            assert len(output_data) > 0
            assert output_data[0]["text"] == "phoenix"

        finally:
            Path(input_path).unlink()
            Path(output_path).unlink(missing_ok=True)


class TestExtractInvalidInput:
    """Tests for invalid input handling."""

    def test_invalid_json_file(self):
        """Should handle invalid JSON gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {}")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--preview"])

            # Should error with meaningful message
            assert result.exit_code != 0
        finally:
            Path(temp_path).unlink()

    def test_wrong_schema_file(self):
        """Should handle JSON with wrong schema."""
        # Valid JSON but not DocumentOutput schema
        wrong_schema = {"random": "data", "not": "a document"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(wrong_schema, f)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", temp_path, "--preview"])

            # Should error with validation message
            assert result.exit_code != 0
            assert "Invalid" in result.output or "Error" in result.output
        finally:
            Path(temp_path).unlink()
