# Phase 2: Vocabulary Extraction & Classification - Research

**Researched:** 2026-02-03
**Domain:** NLP Term Extraction + Claude API Classification
**Confidence:** HIGH

## Summary

Phase 2 implements a hybrid NLP + Claude pipeline: spaCy extracts candidate terms from parsed document text (nouns, verbs, adjectives, noun chunks), filters out stopwords and common English, then Claude classifies the remaining fantasy-relevant vocabulary with the full schema including the 16-axis system.

The research confirms:
1. **spaCy** is the correct choice for NLP extraction (fast, production-ready, built-in noun chunks)
2. **Anthropic Batch API** provides 50% cost savings for asynchronous classification
3. **Prompt caching** reduces token costs by 90% for repeated system prompts (minimum 1024 tokens for Sonnet/Haiku)
4. **tenacity** library handles rate limiting with exponential backoff
5. **Pydantic 2** provides robust validation for the 16-axis classification schema

**Primary recommendation:** Use spaCy `en_core_web_sm` for extraction (low memory), Claude Haiku 4.5 for classification (90% of Sonnet quality at 1/3 cost), Batch API for cost efficiency, and prompt caching for the system prompt.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| spacy | >=3.7 | NLP extraction (POS tagging, noun chunks, NER) | Industry standard for production NLP, fast Cython implementation |
| anthropic | >=0.77 | Claude API client (Batch API, prompt caching) | Official SDK with built-in retry, async support |
| tenacity | >=8.0 | Retry logic with exponential backoff | De facto standard for Python retry patterns |
| pydantic | >=2.0 | Schema validation (already in project) | Already used in Phase 1, v2 has excellent performance |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| en_core_web_sm | 3.7+ | spaCy English model (small) | Default for low memory, fast processing |
| en_core_web_md | 3.7+ | spaCy English model (medium) | If similarity/vectors needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| spaCy | NLTK | NLTK is slower, more academic-focused, better for learning |
| tenacity | Manual retry | tenacity is battle-tested, handles edge cases |
| Haiku 4.5 | Sonnet 4.5 | Sonnet is 3x cost but only ~5-10% quality improvement |

**Installation:**
```bash
pip install spacy anthropic tenacity
python -m spacy download en_core_web_sm
```

## Architecture Patterns

### Recommended Project Structure
```
src/corpora/
├── extraction/           # NEW: Term extraction module
│   ├── __init__.py
│   ├── extractor.py      # NLP term extraction logic
│   ├── filters.py        # Stopword and common word filtering
│   └── models.py         # CandidateTerm, ExtractionResult
├── classification/       # NEW: Claude classification module
│   ├── __init__.py
│   ├── classifier.py     # Claude API integration
│   ├── batch.py          # Batch API handling
│   ├── prompts.py        # System prompts (cacheable)
│   └── models.py         # ClassifiedTerm (16-axis schema)
├── cli/
│   ├── extract.py        # NEW: extract/classify CLI command
│   └── ...
└── models/
    └── vocabulary.py     # NEW: VocabularyTerm schema
```

### Pattern 1: Hybrid Extraction Pipeline
**What:** Extract candidates with NLP, filter, then classify with Claude
**When to use:** Always (per CONTEXT.md locked decision)
**Example:**
```python
# Source: spaCy docs + project pattern
import spacy
from typing import List, Set

nlp = spacy.load("en_core_web_sm")
STOPWORDS: Set[str] = nlp.Defaults.stop_words

def extract_candidates(text: str) -> List[str]:
    """Extract fantasy-relevant term candidates."""
    doc = nlp(text)
    candidates = set()

    # Extract nouns, verbs, adjectives
    for token in doc:
        if token.pos_ in ("NOUN", "VERB", "ADJ"):
            if token.text.lower() not in STOPWORDS and len(token.text) > 2:
                candidates.add(token.lemma_.lower())

    # Extract noun chunks (2-3 words)
    for chunk in doc.noun_chunks:
        words = [t for t in chunk if not t.is_stop]
        if 2 <= len(words) <= 3:
            phrase = " ".join(t.text.lower() for t in words)
            candidates.add(phrase)

    return list(candidates)
```

### Pattern 2: Batch API Classification
**What:** Group terms into batches for 50% cost savings
**When to use:** For bulk classification (not real-time)
**Example:**
```python
# Source: Anthropic Batch API docs
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

client = anthropic.Anthropic()

def create_classification_batch(terms: list[str], system_prompt: str) -> str:
    """Create a batch for term classification."""
    requests = [
        Request(
            custom_id=f"term-{i}",
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5-20250929",
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}  # Cache system prompt
                    }
                ],
                messages=[{
                    "role": "user",
                    "content": f"Classify this term: {term}"
                }]
            )
        )
        for i, term in enumerate(terms)
    ]

    batch = client.messages.batches.create(requests=requests)
    return batch.id
```

