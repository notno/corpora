# Architecture Patterns

**Domain:** Document Processing / Vocabulary Extraction Pipeline for RPG Sourcebooks
**Researched:** 2026-02-03
**Confidence:** MEDIUM (patterns well-established, specific application novel)

## Recommended Architecture

### High-Level Pipeline

```
[Document Sources]     [Processing Pipeline]        [Output Layer]
     |                       |                           |
  Folder(s) ──> Ingestion ──> Parsing ──> Extraction ──> Per-Doc JSON
  (PDF/EPUB/      Queue       Engine      (Claude API)        |
   DOCX)            |           |              |              v
                    v           v              v         Consolidation
              File Discovery  Text +      Vocabulary          |
              + Validation    Structure   Classification      v
                                               |         Master JSON
                                               v              |
                                          IP Review           v
                                          + Sanitize     Final Output
```

### Component Boundaries

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| **File Discovery** | Scan folders, validate file types, build work queue | Folder path(s) | File manifest (path, type, size) | Ingestion Queue |
| **Ingestion Queue** | Manage processing order, track status, enable resume | File manifest | Processing jobs | Parser Router |
| **Parser Router** | Route documents to format-specific parsers | Processing job | Parser selection | Format Parsers |
| **PDF Parser** | Extract text + structure from PDFs | PDF file | Structured text blocks | Text Normalizer |
| **EPUB Parser** | Extract text + structure from EPUBs | EPUB file | Structured text blocks | Text Normalizer |
| **DOCX Parser** | Extract text + structure from DOCX | DOCX file | Structured text blocks | Text Normalizer |
| **Text Normalizer** | Clean, segment, prepare text for extraction | Raw text blocks | Normalized text chunks | Extraction Engine |
| **Extraction Engine** | Orchestrate Claude API calls for vocabulary | Text chunks | Raw vocabulary items | Rate Limiter |
| **Rate Limiter** | Manage API rate limits, queue requests | API requests | Throttled requests | Claude API |
| **Vocabulary Classifier** | Classify/categorize extracted terms via Claude | Raw vocabulary | Classified vocabulary | IP Reviewer |
| **IP Reviewer** | Flag/sanitize potential IP issues | Classified vocabulary | Reviewed vocabulary | Per-Doc Output |
| **Per-Doc Output** | Write individual document JSON files | Reviewed vocabulary | JSON file per document | Consolidation |
| **Consolidation Engine** | Merge per-doc files, deduplicate, build master | Per-doc JSONs | Master vocabulary JSON | Final Output |
| **Checkpoint Manager** | Track progress, enable resume from failures | All components | State persistence | All components |

## Data Flow

### Stage 1: Document Ingestion

```
Folder(s) ──> File Discovery
                   |
                   v
            ┌─────────────────┐
            │ For each file:  │
            │ - Validate type │
            │ - Check size    │
            │ - Generate ID   │
            │ - Add to queue  │
            └─────────────────┘
                   |
                   v
            Ingestion Queue (persistent)
            [file_id, path, type, status, checkpoint]
```

**Data structures:**
- File manifest: `{id, path, type, size, discovered_at}`
- Queue entry: `{id, path, type, status: pending|processing|complete|failed, checkpoint, error?}`

### Stage 2: Document Parsing

```
Queue Entry ──> Parser Router
                    |
       ┌────────────┼────────────┐
       v            v            v
   PDF Parser  EPUB Parser  DOCX Parser
       |            |            |
       └────────────┴────────────┘
                    |
                    v
             Text Normalizer
                    |
                    v
            ┌─────────────────────┐
            │ Structured Output:  │
            │ - Text blocks       │
            │ - Block types       │
            │   (prose, table,    │
            │    list, heading)   │
            │ - Page/section refs │
            └─────────────────────┘
```

**Data structures:**
- Text block: `{id, content, type: prose|table|list|stat_block|spell_list|heading, page?, section?}`
- Document structure: `{doc_id, title, blocks: TextBlock[], metadata}`

### Stage 3: Vocabulary Extraction

```
Document Structure ──> Chunking Strategy
                            |
                            v
                    ┌───────────────┐
                    │ Chunk types:  │
                    │ - Prose (1-2k)│
                    │ - Tables (as  │
                    │   complete)   │
                    │ - Lists (as   │
                    │   complete)   │
                    └───────────────┘
                            |
                            v
                    Extraction Engine
                            |
                ┌───────────┴───────────┐
                v                       v
          Rate Limiter           Prompt Templates
                |                       |
                v                       v
           Claude API  <──────────────────┘
                |
                v
        Raw Vocabulary Items
        {term, context, source_block, confidence}
```

