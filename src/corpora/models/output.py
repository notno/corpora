"""Pydantic models for document extraction output."""

from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AxisScores(BaseModel):
    """Scores for each of the 16 magical/mechanical axes (0.0-1.0).

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

    fire: float = Field(ge=0.0, le=1.0, default=0.0)
    water: float = Field(ge=0.0, le=1.0, default=0.0)
    earth: float = Field(ge=0.0, le=1.0, default=0.0)
    air: float = Field(ge=0.0, le=1.0, default=0.0)
    light: float = Field(ge=0.0, le=1.0, default=0.0)
    shadow: float = Field(ge=0.0, le=1.0, default=0.0)
    life: float = Field(ge=0.0, le=1.0, default=0.0)
    void: float = Field(ge=0.0, le=1.0, default=0.0)
    force: float = Field(ge=0.0, le=1.0, default=0.0)
    binding: float = Field(ge=0.0, le=1.0, default=0.0)
    ward: float = Field(ge=0.0, le=1.0, default=0.0)
    sight: float = Field(ge=0.0, le=1.0, default=0.0)
    mind: float = Field(ge=0.0, le=1.0, default=0.0)
    time: float = Field(ge=0.0, le=1.0, default=0.0)
    space: float = Field(ge=0.0, le=1.0, default=0.0)
    fate: float = Field(ge=0.0, le=1.0, default=0.0)


class ClassifiedTerm(BaseModel):
    """Full vocabulary term with classification.

    This is the Phase 2 output format containing classified terms
    with the 16-axis system and full metadata.
    """

    id: str = Field(description="Unique identifier (e.g., 'src-fireball')")
    text: str = Field(description="Display text")
    source: str = Field(description="Source document identifier")
    genre: Literal["fantasy"] = "fantasy"
    intent: str = Field(description="Primary intent (offensive, defensive, utility, etc.)")
    pos: Literal["noun", "verb", "adjective", "phrase"] = Field(
        description="Part of speech"
    )
    axes: AxisScores = Field(
        default_factory=AxisScores,
        description="16-axis relevance scores"
    )
    tags: List[str] = Field(default_factory=list, description="Additional tags")
    category: str = Field(description="Term category (spell, creature, item, etc.)")
    canonical: str = Field(description="Canonical/normalized form")
    mood: str = Field(description="Mood/tone (arcane, dark, heroic, etc.)")
    energy: str = Field(default="", description="Energy type if applicable")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    secondary_intents: List[str] = Field(
        default_factory=list, description="Alternative intents"
    )


class ContentBlock(BaseModel):
    """A block of extracted content from a document."""

    type: str = Field(description="Block type: text, heading, etc.")
    text: str = Field(description="The extracted text content")
    page: Optional[int] = Field(default=None, description="Source page number (1-indexed)")
    chapter: Optional[int] = Field(default=None, description="Source chapter number (1-indexed)")


class DocumentOutput(BaseModel):
    """Output schema for parsed documents.

    This is the Phase 1 output format containing raw extracted text
    with metadata. The rich vocabulary schema (id, intent, mood, axes, etc.)
    comes from Phase 2 classification.
    """

    source: str = Field(description="Source file path")
    format: Literal["pdf", "epub"] = Field(description="Detected document format")
    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of extraction"
    )
    ocr_used: bool = Field(default=False, description="Whether OCR was used for extraction")
    metadata: dict = Field(
        default_factory=dict,
        description="Document metadata (title, author, etc.)"
    )
    content: List[ContentBlock] = Field(description="Extracted content blocks")

    def to_json_file(self, path: str) -> None:
        """Write output to JSON file.

        Args:
            path: Path to write the JSON file to.
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