### Pattern 3: Prompt Caching for System Prompts
**What:** Cache the classification system prompt to reduce costs by 90%
**When to use:** When system prompt exceeds 1024 tokens (Sonnet/Haiku minimum)
**Example:**
```python
# Source: Anthropic Prompt Caching docs
CLASSIFICATION_SYSTEM_PROMPT = """You are a fantasy vocabulary classifier...

## 16-Axis System
{detailed axis descriptions - this makes prompt > 1024 tokens}

## Output Schema
{JSON schema}
"""

# In batch request:
system=[
    {
        "type": "text",
        "text": CLASSIFICATION_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}  # 5-min TTL, 90% cost savings on reads
    }
]
```

### Pattern 4: Rate Limit Handling with Tenacity
**What:** Exponential backoff for API rate limits
**When to use:** For any direct Claude API calls (non-batch)
**Example:**
```python
# Source: tenacity docs + Anthropic patterns
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import anthropic

@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    wait=wait_exponential(multiplier=2, min=1, max=120),
    stop=stop_after_attempt(5)
)
def classify_term_sync(client: anthropic.Anthropic, term: str) -> dict:
    """Classify a single term with retry logic."""
    response = client.messages.create(
        model="claude-haiku-4-5-20250929",
        max_tokens=2048,
        messages=[{"role": "user", "content": f"Classify: {term}"}]
    )
    return response.content[0].text
```

### Anti-Patterns to Avoid
- **Processing terms one-by-one without batching:** Use Batch API for bulk classification
- **Ignoring prompt caching minimum:** System prompt must be >=1024 tokens for caching
- **Loading en_core_web_lg for simple extraction:** Use `sm` model unless you need word vectors
- **Retrying immediately on rate limits:** Always use exponential backoff

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stopword filtering | Custom word list | spaCy's built-in `is_stop` | Comprehensive, language-aware, maintained |
| Noun phrase extraction | Regex patterns | spaCy `doc.noun_chunks` | Handles grammar edge cases, dependency parsing |
| POS tagging | Rule-based patterns | spaCy POS tagger | Statistical model, context-aware |
| API retry logic | Manual sleep loops | tenacity library | Handles jitter, logging, failure modes |
| JSON schema validation | Manual checks | Pydantic models | Type safety, clear error messages |
| Batch polling | Manual status loop | SDK's built-in polling | Handles edge cases, rate limits |

**Key insight:** NLP tasks that seem simple (like "extract nouns") have many edge cases that statistical models handle automatically. Regex-based extraction will miss grammatically complex phrases and produce lower quality candidates.

## Common Pitfalls

### Pitfall 1: Memory Bloat from Large spaCy Models
**What goes wrong:** Loading `en_core_web_lg` (685k vectors) uses ~1GB RAM
**Why it happens:** Developers assume "bigger is better"
**How to avoid:** Use `en_core_web_sm` for extraction tasks - word vectors aren't needed for POS tagging
**Warning signs:** Memory warnings in deployment, slow startup

### Pitfall 2: Prompt Cache Misses
**What goes wrong:** No cost savings from prompt caching
**Why it happens:** System prompt under 1024 tokens, or content changes between requests
**How to avoid:** Ensure system prompt is verbose enough (include full axis definitions), use identical `cache_control` blocks
**Warning signs:** `cache_read_input_tokens: 0` in every response

### Pitfall 3: Batch API Timeouts
**What goes wrong:** Batch expires after 24 hours without completion
**Why it happens:** Too many requests in batch, API load spikes
**How to avoid:** Monitor batch status, consider smaller batches (1000-5000 requests), use 1-hour cache TTL
**Warning signs:** `expired` result type in batch results

### Pitfall 4: Overwhelming Claude with Context
**What goes wrong:** Sending 1000+ terms in a single message
**Why it happens:** Trying to minimize API calls
**How to avoid:** Batch terms in groups of 10-50 per message, let Batch API parallelize
**Warning signs:** Inconsistent classification quality, truncated responses

### Pitfall 5: Not Filtering Common Words
**What goes wrong:** Wasting API calls classifying "the", "with", "very"
**Why it happens:** Skipping pre-filtering step
**How to avoid:** Remove stopwords AND common English words (frequency lists) before Claude
**Warning signs:** High API costs, irrelevant terms in output

