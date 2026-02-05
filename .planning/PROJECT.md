# Corpora

## What This Is

A document processing pipeline that extracts fantasy-themed vocabulary from RPG sourcebooks (PDFs, EPUBs) and outputs richly structured JSON data for use in games and applications. The system uses Claude API to classify extracted terms across multiple dimensions (genre, intent, mood, axes, etc.) and consolidates them into a deduplicated master vocabulary with IP-safe terminology.

## Core Value

Extract and classify fantasy vocabulary from source documents into structured, game-ready JSON that can power vocabulary-dependent features in apps and games.

## Current State

**Version:** v1.0 MVP (shipped 2026-02-04)
**Codebase:** 6,932 LOC Python
**Tech stack:** Python 3.13, Pydantic v2, spaCy, PyMuPDF, Anthropic SDK, Typer, Rich

**CLI Commands:**
- `corpora parse` - Extract text from PDF/EPUB
- `corpora extract` - Extract and classify vocabulary
- `corpora output` - Write .vocab.json files
- `corpora consolidate` - Merge vocab files into master
- `corpora batch` - Process entire folders

## Requirements

### Validated

- Parse text from PDF and EPUB files — v1.0
- Extract fantasy-relevant words and phrases (nouns, verbs, adjectives, multi-word phrases) — v1.0
- Classify each term with rich metadata (id, text, genre, intent, pos, axes, tags, category, canonical, mood, energy, source) — v1.0
- Output one JSON file per source document — v1.0
- Consolidate all per-document JSONs into a master vocabulary — v1.0
- Deduplicate entries and link variants to canonical forms — v1.0
- Flag/identify IP-encumbered terms for review — v1.0
- Support batch processing of document folders — v1.0

### Active

(None yet — define in next milestone)

### Out of Scope

- Real-time/streaming processing — batch is sufficient for dozens of documents
- Local LLM inference — Claude API via Max subscription handles classification
- Non-fantasy themes (Sci-Fi, Horror) — can add later, Fantasy first
- GUI/web interface — CLI scripts are sufficient
- DOCX support — deferred to v1.1

## Context

**Source material:** RPG sourcebooks (D&D, Pathfinder, etc.) which are semi-structured with spell lists, creature stat blocks, item tables, and descriptive prose.

**Output schema example:**
```json
{
  "id": "spell-fireball",
  "text": "Fireball",
  "source": "Fantasy\\Arcane_Engineering.pdf",
  "genre": "fantasy",
  "intent": "offensive",
  "pos": "noun",
  "axes": {"fire": 0.95, "force": 0.65, "air": 0.2, ...},
  "tags": ["evocation", "area-effect", "classic"],
  "category": "spell",
  "canonical": "fireball",
  "mood": "arcane",
  "energy": "fire",
  "confidence": 0.99
}
```

**IP considerations:** Any WotC-specific terms (Beholder, Forgotten Realms, etc.) need to be flagged and renamed before use. Generic fantasy terms (dragon, wizard, fireball) are fine.

**Hardware:** CPU-only machine, so heavy local inference isn't viable. Claude API handles the AI-intensive classification work.

**Volume:** Dozens of documents (10-100), not thousands.

## Constraints

- **API**: Claude API via Max subscription — no additional API costs
- **Hardware**: CPU-only, no GPU acceleration available
- **IP**: Must sanitize proprietary game terms before use in production

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Claude API over local LLM | Rich multi-dimensional classification needs high-quality model; CPU-only makes local inference slow | ✓ Good — classification quality excellent |
| Per-document JSON then consolidate | Allows incremental processing, resumability, and easier debugging | ✓ Good — enables batch resume |
| Separate IP review step | Keeps extraction clean; IP detection is subjective and benefits from human review | ✓ Good — clear separation |
| Batch API for classification | 50% cost savings on bulk operations | ✓ Good — significant savings |
| spaCy for NLP extraction | Fast, lightweight, good for noun/verb/phrase extraction | ✓ Good — ~200 common words filtered |
| PyMuPDF for PDF parsing | Built-in OCR integration, proper reading order | ✓ Good — handles complex PDFs |
| ThreadPoolExecutor for parallel processing | I/O-bound work benefits from threading | ✓ Good — scales to 8 workers |

---
*Last updated: 2026-02-04 after v1.0 milestone*
