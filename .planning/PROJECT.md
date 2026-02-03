# Corpora

## What This Is

A document processing pipeline that extracts fantasy-themed vocabulary from RPG sourcebooks (PDFs, EPUBs, DOCX) and outputs richly structured JSON data for use in games and applications. The system uses Claude API to classify extracted terms across multiple dimensions (genre, intent, mood, axes, etc.) and consolidates them into a deduplicated master vocabulary with IP-safe terminology.

## Core Value

Extract and classify fantasy vocabulary from source documents into structured, game-ready JSON that can power vocabulary-dependent features in apps and games.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Parse text from PDF, EPUB, and DOCX files
- [ ] Extract fantasy-relevant words and phrases (nouns, verbs, adjectives, multi-word phrases)
- [ ] Classify each term with rich metadata (id, text, genre, intent, pos, axes, tags, category, canonical, mood, energy, source)
- [ ] Output one JSON file per source document
- [ ] Consolidate all per-document JSONs into a master vocabulary
- [ ] Deduplicate entries and link variants to canonical forms
- [ ] Flag/identify IP-encumbered terms for review and renaming
- [ ] Support batch processing of document folders

### Out of Scope

- Real-time/streaming processing — batch is sufficient for dozens of documents
- Local LLM inference — Claude API via Max subscription handles classification
- Non-fantasy themes (Sci-Fi, Horror) — can add later, Fantasy first
- GUI/web interface — CLI scripts are sufficient

## Context

**Source material:** RPG sourcebooks (D&D, Pathfinder, etc.) which are semi-structured with spell lists, creature stat blocks, item tables, and descriptive prose.

**Output schema example:**
```json
{
  "id": "srd-acid-arrow",
  "text": "Corrosive Dart",
  "source": "5e-srd",
  "genre": "fantasy",
  "intent": "offensive",
  "pos": "phrase",
  "axes": ["fire", "force", "light"],
  "tags": ["evocation", "level-2"],
  "category": "invocation",
  "canonical": "corrosive dart",
  "mood": "arcane",
  "energy": "acid",
  "srdSource": true,
  "old-text": "Acid Arrow"
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
| Claude API over local LLM | Rich multi-dimensional classification needs high-quality model; CPU-only makes local inference slow and lower quality | — Pending |
| Per-document JSON then consolidate | Allows incremental processing, resumability, and easier debugging vs. running list | — Pending |
| Separate IP review step | Keeps extraction clean; IP detection is subjective and benefits from human review | — Pending |

---
*Last updated: 2026-02-03 after initialization*
