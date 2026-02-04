"""Tests for the vocabulary extraction module."""

import pytest

from corpora.extraction import TermExtractor
from corpora.models import CandidateTerm


@pytest.fixture
def extractor():
    """Create a TermExtractor instance for testing."""
    return TermExtractor()


class TestTermExtraction:
    """Tests for term extraction functionality."""

    def test_extracts_nouns(self, extractor):
        """Nouns should be extracted from text."""
        text = "The wizard cast a powerful fireball spell."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        assert "wizard" in lemmas
        assert "fireball" in lemmas
        assert "spell" in lemmas

    def test_extracts_verbs(self, extractor):
        """Verbs should be extracted from text."""
        text = "The knight attacked and defended with skill."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        # Note: spaCy lemmatizes to base form
        assert "attack" in lemmas
        assert "defend" in lemmas

    def test_extracts_adjectives(self, extractor):
        """Adjectives should be extracted from text."""
        text = "The ancient dragon breathed deadly fire."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        assert "ancient" in lemmas
        assert "deadly" in lemmas

    def test_extracts_noun_chunks(self, extractor):
        """Multi-word noun chunks (2-3 words) should be extracted."""
        text = "The dark elven warrior wielded a magical crystal sword."
        terms = extractor.extract(text)
        # Should find multi-word phrases
        phrases = [t for t in terms if t.pos == "phrase"]
        phrase_lemmas = {t.lemma for t in phrases}
        # Expect phrases like "dark elven warrior", "magical crystal sword"
        assert len(phrases) > 0
        # At least one phrase should have multiple words
        assert any(" " in lemma for lemma in phrase_lemmas)

    def test_filters_stopwords(self, extractor):
        """Stopwords should be filtered out."""
        text = "The wizard is very powerful and can do many things."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        # Common stopwords should not appear
        assert "the" not in lemmas
        assert "is" not in lemmas
        assert "very" not in lemmas
        assert "and" not in lemmas
        assert "can" not in lemmas
        assert "do" not in lemmas

    def test_filters_common_words(self, extractor):
        """Common English words should be filtered out."""
        text = "The people in the group went to the place."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        # Common words from our filter list should not appear
        assert "people" not in lemmas
        assert "group" not in lemmas
        assert "place" not in lemmas

    def test_deduplicates_by_lemma(self, extractor):
        """Terms should be deduplicated by lemma."""
        text = "The wizards cast spells. A wizard casts a spell."
        terms = extractor.extract(text)
        lemmas = [t.lemma for t in terms]
        # Should not have duplicates
        assert len(lemmas) == len(set(lemmas))

    def test_candidate_term_has_span(self, extractor):
        """CandidateTerm should have valid source_span."""
        text = "A dragon appeared."
        terms = extractor.extract(text)
        dragon = next((t for t in terms if t.lemma == "dragon"), None)
        assert dragon is not None
        assert dragon.source_span[0] >= 0
        assert dragon.source_span[1] > dragon.source_span[0]
        # Verify span corresponds to actual text position
        assert text[dragon.source_span[0]:dragon.source_span[1]] == "dragon"

    def test_candidate_term_structure(self, extractor):
        """CandidateTerm should have all required fields."""
        text = "The wizard cast a fireball."
        terms = extractor.extract(text)
        assert len(terms) > 0
        for term in terms:
            assert isinstance(term, CandidateTerm)
            assert isinstance(term.text, str)
            assert isinstance(term.lemma, str)
            assert term.pos in ("noun", "verb", "adjective", "phrase")
            assert isinstance(term.source_span, tuple)
            assert len(term.source_span) == 2

    def test_empty_text_returns_empty_list(self, extractor):
        """Empty text should return an empty list."""
        assert extractor.extract("") == []
        assert extractor.extract("   ") == []

    def test_filters_short_words(self, extractor):
        """Very short words (2 chars or less) should be filtered."""
        text = "I am an AI."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        # Short words like "I", "am", "an", "AI" should be filtered
        assert "i" not in lemmas
        assert "am" not in lemmas
        assert "an" not in lemmas

    def test_filters_numbers(self, extractor):
        """Purely numeric terms should be filtered."""
        text = "The 123 warriors fought in 2024."
        terms = extractor.extract(text)
        lemmas = {t.lemma for t in terms}
        assert "123" not in lemmas
        assert "2024" not in lemmas

    def test_pos_tags_correct(self, extractor):
        """POS tags should be correctly assigned."""
        text = "The ancient wizard cast a powerful spell."
        terms = extractor.extract(text)

        # Find specific terms and check their POS
        wizard = next((t for t in terms if t.lemma == "wizard"), None)
        cast = next((t for t in terms if t.lemma == "cast"), None)
        ancient = next((t for t in terms if t.lemma == "ancient"), None)

        assert wizard is not None and wizard.pos == "noun"
        assert cast is not None and cast.pos == "verb"
        assert ancient is not None and ancient.pos == "adjective"

    def test_preserves_original_text(self, extractor):
        """Original text should be preserved in CandidateTerm.text."""
        # Use lowercase to ensure it's tagged as NOUN not PROPN
        text = "The wizards cast many spells."
        terms = extractor.extract(text)
        # Find the wizard term - original should preserve case
        wizard = next((t for t in terms if t.lemma == "wizard"), None)
        assert wizard is not None
        assert wizard.text == "wizards"  # Original text form
        assert wizard.lemma == "wizard"  # Normalized lemma


class TestTermFilter:
    """Tests for the TermFilter class."""

    def test_filter_initialization(self, extractor):
        """Filter should be properly initialized with stopwords."""
        assert len(extractor.filter.stopwords) > 0

    def test_should_keep_fantasy_terms(self, extractor):
        """Fantasy-specific terms should be kept."""
        assert extractor.filter.should_keep("dragon")
        assert extractor.filter.should_keep("wizard")
        assert extractor.filter.should_keep("fireball")
        assert extractor.filter.should_keep("enchantment")

    def test_should_filter_stopwords(self, extractor):
        """Stopwords should be filtered."""
        assert not extractor.filter.should_keep("the")
        assert not extractor.filter.should_keep("and")
        assert not extractor.filter.should_keep("or")
        assert not extractor.filter.should_keep("but")

    def test_should_filter_common_words(self, extractor):
        """Common English words should be filtered."""
        assert not extractor.filter.should_keep("people")
        assert not extractor.filter.should_keep("work")
        assert not extractor.filter.should_keep("good")
        assert not extractor.filter.should_keep("just")

    def test_case_insensitive_filtering(self, extractor):
        """Filtering should be case-insensitive."""
        assert not extractor.filter.should_keep("THE")
        assert not extractor.filter.should_keep("People")
        assert not extractor.filter.should_keep("GOOD")