**Data structures:**
- Chunk: `{id, doc_id, content, type, token_count}`
- Extraction request: `{chunk_id, prompt, retry_count}`
- Raw vocabulary: `{term, type_hint, context_snippet, source: {doc, block, page}}`

### Stage 4: Classification + Review

```
Raw Vocabulary ──> Vocabulary Classifier
                         |
                         v (Claude API)
                   ┌─────────────────────┐
                   │ Classification:     │
                   │ - Category          │
                   │ - Fantasy domain    │
                   │ - Confidence        │
                   │ - Related terms     │
                   └─────────────────────┘
                         |
                         v
                    IP Reviewer
                         |
                         v
                   ┌─────────────────────┐
                   │ IP Check:           │
                   │ - Flag: safe|review │
                   │   |sanitize|exclude │
                   │ - Reason (if any)   │
                   │ - Sanitized version │
                   └─────────────────────┘
```

**Data structures:**
- Classified vocabulary: `{term, category, domain, confidence, related_terms[], source}`
- Reviewed vocabulary: `{...classified, ip_status, ip_reason?, sanitized_term?}`

### Stage 5: Output Generation

```
Reviewed Vocabulary ──> Per-Doc Output
(per document)               |
                            v
                   doc_001_vocabulary.json
                   doc_002_vocabulary.json
                   doc_003_vocabulary.json
                            |
                            v
                   Consolidation Engine
                            |
                   ┌────────┴────────┐
                   │ Operations:     │
                   │ - Merge all     │
                   │ - Deduplicate   │
                   │ - Resolve       │
                   │   conflicts     │
                   │ - Sort/organize │
                   └─────────────────┘
                            |
                            v
                   master_vocabulary.json
```

**Data structures:**
- Per-doc output: `{doc_id, title, processed_at, vocabulary: ReviewedVocab[], stats}`
- Master vocabulary: `{version, generated_at, sources: DocRef[], vocabulary: MergedVocab[], stats}`

## Patterns to Follow

### Pattern 1: Pipeline with Checkpoints

**What:** Implement checkpointing at each major stage boundary to enable recovery.

**When:** After each stage completes for a document (parsing complete, extraction complete, classification complete).

**Why:** Long-running pipelines processing many documents will inevitably fail. Without checkpoints, failures require full restart.

**Example:**
```python
class CheckpointManager:
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir

    def save_checkpoint(self, doc_id: str, stage: str, data: dict):
        checkpoint = {
            "doc_id": doc_id,
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        path = self.checkpoint_dir / f"{doc_id}_{stage}.json"
        path.write_text(json.dumps(checkpoint))

    def get_last_checkpoint(self, doc_id: str) -> Optional[dict]:
        # Find most recent checkpoint for document
        checkpoints = sorted(
            self.checkpoint_dir.glob(f"{doc_id}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if checkpoints:
            return json.loads(checkpoints[0].read_text())
        return None

    def can_resume_from(self, doc_id: str, stage: str) -> bool:
        return (self.checkpoint_dir / f"{doc_id}_{stage}.json").exists()
```

### Pattern 2: Rate-Limited API Client

**What:** Wrap Claude API calls in a rate limiter that respects RPM/TPM limits.

**When:** All interactions with Claude API.

**Why:** Claude has rate limits (RPM, input tokens/minute, output tokens/minute). Exceeding them causes failures and wastes processed work.

**Example:**
```python
from dataclasses import dataclass
from time import sleep, time
from collections import deque

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 50
    tokens_per_minute: int = 40000

class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times = deque()
        self.token_counts = deque()  # (timestamp, token_count)

    def wait_if_needed(self, estimated_tokens: int):
        now = time()
        minute_ago = now - 60

        # Clean old entries
        while self.request_times and self.request_times[0] < minute_ago:
            self.request_times.popleft()
        while self.token_counts and self.token_counts[0][0] < minute_ago:
            self.token_counts.popleft()

        # Check request limit
        if len(self.request_times) >= self.config.requests_per_minute:
            wait_time = self.request_times[0] - minute_ago
            sleep(wait_time)

        # Check token limit
        current_tokens = sum(tc[1] for tc in self.token_counts)
        if current_tokens + estimated_tokens > self.config.tokens_per_minute:
            wait_time = self.token_counts[0][0] - minute_ago
            sleep(wait_time)

        self.request_times.append(now)
        self.token_counts.append((now, estimated_tokens))
```

### Pattern 3: Adapter Pattern for Parsers

**What:** Use a common interface for all document parsers, adapting format-specific libraries.

**When:** Integrating multiple parsing libraries (pdf-parser, epub-parser, python-docx).

**Why:** Allows uniform handling of documents regardless of format, easy to add new formats.

