"""Term filtering for vocabulary extraction.

This module provides filtering of stopwords and common English words
to ensure only fantasy-relevant vocabulary candidates are passed to Claude.
"""

from typing import Set

import spacy


# Top ~1000 common English words to filter out
# These are high-frequency words that aren't fantasy-specific
COMMON_WORDS: Set[str] = {
    # Common verbs
    "be", "have", "do", "say", "get", "make", "go", "know", "take", "see",
    "come", "think", "look", "want", "give", "use", "find", "tell", "ask",
    "work", "seem", "feel", "try", "leave", "call", "keep", "let", "begin",
    "show", "hear", "play", "run", "move", "live", "believe", "hold", "bring",
    "happen", "write", "provide", "sit", "stand", "lose", "pay", "meet",
    "include", "continue", "set", "learn", "change", "lead", "understand",
    "watch", "follow", "stop", "create", "speak", "read", "allow", "add",
    "spend", "grow", "open", "walk", "win", "offer", "remember", "love",
    "consider", "appear", "buy", "wait", "serve", "die", "send", "expect",
    "build", "stay", "fall", "cut", "reach", "kill", "remain", "suggest",
    "raise", "pass", "sell", "require", "report", "decide", "pull",

    # Common nouns
    "people", "year", "way", "day", "man", "thing", "woman", "life", "child",
    "world", "school", "state", "family", "student", "group", "country",
    "problem", "hand", "part", "place", "case", "week", "company", "system",
    "program", "question", "work", "government", "number", "night", "point",
    "home", "water", "room", "mother", "area", "money", "story", "fact",
    "month", "lot", "right", "study", "book", "eye", "job", "word", "business",
    "issue", "side", "kind", "head", "house", "service", "friend", "father",
    "power", "hour", "game", "line", "end", "member", "law", "car", "city",
    "community", "name", "president", "team", "minute", "idea", "kid", "body",
    "information", "back", "parent", "face", "others", "level", "office",
    "door", "health", "person", "art", "war", "history", "party", "result",
    "change", "morning", "reason", "research", "girl", "guy", "moment", "air",
    "teacher", "force", "education", "foot", "boy", "age", "policy", "process",
    "music", "market", "sense", "nation", "plan", "college", "interest",
    "death", "experience", "effect", "use", "class", "control", "care",
    "field", "development", "role", "effort", "rate", "heart", "drug", "show",
    "leader", "light", "voice", "wife", "police", "mind", "difference",
    "period", "building", "action", "authority", "model", "course", "century",
    "relationship", "activity", "road", "table", "form", "ground", "summer",
    "street", "view", "event", "picture", "project", "center", "value",
    "performance", "type", "paper", "material", "order", "stage", "size",
    "town", "attention", "chance", "structure", "girl", "cost", "situation",
    "society", "data", "report", "analysis", "range", "test", "deal",

    # Common adjectives
    "good", "new", "first", "last", "long", "great", "little", "own", "other",
    "old", "right", "big", "high", "different", "small", "large", "next",
    "early", "young", "important", "few", "public", "bad", "same", "able",
    "human", "local", "sure", "free", "real", "best", "better", "hard",
    "special", "easy", "clear", "recent", "certain", "personal", "open",
    "red", "difficult", "available", "likely", "short", "single", "medical",
    "current", "wrong", "private", "past", "foreign", "fine", "common",
    "poor", "natural", "significant", "similar", "hot", "dead", "central",
    "happy", "serious", "ready", "simple", "left", "physical", "general",
    "environmental", "financial", "blue", "democratic", "late", "possible",
    "full", "close", "necessary", "low", "economic", "military", "white",
    "true", "federal", "international", "strong", "various", "whole",
    "cold", "final", "main", "green", "nice", "huge", "popular", "traditional",
    "cultural",

    # Common adverbs and others
    "just", "also", "now", "only", "very", "well", "even", "back", "most",
    "then", "still", "really", "already", "much", "never", "always", "often",
    "however", "away", "again", "actually", "else", "quite", "rather",
    "probably", "certainly", "perhaps", "maybe", "yet", "though", "enough",
    "almost", "especially", "ever", "quickly", "finally", "together",
    "soon", "definitely", "later", "usually", "exactly", "sometimes",
    "obviously", "suddenly", "basically", "simply", "generally", "clearly",
    "recently", "apparently", "absolutely", "completely", "truly",
}


class TermFilter:
    """Filters out stopwords and common English words from extraction candidates.

    Uses spaCy's built-in stopwords plus a curated list of high-frequency
    English words that aren't fantasy-specific.
    """

    def __init__(self) -> None:
        """Initialize the filter with spaCy stopwords and common word list."""
        # Load spaCy's English stopwords
        nlp = spacy.blank("en")
        self.stopwords: Set[str] = set(nlp.Defaults.stop_words)

        # Add common English words
        self.stopwords.update(COMMON_WORDS)

        # Add lowercase versions for case-insensitive matching
        self.stopwords.update(word.lower() for word in self.stopwords)

    def should_keep(self, term: str) -> bool:
        """Check if a term should be kept (not filtered out).

        Args:
            term: The term to check.

        Returns:
            True if the term should be kept, False if it should be filtered.
        """
        term_lower = term.lower().strip()

        # Filter out empty terms
        if not term_lower:
            return False

        # Filter out very short terms (2 chars or less)
        if len(term_lower) <= 2:
            return False

        # Filter out terms that are all digits
        if term_lower.isdigit():
            return False

        # Filter out stopwords and common words
        if term_lower in self.stopwords:
            return False

        # For phrases, check if all words are stopwords/common
        words = term_lower.split()
        if len(words) > 1:
            content_words = [w for w in words if w not in self.stopwords]
            if len(content_words) == 0:
                return False

        return True