### Pitfall 6: Sync API for Bulk Processing
**What goes wrong:** Hit rate limits immediately, slow processing
**Why it happens:** Using `client.messages.create()` in a loop
**How to avoid:** Use Batch API for 10+ terms, always
**Warning signs:** 429 errors, hours of processing time

## Code Examples

Verified patterns from official sources:

### spaCy Extraction Setup
```python
# Source: spaCy docs - https://spacy.io/usage/linguistic-features
import spacy
from typing import NamedTuple, List

class CandidateTerm(NamedTuple):
    text: str
    lemma: str
    pos: str  # NOUN, VERB, ADJ, PHRASE
    source_span: tuple[int, int]  # character offsets

def setup_nlp():
    """Load spaCy with only needed components."""
    # Disable components we don't need for speed
    nlp = spacy.load("en_core_web_sm", disable=["ner"])
    return nlp

def extract_terms(nlp, text: str) -> List[CandidateTerm]:
    """Extract candidate terms from text."""
    doc = nlp(text)
    candidates = []
    seen = set()

    # Single tokens: nouns, verbs, adjectives
    for token in doc:
        if token.pos_ in ("NOUN", "VERB", "ADJ"):
            if not token.is_stop and len(token.text) > 2:
                key = token.lemma_.lower()
                if key not in seen:
                    seen.add(key)
                    candidates.append(CandidateTerm(
                        text=token.text,
                        lemma=token.lemma_.lower(),
                        pos=token.pos_,
                        source_span=(token.idx, token.idx + len(token.text))
                    ))

    # Noun chunks (2-3 words)
    for chunk in doc.noun_chunks:
        content_words = [t for t in chunk if not t.is_stop and t.pos_ != "DET"]
        if 2 <= len(content_words) <= 3:
            phrase = " ".join(t.text for t in content_words)
            key = phrase.lower()
            if key not in seen:
                seen.add(key)
                candidates.append(CandidateTerm(
                    text=phrase,
                    lemma=key,
                    pos="PHRASE",
                    source_span=(chunk.start_char, chunk.end_char)
                ))

    return candidates
```

### Pydantic Schema for 16-Axis Classification
```python
# Source: Pydantic v2 docs + CONTEXT.md schema
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List
from enum import Enum

class Axis(str, Enum):
    """16 magical/mechanical axes for classification."""
    # Elemental (0-7)
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    AIR = "air"
    LIGHT = "light"
    SHADOW = "shadow"
    LIFE = "life"
    VOID = "void"
    # Mechanical (8-15)
    FORCE = "force"
    BINDING = "binding"
    WARD = "ward"
    SIGHT = "sight"
    MIND = "mind"
    TIME = "time"
    SPACE = "space"
    FATE = "fate"

class AxisScores(BaseModel):
    """Scores for each axis (0.0-1.0)."""
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
    """Full vocabulary term with classification."""
    id: str = Field(description="Unique identifier (e.g., 'src-fireball')")
    text: str = Field(description="Display text")
    source: str = Field(description="Source document identifier")
    genre: Literal["fantasy"] = "fantasy"
    intent: str = Field(description="Primary intent (offensive, defensive, utility, etc.)")
    pos: Literal["noun", "verb", "adjective", "phrase"]
    axes: AxisScores = Field(description="16-axis relevance scores")
    tags: List[str] = Field(default_factory=list, description="Additional tags")
    category: str = Field(description="Term category (spell, creature, item, etc.)")
    canonical: str = Field(description="Canonical/normalized form")
    mood: str = Field(description="Mood/tone (arcane, dark, heroic, etc.)")
    energy: str = Field(description="Energy type if applicable")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    secondary_intents: List[str] = Field(default_factory=list, description="Alternative intents")
```

### Batch API Result Processing
```python
# Source: Anthropic Batch API docs
import anthropic
import time
from typing import Iterator

def poll_batch_completion(
    client: anthropic.Anthropic,
    batch_id: str,
    poll_interval: int = 60
) -> None:
    """Poll until batch processing completes."""
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return
        print(f"Batch {batch_id}: {batch.request_counts.processing} processing...")
        time.sleep(poll_interval)

def stream_batch_results(
    client: anthropic.Anthropic,
    batch_id: str
) -> Iterator[tuple[str, dict]]:
    """Stream batch results, yielding (custom_id, result) tuples."""
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            # Parse the JSON response from the message
            content = result.result.message.content[0].text
            yield (result.custom_id, {"status": "success", "content": content})
        elif result.result.type == "errored":
            yield (result.custom_id, {"status": "error", "error": str(result.result.error)})
        elif result.result.type == "expired":
            yield (result.custom_id, {"status": "expired"})
        elif result.result.type == "canceled":
            yield (result.custom_id, {"status": "canceled"})
```

