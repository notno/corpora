"""NLP-based term extraction using spaCy.

This module extracts fantasy-relevant vocabulary candidates from text using
spaCy's linguistic features (POS tagging, noun chunks).
"""

from typing import List, Set

import spacy
from spacy.language import Language

from corpora.extraction.filters import TermFilter
from corpora.models import CandidateTerm


class TermExtractor:
    """Extracts vocabulary candidates from text using spaCy.

    Extracts:
    - Single tokens: nouns, verbs, adjectives
    - Multi-word expressions: 2-3 word noun chunks

    All candidates are filtered through TermFilter to remove stopwords
    and common English words.
    """

    def __init__(self, nlp: Language | None = None) -> None:
        """Initialize the extractor.

        Args:
            nlp: Optional pre-loaded spaCy model. If not provided,
                 loads en_core_web_sm with NER disabled for speed.
        """
        if nlp is None:
            # Load spaCy with NER disabled (not needed for extraction)
            self.nlp = spacy.load("en_core_web_sm", disable=["ner"])
        else:
            self.nlp = nlp

        self.filter = TermFilter()

    def extract(self, text: str) -> List[CandidateTerm]:
        """Extract vocabulary candidates from text.

        Args:
            text: The text to extract terms from.

        Returns:
            List of CandidateTerm objects, deduplicated by lemma.
        """
        if not text or not text.strip():
            return []

        doc = self.nlp(text)
        candidates: List[CandidateTerm] = []
        seen_lemmas: Set[str] = set()

        # Extract single tokens: NOUN, VERB, ADJ
        for token in doc:
            if token.pos_ in ("NOUN", "VERB", "ADJ"):
                # Skip stopwords using spaCy's built-in check
                if token.is_stop:
                    continue

                # Get normalized lemma
                lemma = token.lemma_.lower()

                # Apply our filter
                if not self.filter.should_keep(lemma):
                    continue

                # Skip if already seen
                if lemma in seen_lemmas:
                    continue

                seen_lemmas.add(lemma)

                # Map spaCy POS to our schema
                pos_map = {"NOUN": "noun", "VERB": "verb", "ADJ": "adjective"}
                pos = pos_map.get(token.pos_, "noun")

                candidates.append(CandidateTerm(
                    text=token.text,
                    lemma=lemma,
                    pos=pos,  # type: ignore[arg-type]
                    source_span=(token.idx, token.idx + len(token.text))
                ))

        # Extract noun chunks (multi-word expressions)
        for chunk in doc.noun_chunks:
            # Filter to content words (remove DET, stopwords)
            content_tokens = [
                t for t in chunk
                if not t.is_stop and t.pos_ not in ("DET", "PRON", "ADP", "CCONJ")
            ]

            # Only keep 2-3 word phrases
            if not (2 <= len(content_tokens) <= 3):
                continue

            # Build phrase from content words
            phrase_text = " ".join(t.text for t in content_tokens)
            phrase_lemma = " ".join(t.lemma_.lower() for t in content_tokens)

            # Apply filter to the phrase
            if not self.filter.should_keep(phrase_lemma):
                continue

            # Skip if already seen (as phrase or individual words)
            if phrase_lemma in seen_lemmas:
                continue

            seen_lemmas.add(phrase_lemma)

            # Calculate span from first to last content token
            start = content_tokens[0].idx
            end = content_tokens[-1].idx + len(content_tokens[-1].text)

            candidates.append(CandidateTerm(
                text=phrase_text,
                lemma=phrase_lemma,
                pos="phrase",
                source_span=(start, end)
            ))

        return candidates


def extract_candidates(text: str) -> List[CandidateTerm]:
    """Convenience function to extract candidates from text.

    Creates a TermExtractor instance and extracts candidates.
    For processing multiple texts, create a TermExtractor once
    and reuse it.

    Args:
        text: The text to extract terms from.

    Returns:
        List of CandidateTerm objects.
    """
    extractor = TermExtractor()
    return extractor.extract(text)
