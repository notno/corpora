# Phase 1: Document Parsing - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract clean, normalized text from PDF and EPUB files via CLI. Users get structured output (JSON by default) containing the raw extracted text with metadata. This phase handles text extraction only — vocabulary classification happens in Phase 2.

</domain>

<decisions>
## Implementation Decisions

### CLI Invocation
- Subcommand style: `corpora parse <input>`
- Flexible input: accepts file, folder, or glob pattern
- Output destination: stdout by default, `-o/--output` for file/directory
- Required flags: `-o/--output`, `-v/--verbose`, `--format`
- Claude adds additional sensible flags

### Output Format
- Default format: JSON (.json)
- JSON includes metadata: source file path, page/section numbers, extraction timestamp, format detected
- Structure preservation: configurable via `--flat` flag
- Chapter/section representation: Claude's discretion

### OCR Behavior
- Auto-detect by default: fallback to OCR if native extraction yields insufficient text
- Override flags: `--ocr` to force, `--no-ocr` to skip
- Prompt before OCR: "This will use OCR, proceed? [y/N]" (unless --yes or non-interactive)
- OCR threshold heuristics: Claude's discretion
- OCR is optional dependency: works without OCR libs, warns if needed but missing

### Error Handling
- Failure behavior: configurable via `--fail-fast` (default: continue with errors)
- Partial extraction: configurable via `--partial` flag
- Error log: always write to `corpora-errors.log`
- Exit codes: Claude's discretion (sensible codes for scripting/CI)

### Claude's Discretion
- Additional CLI flags beyond specified ones
- OCR auto-detection threshold heuristics
- JSON structure for chapters/sections
- Specific exit codes
- Any implementation details not explicitly decided

</decisions>

<specifics>
## Specific Ideas

- Phase 1 JSON output is raw extracted text with metadata, not classified vocabulary
- Example output structure:
  ```json
  {
    "source": "5e-srd.pdf",
    "format": "pdf",
    "extracted_at": "2026-02-03T...",
    "ocr_used": false,
    "content": [...]
  }
  ```
- The rich vocabulary schema (`id`, `intent`, `mood`, `axes`, etc.) comes from Phase 2

</specifics>

<deferred>
## Deferred Ideas

- **Duplicate detection across formats** (PDF vs EPUB of same content) — belongs in Phase 3 consolidation/deduplication logic
- This is important for the user's workflow; ensure Phase 3 planning addresses it

</deferred>

---

*Phase: 01-document-parsing*
*Context gathered: 2026-02-03*
