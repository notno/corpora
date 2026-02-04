"""Tests for classification module.

Uses mocked API calls for CI testing without actual API access.
"""

import json
from unittest.mock import Mock, patch

import pytest

from corpora.classification import ClassificationClient, BatchClassifier
from corpora.classification.prompts import CLASSIFICATION_SYSTEM_PROMPT
from corpora.models import ClassifiedTerm, AxisScores


class TestPrompts:
    """Tests for classification prompts."""

    def test_system_prompt_length_for_caching(self):
        """System prompt must be >1024 tokens for caching."""
        # Approximate: ~4 chars per token on average
        est_tokens = len(CLASSIFICATION_SYSTEM_PROMPT) / 4
        assert est_tokens > 1024, f"System prompt too short for caching: ~{int(est_tokens)} tokens"

    def test_system_prompt_minimum_chars(self):
        """System prompt should have substantial content."""
        # 4000 chars minimum for good caching eligibility
        assert len(CLASSIFICATION_SYSTEM_PROMPT) > 4000, (
            f"System prompt too short: {len(CLASSIFICATION_SYSTEM_PROMPT)} chars"
        )

    def test_system_prompt_contains_all_elemental_axes(self):
        """System prompt should define all 8 elemental axes."""
        elemental_axes = ["fire", "water", "earth", "air", "light", "shadow", "life", "void"]
        for axis in elemental_axes:
            assert axis in CLASSIFICATION_SYSTEM_PROMPT.lower(), f"Missing elemental axis: {axis}"

    def test_system_prompt_contains_all_mechanical_axes(self):
        """System prompt should define all 8 mechanical axes."""
        mechanical_axes = ["force", "binding", "ward", "sight", "mind", "time", "space", "fate"]
        for axis in mechanical_axes:
            assert axis in CLASSIFICATION_SYSTEM_PROMPT.lower(), f"Missing mechanical axis: {axis}"

    def test_system_prompt_contains_output_format(self):
        """System prompt should specify JSON output format."""
        assert "json" in CLASSIFICATION_SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_categories(self):
        """System prompt should define term categories."""
        categories = ["spell", "creature", "item", "location"]
        for cat in categories:
            assert cat in CLASSIFICATION_SYSTEM_PROMPT.lower(), f"Missing category: {cat}"


class TestClassificationClient:
    """Tests for ClassificationClient."""

    @patch("corpora.classification.client.anthropic.Anthropic")
    def test_classify_term_parses_response(self, mock_anthropic):
        """Client should parse valid JSON response into ClassifiedTerm."""
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({
            "id": "test-fireball",
            "text": "Fireball",
            "genre": "fantasy",
            "intent": "offensive",
            "pos": "noun",
            "axes": {"fire": 0.9, "force": 0.7},
            "tags": ["evocation"],
            "category": "spell",
            "canonical": "fireball",
            "mood": "arcane",
            "energy": "fire",
            "confidence": 0.95,
        }))]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        client = ClassificationClient()
        result = client.classify_term("fireball", source="test")

        assert isinstance(result, ClassifiedTerm)
        assert result.text == "Fireball"
        assert result.axes.fire == 0.9
        assert result.axes.force == 0.7
        assert result.source == "test"
        assert result.intent == "offensive"
        assert result.category == "spell"

    @patch("corpora.classification.client.anthropic.Anthropic")
    def test_classify_term_uses_cache_control(self, mock_anthropic):
        """Client should enable prompt caching on system message."""
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({
            "id": "test-dragon",
            "text": "Dragon",
            "genre": "fantasy",
            "intent": "offensive",
            "pos": "noun",
            "axes": {"fire": 0.8, "life": 0.5},
            "tags": ["creature"],
            "category": "creature",
            "canonical": "dragon",
            "mood": "primal",
            "energy": "fire",
            "confidence": 0.9,
        }))]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        client = ClassificationClient()
        client.classify_term("dragon", source="test")

        # Verify cache_control was set on system message
        call_args = mock_client.messages.create.call_args
        system = call_args.kwargs["system"]
        assert len(system) == 1
        assert system[0]["cache_control"] == {"type": "ephemeral"}

    @patch("corpora.classification.client.anthropic.Anthropic")
    def test_classify_term_raises_on_invalid_json(self, mock_anthropic):
        """Client should raise ValueError on invalid JSON response."""
        mock_response = Mock()
        mock_response.content = [Mock(text="not valid json")]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        client = ClassificationClient()
        with pytest.raises(ValueError, match="Failed to parse classification"):
            client.classify_term("test", source="test")

    def test_estimate_cost_returns_dict(self):
        """Cost estimation should return expected fields."""
        client = ClassificationClient.__new__(ClassificationClient)
        estimate = client.estimate_cost(100, use_batch=True)

        assert "est_cost_usd" in estimate
        assert "num_terms" in estimate
        assert "est_input_tokens" in estimate
        assert "est_output_tokens" in estimate
        assert estimate["num_terms"] == 100
        assert estimate["use_batch"] is True
        assert estimate["est_cost_usd"] > 0

    def test_estimate_cost_batch_is_cheaper(self):
        """Batch API should estimate lower cost than sync API."""
        client = ClassificationClient.__new__(ClassificationClient)
        batch_estimate = client.estimate_cost(100, use_batch=True)
        sync_estimate = client.estimate_cost(100, use_batch=False)

        assert batch_estimate["est_cost_usd"] < sync_estimate["est_cost_usd"]

    def test_model_is_haiku(self):
        """Client should use Haiku 4.5 for cost efficiency."""
        assert "haiku" in ClassificationClient.MODEL.lower()


