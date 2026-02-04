"""Tests for output module and CLI commands.

Covers models, writer, merger, consolidator, IP module, and CLI commands.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from corpora.cli.main import app
from corpora.ip import (
    FlaggedTerm,
    IPBlocklist,
    ReviewQueue,
    detect_ip,
    flag_terms,
    generate_review_queue,
)
from corpora.models import AxisScores, ClassifiedTerm
from corpora.output import (
    VOCAB_SCHEMA_VERSION,
    ConsolidationSummary,
    CorporaManifest,
    VocabularyEntry,
    VocabularyMetadata,
    VocabularyOutput,
    compute_file_hash,
    consolidate_vocabularies,
    merge_duplicates,
    write_vocab_file,
)

runner = CliRunner()


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestVocabularyOutputSerialization:
    """Tests for VocabularyOutput model serialization."""

    def test_vocabulary_output_serialization(self):
        """VocabularyOutput should serialize to JSON correctly."""
        metadata = VocabularyMetadata(
            source_path="test.pdf",
            source_hash="abc123",
            term_count=2,
            classified_count=2,
            flagged_count=0,
        )
        entries = [
            VocabularyEntry(
                id="test-fireball",
                text="fireball",
                source="test.pdf",
                intent="offensive",
                pos="noun",
                category="spell",
                canonical="fireball",
                mood="arcane",
                confidence=0.9,
            ),
        ]
        output = VocabularyOutput(metadata=metadata, entries=entries)

        # Serialize and deserialize
        json_str = output.model_dump_json()
        data = json.loads(json_str)

        assert data["metadata"]["schema_version"] == VOCAB_SCHEMA_VERSION
        assert data["metadata"]["source_path"] == "test.pdf"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["canonical"] == "fireball"

    def test_vocabulary_entry_with_ip_flag(self):
        """VocabularyEntry should include ip_flag when set."""
        entry = VocabularyEntry(
            id="test-beholder",
            text="Beholder",
            source="test.pdf",
            intent="creature",
            pos="noun",
            category="creature",
            canonical="beholder",
            mood="dark",
            confidence=0.9,
            ip_flag="blocklist:dnd",
        )

        data = entry.model_dump()
        assert data["ip_flag"] == "blocklist:dnd"

    def test_vocabulary_entry_without_ip_flag(self):
        """VocabularyEntry should have null ip_flag by default."""
        entry = VocabularyEntry(
            id="test-dragon",
            text="Dragon",
            source="test.pdf",
            intent="creature",
            pos="noun",
            category="creature",
            canonical="dragon",
            mood="epic",
            confidence=0.95,
        )

        data = entry.model_dump()
        assert data["ip_flag"] is None


class TestManifestModels:
    """Tests for CorporaManifest model."""

    def test_manifest_needs_processing_new_file(self, tmp_path):
        """Manifest should flag new files as needing processing."""
        manifest = CorporaManifest()
        test_file = tmp_path / "test.pdf"
        test_file.write_text("content")

        assert manifest.needs_processing(test_file) is True

    def test_manifest_needs_processing_unchanged(self, tmp_path):
        """Manifest should skip unchanged files."""
        manifest = CorporaManifest()
        test_file = tmp_path / "test.pdf"
        test_file.write_text("content")

        # Register the file
        manifest.update_entry(test_file, tmp_path / "test.vocab.json", term_count=10)

        # Same file should not need processing
        assert manifest.needs_processing(test_file) is False

    def test_manifest_needs_processing_changed(self, tmp_path):
        """Manifest should flag changed files as needing processing."""
        manifest = CorporaManifest()
        test_file = tmp_path / "test.pdf"
        test_file.write_text("original content")

        # Register the file
        manifest.update_entry(test_file, tmp_path / "test.vocab.json", term_count=10)

        # Change the file
        test_file.write_text("modified content")

        assert manifest.needs_processing(test_file) is True

    def test_manifest_orphan_detection(self, tmp_path):
        """Manifest should detect orphaned vocab files."""
        manifest = CorporaManifest()

        # Create and register two files
        file1 = tmp_path / "doc1.pdf"
        file2 = tmp_path / "doc2.pdf"
        file1.write_text("content1")
        file2.write_text("content2")

        manifest.update_entry(file1, tmp_path / "doc1.vocab.json", term_count=5)
        manifest.update_entry(file2, tmp_path / "doc2.vocab.json", term_count=10)

        # Now only file1 exists in current sources
        orphaned = manifest.get_orphaned_vocabs([file1])

        assert len(orphaned) == 1
        assert str(tmp_path / "doc2.vocab.json") in orphaned


# =============================================================================
# WRITER TESTS
# =============================================================================


class TestVocabWriter:
    """Tests for vocab_writer functions."""

    def test_compute_file_hash(self, tmp_path):
        """compute_file_hash should return MD5 hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        hash_value = compute_file_hash(test_file)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hex digest length

    def test_compute_file_hash_deterministic(self, tmp_path):
        """Same content should produce same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        content = "identical content"
        file1.write_text(content)
        file2.write_text(content)

        assert compute_file_hash(file1) == compute_file_hash(file2)

    def test_write_vocab_file_creates_json(self, tmp_path):
        """write_vocab_file should create a valid JSON file."""
        source_file = tmp_path / "source.json"
        source_file.write_text('{"test": "data"}')
        output_file = tmp_path / "output.vocab.json"

        terms = [
            ClassifiedTerm(
                id="test-spell",
                text="spell",
                source="source.json",
                intent="utility",
                pos="noun",
                axes=AxisScores(mind=0.8),
                category="concept",
                canonical="spell",
                mood="arcane",
                confidence=0.9,
            ),
        ]

        result = write_vocab_file(terms, source_file, output_file)

        assert output_file.exists()
        assert isinstance(result, VocabularyOutput)

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert "metadata" in data
        assert "entries" in data
        assert data["metadata"]["term_count"] == 1

    def test_write_vocab_file_with_ip_flag(self, tmp_path):
        """write_vocab_file should preserve IP flags."""
        source_file = tmp_path / "source.json"
        source_file.write_text('{"test": "data"}')
        output_file = tmp_path / "output.vocab.json"

        terms = [
            ClassifiedTerm(
                id="test-beholder",
                text="Beholder",
                source="source.json",
                intent="creature",
                pos="noun",
                axes=AxisScores(void=0.7),
                category="creature",
                canonical="beholder",
                mood="dark",
                confidence=0.85,
                ip_flag="blocklist:dnd",
            ),
        ]

        write_vocab_file(terms, source_file, output_file)

        with open(output_file) as f:
            data = json.load(f)

        assert data["entries"][0]["ip_flag"] == "blocklist:dnd"
        assert data["metadata"]["flagged_count"] == 1


# =============================================================================
# MERGER TESTS
# =============================================================================


class TestMergeDuplicates:
    """Tests for merge_duplicates function."""

    def test_merge_duplicates_single_entry(self):
        """Single entry should be returned as-is."""
        entry = VocabularyEntry(
            id="test-1",
            text="fireball",
            source="doc1.pdf",
            intent="offensive",
            pos="noun",
            category="spell",
            canonical="fireball",
            mood="arcane",
            confidence=0.9,
        )

        result = merge_duplicates([entry])

        assert result.text == "fireball"
        assert result.source == "doc1.pdf"
        assert result.confidence == 0.9

    def test_merge_duplicates_confidence_weighted(self):
        """Merged entry should use highest confidence as base."""
        entries = [
            VocabularyEntry(
                id="test-1",
                text="fireball",
                source="doc1.pdf",
                intent="offensive",
                pos="noun",
                category="spell",
                canonical="fireball",
                mood="arcane",
                confidence=0.7,
            ),
            VocabularyEntry(
                id="test-2",
                text="Fireball",
                source="doc2.pdf",
                intent="offensive",
                pos="noun",
                category="spell",
                canonical="fireball",
                mood="epic",
                confidence=0.95,
            ),
        ]

        result = merge_duplicates(entries)

        # Should use high-confidence entry's mood
        assert result.mood == "epic"
        # Sources should be joined
        assert "doc1.pdf" in result.source and "doc2.pdf" in result.source
        # Confidence should be averaged
        assert 0.8 <= result.confidence <= 0.85

    def test_merge_duplicates_preserves_ip_flag(self):
        """Merged entry should preserve IP flag if any entry has one."""
        entries = [
            VocabularyEntry(
                id="test-1",
                text="beholder",
                source="doc1.pdf",
                intent="creature",
                pos="noun",
                category="creature",
                canonical="beholder",
                mood="dark",
                confidence=0.8,
            ),
            VocabularyEntry(
                id="test-2",
                text="Beholder",
                source="doc2.pdf",
                intent="creature",
                pos="noun",
                category="creature",
                canonical="beholder",
                mood="dark",
                confidence=0.9,
                ip_flag="blocklist:dnd",
            ),
        ]

        result = merge_duplicates(entries)

        assert result.ip_flag == "blocklist:dnd"

    def test_merge_duplicates_unions_tags(self):
        """Merged entry should union all tags."""
        entries = [
            VocabularyEntry(
                id="test-1",
                text="spell",
                source="doc1.pdf",
                intent="utility",
                pos="noun",
                category="concept",
                canonical="spell",
                mood="arcane",
                confidence=0.9,
                tags=["magic", "arcane"],
            ),
            VocabularyEntry(
                id="test-2",
                text="spell",
                source="doc2.pdf",
                intent="utility",
                pos="noun",
                category="concept",
                canonical="spell",
                mood="arcane",
                confidence=0.85,
                tags=["arcane", "fantasy"],
            ),
        ]

        result = merge_duplicates(entries)

        assert "magic" in result.tags
        assert "arcane" in result.tags
        assert "fantasy" in result.tags


# =============================================================================
# CONSOLIDATOR TESTS
# =============================================================================


class TestConsolidateVocabularies:
    """Tests for consolidate_vocabularies function."""

    def test_consolidate_vocabularies_merges(self, tmp_path):
        """consolidate_vocabularies should merge multiple vocab files."""
        # Create two vocab files
        vocab1 = {
            "metadata": {
                "schema_version": "1.0",
                "source_path": "doc1.pdf",
                "source_hash": "abc",
                "extracted_at": "2026-02-04T00:00:00",
                "term_count": 1,
                "classified_count": 1,
                "flagged_count": 0,
            },
            "entries": [
                {
                    "id": "test-1",
                    "text": "fireball",
                    "source": "doc1.pdf",
                    "genre": "fantasy",
                    "intent": "offensive",
                    "pos": "noun",
                    "axes": {"fire": 0.9},
                    "tags": [],
                    "category": "spell",
                    "canonical": "fireball",
                    "mood": "arcane",
                    "energy": "",
                    "confidence": 0.9,
                    "secondary_intents": [],
                    "ip_flag": None,
                }
            ],
        }

        vocab2 = {
            "metadata": {
                "schema_version": "1.0",
                "source_path": "doc2.pdf",
                "source_hash": "def",
                "extracted_at": "2026-02-04T00:00:00",
                "term_count": 1,
                "classified_count": 1,
                "flagged_count": 0,
            },
            "entries": [
                {
                    "id": "test-2",
                    "text": "dragon",
                    "source": "doc2.pdf",
                    "genre": "fantasy",
                    "intent": "creature",
                    "pos": "noun",
                    "axes": {"fire": 0.8},
                    "tags": [],
                    "category": "creature",
                    "canonical": "dragon",
                    "mood": "epic",
                    "energy": "",
                    "confidence": 0.95,
                    "secondary_intents": [],
                    "ip_flag": None,
                }
            ],
        }

        vocab1_path = tmp_path / "doc1.vocab.json"
        vocab2_path = tmp_path / "doc2.vocab.json"
        master_path = tmp_path / "master.vocab.json"

        vocab1_path.write_text(json.dumps(vocab1))
        vocab2_path.write_text(json.dumps(vocab2))

        summary = consolidate_vocabularies([vocab1_path, vocab2_path], master_path)

        assert master_path.exists()
        assert len(summary.added) == 2

        with open(master_path) as f:
            master = json.load(f)

        assert master["metadata"]["term_count"] == 2

    def test_consolidate_vocabularies_creates_backup(self, tmp_path):
        """consolidate_vocabularies should create backup of existing master."""
        # Create initial master
        master_path = tmp_path / "master.vocab.json"
        master_path.write_text('{"metadata": {}, "entries": []}')

        # Create vocab file
        vocab = {
            "metadata": {
                "schema_version": "1.0",
                "source_path": "doc.pdf",
                "source_hash": "abc",
                "extracted_at": "2026-02-04T00:00:00",
                "term_count": 1,
                "classified_count": 1,
                "flagged_count": 0,
            },
            "entries": [
                {
                    "id": "test-1",
                    "text": "spell",
                    "source": "doc.pdf",
                    "genre": "fantasy",
                    "intent": "utility",
                    "pos": "noun",
                    "axes": {},
                    "tags": [],
                    "category": "concept",
                    "canonical": "spell",
                    "mood": "arcane",
                    "energy": "",
                    "confidence": 0.9,
                    "secondary_intents": [],
                    "ip_flag": None,
                }
            ],
        }

        vocab_path = tmp_path / "doc.vocab.json"
        vocab_path.write_text(json.dumps(vocab))

        consolidate_vocabularies([vocab_path], master_path)

        # Check backup was created
        backup_files = list(tmp_path.glob("*.bak"))
        assert len(backup_files) >= 1

    def test_consolidation_summary_string(self):
        """ConsolidationSummary should format nicely."""
        summary = ConsolidationSummary(
            added={"fireball", "dragon"},
            updated={"spell"},
            removed=set(),
            flagged={"beholder"},
        )

        s = str(summary)
        assert "+2 new" in s
        assert "~1 updated" in s
        assert "!1 flagged" in s


# =============================================================================
# IP TESTS
# =============================================================================


class TestIPBlocklist:
    """Tests for IPBlocklist functionality."""

    def test_blocklist_case_insensitive(self, tmp_path):
        """Blocklist matching should be case-insensitive."""
        blocklist_data = {"dnd": ["Beholder", "Mind Flayer"]}
        blocklist_file = tmp_path / "blocklist.json"
        blocklist_file.write_text(json.dumps(blocklist_data))

        blocklist = IPBlocklist(blocklist_file)

        # Should match regardless of case
        assert blocklist.check("beholder", "beholder") == "dnd"
        assert blocklist.check("BEHOLDER", "beholder") == "dnd"
        assert blocklist.check("Beholder", "beholder") == "dnd"

    def test_blocklist_multi_word(self, tmp_path):
        """Blocklist should match multi-word terms."""
        blocklist_data = {"dnd": ["Mind Flayer", "Gelatinous Cube"]}
        blocklist_file = tmp_path / "blocklist.json"
        blocklist_file.write_text(json.dumps(blocklist_data))

        blocklist = IPBlocklist(blocklist_file)

        assert blocklist.check("Mind Flayer", "mind flayer") == "dnd"
        assert blocklist.check("gelatinous cube", "gelatinous cube") == "dnd"

    def test_blocklist_no_match(self, tmp_path):
        """Blocklist should return None for non-matching terms."""
        blocklist_data = {"dnd": ["Beholder"]}
        blocklist_file = tmp_path / "blocklist.json"
        blocklist_file.write_text(json.dumps(blocklist_data))

        blocklist = IPBlocklist(blocklist_file)

        assert blocklist.check("dragon", "dragon") is None


class TestGenerateReviewQueue:
    """Tests for generate_review_queue function."""

    def test_generate_review_queue(self, tmp_path):
        """generate_review_queue should create flagged.json with flagged terms."""
        vocab = VocabularyOutput(
            metadata=VocabularyMetadata(
                source_path="test.pdf",
                source_hash="abc",
                term_count=3,
                classified_count=3,
                flagged_count=1,
            ),
            entries=[
                VocabularyEntry(
                    id="1",
                    text="Beholder",
                    source="test",
                    intent="creature",
                    pos="noun",
                    category="creature",
                    canonical="beholder",
                    mood="dark",
                    confidence=0.9,
                    ip_flag="blocklist:dnd",
                ),
                VocabularyEntry(
                    id="2",
                    text="Dragon",
                    source="test",
                    intent="creature",
                    pos="noun",
                    category="creature",
                    canonical="dragon",
                    mood="epic",
                    confidence=0.95,
                ),
                VocabularyEntry(
                    id="3",
                    text="Mindflayer",
                    source="test",
                    intent="creature",
                    pos="noun",
                    category="creature",
                    canonical="mindflayer",
                    mood="dark",
                    confidence=0.85,
                    ip_flag="blocklist:dnd",
                ),
            ],
        )

        output_path = tmp_path / "flagged.json"
        queue = generate_review_queue(vocab, output_path)

        assert queue.total_flagged == 2
        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert len(data["terms"]) == 2
        assert data["terms"][0]["canonical"] == "beholder"  # sorted alphabetically

    def test_generate_review_queue_empty(self, tmp_path):
        """generate_review_queue should handle no flagged terms."""
        vocab = VocabularyOutput(
            metadata=VocabularyMetadata(
                source_path="test.pdf",
                source_hash="abc",
                term_count=1,
                classified_count=1,
                flagged_count=0,
            ),
            entries=[
                VocabularyEntry(
                    id="1",
                    text="Dragon",
                    source="test",
                    intent="creature",
                    pos="noun",
                    category="creature",
                    canonical="dragon",
                    mood="epic",
                    confidence=0.95,
                ),
            ],
        )

        output_path = tmp_path / "flagged.json"
        queue = generate_review_queue(vocab, output_path)

        assert queue.total_flagged == 0
        assert len(queue.terms) == 0


class TestFlagTerms:
    """Tests for flag_terms function."""

    def test_flag_terms_applies_blocklist(self, tmp_path):
        """flag_terms should apply blocklist to terms."""
        blocklist_data = {"dnd": ["Beholder"]}
        blocklist_file = tmp_path / "blocklist.json"
        blocklist_file.write_text(json.dumps(blocklist_data))

        blocklist = IPBlocklist(blocklist_file)

        terms = [
            ClassifiedTerm(
                id="1",
                text="Beholder",
                source="test",
                intent="creature",
                pos="noun",
                axes=AxisScores(),
                category="creature",
                canonical="beholder",
                mood="dark",
                confidence=0.9,
            ),
            ClassifiedTerm(
                id="2",
                text="Dragon",
                source="test",
                intent="creature",
                pos="noun",
                axes=AxisScores(),
                category="creature",
                canonical="dragon",
                mood="epic",
                confidence=0.95,
            ),
        ]

        flagged = flag_terms(terms, blocklist)

        assert flagged[0].ip_flag == "blocklist:dnd"
        assert flagged[1].ip_flag is None


# =============================================================================
# CLI TESTS
# =============================================================================


class TestOutputCommandHelp:
    """Tests for output command help."""

    def test_output_command_help(self):
        """output command should show help."""
        result = runner.invoke(app, ["output", "--help"])
        assert result.exit_code == 0
        assert "Generate vocabulary JSON" in result.output
        assert "--blocklist" in result.output
        assert "--verbose" in result.output

    def test_output_command_missing_file(self):
        """output should error on missing file."""
        result = runner.invoke(app, ["output", "nonexistent.json"])
        assert result.exit_code != 0


class TestConsolidateCommandHelp:
    """Tests for consolidate command help."""

    def test_consolidate_command_help(self):
        """consolidate command should show help."""
        result = runner.invoke(app, ["consolidate", "--help"])
        assert result.exit_code == 0
        assert "Consolidate vocabulary files" in result.output
        assert "--master" in result.output
        assert "--force" in result.output
        assert "--remove-orphans" in result.output


class TestOutputCommandFunctional:
    """Functional tests for output command."""

    def test_output_command_generates_vocab(self, tmp_path):
        """output command should generate .vocab.json from extract output."""
        # Create extract output (array of ClassifiedTerm)
        extract_output = [
            {
                "id": "test-fireball",
                "text": "fireball",
                "source": "test.pdf",
                "genre": "fantasy",
                "intent": "offensive",
                "pos": "noun",
                "axes": {"fire": 0.9},
                "tags": [],
                "category": "spell",
                "canonical": "fireball",
                "mood": "arcane",
                "energy": "",
                "confidence": 0.9,
                "secondary_intents": [],
                "ip_flag": None,
            },
        ]

        input_file = tmp_path / "extract.json"
        input_file.write_text(json.dumps(extract_output))

        result = runner.invoke(app, ["output", str(input_file)])

        assert result.exit_code == 0
        assert "Generated:" in result.output

        # Verify output file was created
        vocab_file = tmp_path / "extract.vocab.json"
        assert vocab_file.exists()

        with open(vocab_file) as f:
            data = json.load(f)

        assert "metadata" in data
        assert len(data["entries"]) == 1


class TestConsolidateCommandFunctional:
    """Functional tests for consolidate command."""

    def test_consolidate_command_shows_summary(self, tmp_path):
        """consolidate command should show change summary."""
        # Create vocab files
        vocab = {
            "metadata": {
                "schema_version": "1.0",
                "source_path": "doc.pdf",
                "source_hash": "abc",
                "extracted_at": "2026-02-04T00:00:00",
                "term_count": 1,
                "classified_count": 1,
                "flagged_count": 0,
            },
            "entries": [
                {
                    "id": "test-1",
                    "text": "spell",
                    "source": "doc.pdf",
                    "genre": "fantasy",
                    "intent": "utility",
                    "pos": "noun",
                    "axes": {},
                    "tags": [],
                    "category": "concept",
                    "canonical": "spell",
                    "mood": "arcane",
                    "energy": "",
                    "confidence": 0.9,
                    "secondary_intents": [],
                    "ip_flag": None,
                }
            ],
        }

        vocab_file = tmp_path / "doc.vocab.json"
        vocab_file.write_text(json.dumps(vocab))

        result = runner.invoke(app, ["consolidate", str(tmp_path), "--force"])

        assert result.exit_code == 0
        assert "Consolidated:" in result.output
        # Should show change summary
        assert "new" in result.output or "Change summary" in result.output


class TestReviewQueueModels:
    """Tests for review queue models."""

    def test_flagged_term_model(self):
        """FlaggedTerm should have correct fields."""
        term = FlaggedTerm(
            canonical="beholder",
            text="Beholder",
            source="test.pdf",
            flag_reason="blocklist:dnd",
            confidence=0.9,
            category="creature",
        )

        assert term.reviewed is False
        assert term.decision == ""
        assert term.notes == ""

    def test_review_queue_to_file(self, tmp_path):
        """ReviewQueue should write to JSON file."""
        queue = ReviewQueue(
            total_flagged=1,
            terms=[
                FlaggedTerm(
                    canonical="beholder",
                    text="Beholder",
                    source="test.pdf",
                    flag_reason="blocklist:dnd",
                    confidence=0.9,
                    category="creature",
                )
            ],
        )

        output_path = tmp_path / "review.json"
        queue.to_file(output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["total_flagged"] == 1
        assert len(data["terms"]) == 1
