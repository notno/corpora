# Phase 2: Vocabulary Extraction & Classification - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract fantasy-relevant terms from parsed document text (Phase 1 output) and classify each term with a rich schema using Claude API. Output is classified vocabulary with full metadata. This phase handles extraction and classification only — output consolidation and IP review happen in Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Term Extraction Approach
- Hybrid NLP + Claude: Extract candidates with NLP, Claude filters and classifies
- Multi-word expression handling: 2-3 word phrases (noun chunks, named entities)
- Pre-filtering: Remove stopwords and common English words before sending to Claude
- Parts of speech: Extract nouns, verbs, and adjectives

### Classification Schema
- Ambiguous terms: Primary + secondary classification (one main category, optionally list alternatives)
- Confidence scores: Numeric 0.0-1.0 for each classification
- 16-axis system for the `axes` field with numeric scores (0.0-1.0 per axis):

**Elemental axes (0-7):**
- fire (0): Heat, destruction, passion, transformation
- water (1): Flow, adaptation, emotion, cleansing
- earth (2): Stability, endurance, material, growth
- air (3): Movement, thought, communication, freedom
- light (4): Revelation, truth, healing, purity
- shadow (5): Concealment, fear, decay, secrets
- life (6): Vitality, creation, restoration, nature
- void (7): Negation, entropy, absence, potential

**Mechanical axes (8-15):**
- force (8): Physical power, kinetic energy, impact
- binding (9): Constraints, contracts, connections
- ward (10): Protection, barriers, deflection
- sight (11): Perception, divination, awareness
- mind (12): Thought, memory, will, influence
- time (13): Duration, haste, delay, cycles
- space (14): Distance, location, teleportation
- fate (15): Probability, destiny, luck, consequence

### Claude API Integration
- Request strategy: Batch API for 50% cost savings (group terms into batches)
- Rate limit handling: Claude's discretion (implement sensible backoff/retry)
- Prompt caching: Yes, cache the system prompt to reduce token costs
- Model selection: Claude's discretion based on testing (balance quality vs cost)

### CLI Invocation
- Subcommand naming: Claude's discretion (extract, classify, or combined)
- Input format: Claude's discretion (JSON from Phase 1 minimum, optionally accept raw text)
- Preview mode: `--preview` flag shows extracted term count and sample with estimated API cost
- Progress reporting: Progress bar by default, term-by-term output in verbose mode (`-v`)

### Claude's Discretion
- Specific rate limit strategy (exponential backoff vs queue pacing)
- Model choice (Haiku vs Sonnet) — start with one, measure quality
- CLI subcommand naming
- Input format flexibility beyond Phase 1 JSON
- Batch size optimization
- Any implementation details not explicitly decided

</decisions>

<specifics>
## Specific Ideas

- The 16-axis system is core to the vocabulary schema — each term gets relevance scores across all 16 dimensions
- Axes map to both elemental (narrative) and mechanical (game) concepts
- Example: 'fireball' might score fire: 0.9, force: 0.7, void: 0.0, ward: 0.0
- The axes enable filtering vocabulary by theme/mood in game development

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-vocabulary-extraction*
*Context gathered: 2026-02-03*