class TestBatchClassifier:
    """Tests for BatchClassifier."""

    @patch("corpora.classification.batch.anthropic.Anthropic")
    def test_create_batch_returns_id(self, mock_anthropic):
        """Batch creation should return batch ID."""
        mock_batch = Mock()
        mock_batch.id = "batch_abc123"

        mock_client = Mock()
        mock_client.messages.batches.create.return_value = mock_batch
        mock_anthropic.return_value = mock_client

        classifier = BatchClassifier()
        batch_id = classifier.create_batch([
            ("fireball", "test", "fireball", "noun"),
            ("dragon", "test", "dragon", "noun"),
        ])

        assert batch_id == "batch_abc123"
        mock_client.messages.batches.create.assert_called_once()

    @patch("corpora.classification.batch.anthropic.Anthropic")
    def test_create_batch_uses_correct_model(self, mock_anthropic):
        """Batch requests should use correct model."""
        mock_batch = Mock()
        mock_batch.id = "batch_xyz"

        mock_client = Mock()
        mock_client.messages.batches.create.return_value = mock_batch
        mock_anthropic.return_value = mock_client

        classifier = BatchClassifier()
        classifier.create_batch([("test", "src", "test", "noun")])

        call_args = mock_client.messages.batches.create.call_args
        requests = call_args.kwargs["requests"]
        assert len(requests) == 1
        assert requests[0]["params"]["model"] == "claude-haiku-4-5-20250929"

    @patch("corpora.classification.batch.anthropic.Anthropic")
    def test_create_batch_uses_cache_control(self, mock_anthropic):
        """Batch requests should enable prompt caching."""
        mock_batch = Mock()
        mock_batch.id = "batch_cache"

        mock_client = Mock()
        mock_client.messages.batches.create.return_value = mock_batch
        mock_anthropic.return_value = mock_client

        classifier = BatchClassifier()
        classifier.create_batch([("spell", "src", "spell", "noun")])

        call_args = mock_client.messages.batches.create.call_args
        requests = call_args.kwargs["requests"]
        system = requests[0]["params"]["system"]
        assert system[0]["cache_control"] == {"type": "ephemeral"}

    @patch("corpora.classification.batch.anthropic.Anthropic")
    def test_get_batch_status_returns_counts(self, mock_anthropic):
        """Batch status should include request counts."""
        mock_batch = Mock()
        mock_batch.id = "batch_status"
        mock_batch.processing_status = "in_progress"
        mock_batch.request_counts = Mock(
            processing=10,
            succeeded=5,
            errored=0,
            expired=0,
            canceled=0,
        )

        mock_client = Mock()
        mock_client.messages.batches.retrieve.return_value = mock_batch
        mock_anthropic.return_value = mock_client

        classifier = BatchClassifier()
        status = classifier.get_batch_status("batch_status")

        assert status["id"] == "batch_status"
        assert status["status"] == "in_progress"
        assert status["counts"]["processing"] == 10
        assert status["counts"]["succeeded"] == 5

    @patch("corpora.classification.batch.anthropic.Anthropic")
    def test_stream_results_yields_classified_terms(self, mock_anthropic):
        """Streaming results should yield ClassifiedTerm objects."""
        # Mock a successful result
        mock_result = Mock()
        mock_result.custom_id = "term-0-test"
        mock_result.result.type = "succeeded"
        mock_result.result.message.content = [Mock(text=json.dumps({
            "id": "test-flame",
            "text": "Flame",
            "genre": "fantasy",
            "intent": "offensive",
            "pos": "noun",
            "axes": {"fire": 0.95},
            "tags": [],
            "category": "concept",
            "canonical": "flame",
            "mood": "primal",
            "energy": "fire",
            "confidence": 0.9,
        }))]

        mock_client = Mock()
        mock_client.messages.batches.results.return_value = [mock_result]
        mock_anthropic.return_value = mock_client

        classifier = BatchClassifier()
        results = list(classifier.stream_results("batch_123", source="test"))

        assert len(results) == 1
        idx, term = results[0]
        assert idx == 0
        assert isinstance(term, ClassifiedTerm)
        assert term.text == "Flame"
        assert term.source == "test"

    @patch("corpora.classification.batch.anthropic.Anthropic")
    def test_stream_results_handles_errors(self, mock_anthropic):
        """Streaming results should yield error dicts for failures."""
        mock_result = Mock()
        mock_result.custom_id = "term-1-test"
        mock_result.result.type = "errored"
        mock_result.result.error = "API overloaded"

        mock_client = Mock()
        mock_client.messages.batches.results.return_value = [mock_result]
        mock_anthropic.return_value = mock_client

        classifier = BatchClassifier()
        results = list(classifier.stream_results("batch_err", source="test"))

        assert len(results) == 1
        idx, result = results[0]
        assert idx == 1
        assert isinstance(result, dict)
        assert "error" in result

    def test_model_is_haiku(self):
        """Batch classifier should use Haiku 4.5."""
        assert "haiku" in BatchClassifier.MODEL.lower()


