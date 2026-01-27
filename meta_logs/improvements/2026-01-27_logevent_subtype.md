# Improvement: Add `subtype` to LogEvent

**Date:** 2026-01-27
**Files changed:** `main.py`, `ui/src/lib/types/index.ts`, `ui/src/lib/components/LogCallouts.svelte`

## Problem
Frontend classified log callouts by string-matching on `log.message` (e.g. checking for "retrieved" or "loaded"). Fragile — any wording change silently broke UI classification.

## Solution
Added `subtype: Optional[str] = None` to the `LogEvent` Pydantic model. Every log creation site now sets an explicit subtype (e.g. `"read"`, `"write"`, `"intent"`, `"knowledge_extract"`, `"done"`).

Frontend `classifyLog()` and `shouldSkip()` now branch on `log.subtype` instead of parsing message strings.

## Subtypes introduced
| subtype | type | Meaning |
|---------|------|---------|
| `snapshot` | tool | Git snapshot |
| `skill_gen` | tool/error | Skill code generation |
| `skill_save` | error | Failed to save skill |
| `skill_validate` | error | Validation failed |
| `skill_exec` | tool/error | Skill execution |
| `commit` | tool | Git commit |
| `receive` | thought | Incoming message (skipped in UI) |
| `done` | thought | Response complete (skipped in UI) |
| `intent` | thought | Intent detection result |
| `mode` | thought | Entering CHAT/DEV mode |
| `plan` | thought/error | Skill plan stored/failed |
| `approval` | thought | User approved/rejected plan |
| `history` | thought | Loaded conversation history |
| `knowledge_read` | thought | Retrieved knowledge entries |
| `knowledge_extract` | thought | Extracting knowledge |
| `knowledge` | error | Knowledge extraction failed |
| `read` | file_io | Read from disk |
| `write` | file_io | Write to disk |
| `validation` | error | ValueError |
| `llm` | error | LLM call failed |

## Follow-up: Tag-based retrieval + error callout visibility

**Additional files changed:** `core/memory/knowledge.py`, `memory/knowledge/people/isaac.md`, `memory/knowledge/people/reuben.md`, `ui/src/lib/components/LogCallout.svelte`

### Problems fixed
1. **"Knowledge Read/Updated" callouts were mislabeled** — thread `file_io` logs (save message, continue thread) were classified as knowledge operations. Fixed by skipping all `file_io` logs from callouts; `read`/`write` callout types now only trigger from `knowledge_read`/`knowledge_extract` subtypes.
2. **Errors not visible enough** — error callouts required clicking to expand. Now auto-expand (`expanded = calloutType === 'error'`).
3. **Empty knowledge retrieval was silent** — added an `error` log with subtype `knowledge_read` when `retrieve_relevant()` returns nothing, so users see a red ❌ callout.
4. **Broad queries like "list all people" failed** — added tag-based category detection to `retrieve_relevant()` and auto-tagging of template type on `create_entry()`. Backfilled `person` tag on existing entries.

## Why this matters
- Decouples backend message wording from frontend behavior
- New log types can be added without touching UI classification logic
- Makes filtering/analytics on logs trivial (query by subtype)
- Error callouts are now immediately visible without user interaction
- Knowledge callouts only appear for actual knowledge base operations