**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class TextBlock:
    id: str
    content: str
    block_type: str  # prose, table, list, heading, stat_block
    page: Optional[int] = None
    section: Optional[str] = None

@dataclass
class ParsedDocument:
    doc_id: str
    title: str
    blocks: List[TextBlock]
    metadata: dict

class DocumentParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        pass

class PDFParser(DocumentParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf'

    def parse(self, file_path: Path) -> ParsedDocument:
        # Use Docling or similar
        ...

class ParserRouter:
    def __init__(self, parsers: List[DocumentParser]):
        self.parsers = parsers

    def parse(self, file_path: Path) -> ParsedDocument:
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser.parse(file_path)
        raise ValueError(f"No parser for {file_path}")
```

### Pattern 4: Idempotent Processing

**What:** Design each stage to produce the same output if run multiple times.

**When:** All processing stages.

**Why:** Enables safe retries, recovery from failures, and re-processing without side effects.

**Example:**
```python
def process_document(doc_id: str, file_path: Path, output_dir: Path):
    output_path = output_dir / f"{doc_id}_vocabulary.json"

    # Skip if already processed (idempotent)
    if output_path.exists():
        existing = json.loads(output_path.read_text())
        if existing.get("status") == "complete":
            return existing

    # Process...
    result = do_extraction(file_path)

    # Atomic write (write to temp, then rename)
    temp_path = output_path.with_suffix('.tmp')
    temp_path.write_text(json.dumps(result))
    temp_path.rename(output_path)

    return result
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Processing

**What:** Processing entire documents in a single pass without intermediate outputs.

**Why bad:**
- Memory issues with large documents
- No recovery points on failure
- Cannot parallelize
- Hard to debug

**Instead:** Break into discrete stages with persistent intermediate outputs. Each stage writes its output before the next begins.

### Anti-Pattern 2: Synchronous API Calls in Loop

**What:** Making Claude API calls one-by-one in a tight loop without rate management.

**Why bad:**
- Hits rate limits quickly
- No batching efficiency
- Failures cascade
- No progress tracking

**Instead:** Use a request queue with rate limiter. Process in batches. Track each request's status independently.

### Anti-Pattern 3: Format-Specific Processing Logic

**What:** Having extraction/classification logic that differs by document format.

**Why bad:**
- Duplicated logic
- Inconsistent results
- Hard to maintain
- Adding formats requires touching extraction code

**Instead:** Use adapter pattern. Parsers produce uniform TextBlock output. Extraction logic is format-agnostic.

### Anti-Pattern 4: In-Memory State Only

**What:** Keeping processing state only in memory during execution.

**Why bad:**
- Lost on crash
- Cannot resume
- Cannot inspect progress
- Cannot distribute

**Instead:** Persist state to disk (queue state, checkpoints, intermediate outputs). Memory is cache, disk is truth.

### Anti-Pattern 5: Eager Consolidation

**What:** Building master vocabulary as documents process rather than as a final step.

**Why bad:**
- Partial failures leave master in inconsistent state
- Cannot re-run consolidation with different rules
- Deduplication logic mixed with extraction
- Hard to trace vocabulary origins

**Instead:** Write per-document JSON files first. Consolidation is a separate, idempotent step that reads all per-doc files and produces master output.

## Suggested Build Order

Based on component dependencies, build in this order:

### Phase 1: Core Infrastructure (No Dependencies)

**Components to build:**
1. **Checkpoint Manager** - Foundation for all recovery
2. **File Discovery** - Entry point to pipeline
3. **Data Models** - TypedDict/dataclass definitions for all structures

**Rationale:** These have no dependencies on other components. Checkpoint manager is needed by everything else.

### Phase 2: Document Parsing (Depends on Phase 1)

**Components to build:**
1. **Parser Interface** (abstract base)
2. **PDF Parser** (most common RPG format)
3. **Text Normalizer**
4. **Parser Router**

**Rationale:** PDF is likely the dominant format for RPG sourcebooks. Get one parser working end-to-end before adding others. Normalizer needed to test parser output quality.

### Phase 3: API Integration (Depends on Phase 1)

**Components to build:**
1. **Rate Limiter**
2. **Claude API Client** (wrapped with rate limiter)
3. **Prompt Templates** (extraction, classification prompts)

**Rationale:** Can build and test API integration in parallel with parsing. Rate limiter is critical infrastructure.

### Phase 4: Extraction Pipeline (Depends on Phases 2, 3)

**Components to build:**
1. **Chunking Strategy** - Split parsed documents for API
2. **Extraction Engine** - Orchestrate extraction calls
3. **Vocabulary Classifier** - Categorization via Claude

**Rationale:** Connects parsing output to API. Core value of the pipeline.

### Phase 5: Review + Output (Depends on Phase 4)

**Components to build:**
1. **IP Reviewer** - Flag/sanitize terms
2. **Per-Doc Output Writer**
3. **Consolidation Engine**

**Rationale:** Final stages of pipeline. IP review is critical for RPG content.

### Phase 6: Additional Parsers (Depends on Phase 2)

**Components to build:**
1. **EPUB Parser**
2. **DOCX Parser**

**Rationale:** Lower priority than PDF. Add after core pipeline works. Interface already defined by Phase 2.

### Phase 7: Batch Processing (Depends on all above)

**Components to build:**
1. **Batch Orchestrator** - Process folder of documents
2. **Progress Reporter** - Track batch progress
3. **Error Reporter** - Aggregate and report failures

**Rationale:** Polish and production features after core pipeline stable.

### Dependency Graph

```
Phase 1: Infrastructure
    Checkpoint Manager ────────────────────────────┐
    File Discovery ──────────────────────────┐     │
    Data Models ─────────────────────────┐   │     │
                                         │   │     │
Phase 2: Parsing                         v   v     v
    Parser Interface ─────> PDF Parser ────> Text Normalizer
                       │                           │
Phase 3: API           │                           │
    Rate Limiter ────> Claude Client               │
    Prompt Templates ───────────────────┐          │
                                        │          │
Phase 4: Extraction                     v          v
    Chunking Strategy <─────────────────────────────┘
         │
         v
    Extraction Engine ──────> Vocabulary Classifier
                                        │
Phase 5: Output                         v
    IP Reviewer <────────────────────────┘
         │
         v
    Per-Doc Output ──────> Consolidation Engine
                                   │
                                   v
                           Master Vocabulary

Phase 6: Additional Parsers (parallel, low priority)
    EPUB Parser ─┬─> Text Normalizer (shared)
    DOCX Parser ─┘
```

## Sources

### Document Processing Architecture
- [Building a Scalable Document Pre-Processing Pipeline | AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/building-a-scalable-document-pre-processing-pipeline/)
- [Azure AI Document Processing Pipeline | Microsoft Learn](https://learn.microsoft.com/en-us/samples/azure/ai-document-processing-pipeline/azure-ai-document-processing-pipeline-python/)
- [Building an On-Premise Intelligent Document Processing Pipeline | Medium](https://medium.com/@Samir.D/building-an-on-premise-intelligent-document-processing-pipeline-for-regulated-industries-9ca8a1e69070)

### Document Parsing Tools
- [Docling - GitHub](https://github.com/docling-project/docling)
- [PDF Data Extraction Benchmark 2025 | Procycons](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)
- [Building Document Parsing Pipelines with Python | Medium](https://lasha-dolenjashvili.medium.com/building-document-parsing-pipelines-with-python-3c06f62569ad)

### NLP Pipeline Patterns
- [Natural Language Processing Pipeline | GeeksforGeeks](https://www.geeksforgeeks.org/nlp/natural-language-processing-nlp-pipeline/)
- [spaCy Processing Pipelines](https://spacy.io/usage/processing-pipelines)
- [NLP Pipeline Architecture | OnlineTutorialHub](https://onlinetutorialhub.com/nlp/nlp-pipeline-architecture/)

### Rate Limiting and Batching
- [Tackling Rate Limiting for LLM Apps | Portkey](https://portkey.ai/blog/tackling-rate-limiting-for-llm-apps/)
- [Prompt Rate Limits & Batching | HackerNoon](https://hackernoon.com/prompt-rate-limits-and-batching-how-to-stop-your-llm-api-from-melting-down)
- [Rate Limits for LLM Providers | Requesty](https://www.requesty.ai/blog/rate-limits-for-llm-providers-openai-anthropic-and-deepseek)

### Pipeline Design Patterns
- [Data Pipeline Design Patterns | Start Data Engineering](https://www.startdataengineering.com/post/code-patterns/)
- [Pipeline Pattern in Python | Pybites](https://pybit.es/articles/a-practical-example-of-the-pipeline-pattern-in-python/)
- [Data Pipeline Architecture Patterns | Dagster](https://dagster.io/guides/data-pipeline/data-pipeline-architecture-5-design-patterns-with-examples)

### Error Handling and Recovery
- [Checkpointing | Dagster Glossary](https://dagster.io/glossary/checkpointing)
- [Error Handling in Distributed Systems | Temporal](https://temporal.io/blog/error-handling-in-distributed-systems)
- [Handling Data Pipeline Failures | Pipeline Mastery](https://pipelinemastery.io/handling-data-pipeline-failures-strategies-and-solutions/)