### CLI with Preview Mode
```python
# Source: Project pattern from cli/parse.py + typer docs
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console(stderr=True)

def extract_command(
    input_file: Path = typer.Argument(..., help="Parsed document JSON from Phase 1"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
    preview: bool = typer.Option(False, "--preview", help="Preview extraction without API calls"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    batch_size: int = typer.Option(50, "--batch-size", help="Terms per batch request"),
):
    """Extract and classify vocabulary from parsed documents."""
    # Load document
    doc = load_document(input_file)

    # Extract candidates
    candidates = extract_candidates(doc)

    if preview:
        # Preview mode: show stats and sample, estimate cost
        console.print(f"[bold]Extraction Preview[/bold]")
        console.print(f"Total candidates: {len(candidates)}")
        console.print(f"Sample terms: {candidates[:10]}")

        # Estimate API cost (Haiku 4.5 batch: $0.50/$2.50 per MTok)
        est_input_tokens = len(candidates) * 200  # ~200 tokens per term prompt
        est_output_tokens = len(candidates) * 500  # ~500 tokens per classification
        est_cost = (est_input_tokens * 0.50 + est_output_tokens * 2.50) / 1_000_000
        console.print(f"Estimated API cost: ${est_cost:.2f}")
        return

    # Full extraction with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Classifying terms...", total=len(candidates))
        # ... classification logic
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NLTK for extraction | spaCy (Cython) | ~2018 | 8x faster, better accuracy |
| Sync API calls | Batch API | 2024 | 50% cost reduction |
| No caching | Prompt caching | 2024 | 90% input cost reduction |
| Claude Sonnet only | Haiku 4.5 | Late 2025 | 3x cheaper, 90% quality |
| claude-3-* models | claude-*-4-* models | 2025 | Better quality, deprecated warning |

**Deprecated/outdated:**
- `claude-3-opus-latest` - EOL Jan 5, 2026
- `claude-3-7-sonnet-latest` - EOL Feb 19, 2026
- Use `claude-haiku-4-5-20250929` or `claude-sonnet-4-5-20250929` instead

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal batch size for classification**
   - What we know: Batch API supports up to 100k requests, most complete in <1 hour
   - What's unclear: Sweet spot for balancing latency vs efficiency (1k? 5k? 10k?)
   - Recommendation: Start with 1000 per batch, measure completion times, adjust

2. **Fantasy term pre-filtering**
   - What we know: Stopwords should be removed, common English filtered
   - What's unclear: Best frequency threshold for "common" words (top 1k? 5k? 10k?)
   - Recommendation: Start with spaCy stopwords + top 5k English words, refine based on results

3. **Haiku vs Sonnet quality difference for classification**
   - What we know: Haiku 4.5 is 90% of Sonnet quality for coding tasks
   - What's unclear: Quality difference for nuanced fantasy vocabulary classification
   - Recommendation: Test both on 100 sample terms, compare axis scores, decide

## Sources

### Primary (HIGH confidence)
- [Anthropic Batch API docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing) - Full batch processing details
- [Anthropic Prompt Caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) - Caching implementation
- [spaCy Linguistic Features](https://spacy.io/usage/linguistic-features) - POS tagging, noun chunks
- [spaCy Models](https://spacy.io/models/en) - English model sizes and tradeoffs
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/concepts/models/) - Nested model validation

### Secondary (MEDIUM confidence)
- [tenacity docs](https://tenacity.readthedocs.io/) - Retry patterns verified
- [Anthropic SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) - SDK patterns
- [Claude Haiku 4.5 announcement](https://www.anthropic.com/news/claude-haiku-4-5) - Performance benchmarks

### Tertiary (LOW confidence)
- WebSearch results for model memory footprints - varies by deployment
- Community discussions on batch size optimization - anecdotal

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official docs, widely used libraries
- Architecture: HIGH - Based on official Anthropic patterns and spaCy docs
- Pitfalls: MEDIUM - Combination of official docs and community patterns
- Model recommendations: MEDIUM - Haiku 4.5 is new, benchmarks promising but limited real-world data for this specific use case

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - stable domain, but watch for Claude model updates)