class TestAxisScores:
    """Tests for AxisScores model."""

    def test_default_values_are_zero(self):
        """All axes should default to 0.0."""
        axes = AxisScores()
        assert axes.fire == 0.0
        assert axes.water == 0.0
        assert axes.void == 0.0
        assert axes.fate == 0.0

    def test_can_set_values(self):
        """Axes can be set to valid values."""
        axes = AxisScores(fire=0.9, force=0.7)
        assert axes.fire == 0.9
        assert axes.force == 0.7
        assert axes.water == 0.0

    def test_validates_range(self):
        """Axes should reject values outside 0.0-1.0."""
        with pytest.raises(ValueError):
            AxisScores(fire=1.5)

        with pytest.raises(ValueError):
            AxisScores(shadow=-0.1)


class TestClassifiedTerm:
    """Tests for ClassifiedTerm model."""

    def test_full_term_creation(self):
        """ClassifiedTerm can be created with all fields."""
        term = ClassifiedTerm(
            id="test-fireball",
            text="Fireball",
            source="test",
            genre="fantasy",
            intent="offensive",
            pos="noun",
            axes=AxisScores(fire=0.9, force=0.6),
            tags=["evocation", "classic"],
            category="spell",
            canonical="fireball",
            mood="arcane",
            energy="fire",
            confidence=0.95,
            secondary_intents=["utility"],
        )
        assert term.id == "test-fireball"
        assert term.axes.fire == 0.9

    def test_minimal_term_creation(self):
        """ClassifiedTerm can be created with required fields only."""
        term = ClassifiedTerm(
            id="test-ward",
            text="Ward",
            source="test",
            intent="defensive",
            pos="noun",
            category="spell",
            canonical="ward",
            mood="arcane",
            confidence=0.8,
        )
        assert term.genre == "fantasy"  # Default
        assert term.axes.fire == 0.0  # Default
        assert term.tags == []  # Default
