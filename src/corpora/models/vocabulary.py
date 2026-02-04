"""Pydantic models for vocabulary extraction and classification.

This module defines the data models for the hybrid NLP + Claude extraction pipeline:
- CandidateTerm: Output from spaCy-based extraction
- AxisScores: 16-axis classification scores for term categorization
- ClassifiedTerm: Full vocabulary term with Claude classification
"""

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


class CandidateTerm(BaseModel):
    """A candidate term extracted from text via NLP.

    This is the output of the spaCy extraction phase before Claude classification.
    """

    text: str = Field(description="Original text as it appears in source")
    lemma: str = Field(description="Normalized/lemmatized form")
    pos: Literal["noun", "verb", "adjective", "phrase"] = Field(
        description="Part of speech or 'phrase' for multi-word expressions"
    )
    source_span: Tuple[int, int] = Field(
        description="Character offsets (start, end) in source text"
    )


class AxisScores(BaseModel):
    """Scores for the 16-axis classification system.

    Each axis represents a magical or mechanical dimension with a relevance
    score from 0.0 (not relevant) to 1.0 (highly relevant).

    Elemental axes (0-7):
    - fire: Heat, destruction, passion, transformation
    - water: Flow, adaptation, emotion, cleansing
    - earth: Stability, endurance, material, growth
    - air: Movement, thought, communication, freedom
    - light: Revelation, truth, healing, purity
    - shadow: Concealment, fear, decay, secrets
    - life: Vitality, creation, restoration, nature
    - void: Negation, entropy, absence, potential

    Mechanical axes (8-15):
    - force: Physical power, kinetic energy, impact
    - binding: Constraints, contracts, connections
    - ward: Protection, barriers, deflection
    - sight: Perception, divination, awareness
    - mind: Thought, memory, will, influence
    - time: Duration, haste, delay, cycles
    - space: Distance, location, teleportation
    - fate: Probability, destiny, luck, consequence
    """

    # Elemental axes (0-7)
    fire: float = Field(ge=0.0, le=1.0, default=0.0)
    water: float = Field(ge=0.0, le=1.0, default=0.0)
    earth: float = Field(ge=0.0, le=1.0, default=0.0)
    air: float = Field(ge=0.0, le=1.0, default=0.0)
    light: float = Field(ge=0.0, le=1.0, default=0.0)
    shadow: float = Field(ge=0.0, le=1.0, default=0.0)
    life: float = Field(ge=0.0, le=1.0, default=0.0)
    void: float = Field(ge=0.0, le=1.0, default=0.0)

    # Mechanical axes (8-15)
    force: float = Field(ge=0.0, le=1.0, default=0.0)
    binding: float = Field(ge=0.0, le=1.0, default=0.0)
    ward: float = Field(ge=0.0, le=1.0, default=0.0)
    sight: float = Field(ge=0.0, le=1.0, default=0.0)
    mind: float = Field(ge=0.0, le=1.0, default=0.0)
    time: float = Field(ge=0.0, le=1.0, default=0.0)
    space: float = Field(ge=0.0, le=1.0, default=0.0)
    fate: float = Field(ge=0.0, le=1.0, default=0.0)


class ClassifiedTerm(BaseModel):
    """A fully classified vocabulary term.

    This is the output of the Claude classification phase, containing
    the complete vocabulary schema with 16-axis scores and metadata.
    """

    id: str = Field(description="Unique identifier (e.g., 'src-fireball')")
    text: str = Field(description="Display text")
    source: str = Field(description="Source document identifier")
    genre: Literal["fantasy"] = Field(
        default="fantasy",
        description="Genre classification"
    )
    intent: str = Field(description="Primary intent (offensive, defensive, utility, etc.)")
    pos: Literal["noun", "verb", "adjective", "phrase"] = Field(
        description="Part of speech"
    )
    axes: AxisScores = Field(
        default_factory=AxisScores,
        description="16-axis relevance scores"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Additional classification tags"
    )
    category: str = Field(description="Term category (spell, creature, item, etc.)")
    canonical: str = Field(description="Canonical/normalized form")
    mood: str = Field(description="Mood/tone (arcane, dark, heroic, etc.)")
    energy: str = Field(default="", description="Energy type if applicable")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score"
    )
    secondary_intents: List[str] = Field(
        default_factory=list,
        description="Alternative/secondary intents"
    )
    ip_flag: Optional[str] = Field(
        default=None,
        description="IP flag reason if term is potentially IP-encumbered (e.g., 'blocklist:dnd', 'classification:ip-suspect')"
    )
