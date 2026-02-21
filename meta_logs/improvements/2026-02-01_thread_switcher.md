# Feature: Thread switcher dropdown

**Date:** 2026-02-01

## Problem
Users could only interact with the current thread. Switching to a past conversation required knowing the thread ID and manually editing localStorage — there was no UI for browsing or jumping between threads.

## Solution
Added a thread list dropdown anchored to the header, triggered by a chevron button next to the thread ID:

1. **Backend** — `ConversationManager.list_threads()` scans month-partitioned directories, extracts lightweight metadata (id, created_at, message_count, first-user-message preview), returns sorted newest-first with pagination support.
2. **API** — `GET /threads` endpoint with `ThreadSummary` / `ThreadListResponse` Pydantic models. No proxy or SPA guard changes needed (`/thread` prefix covers `/threads`).
3. **ThreadSwitcher.svelte** — New dropdown component that fetches fresh on every open, groups threads by date (Today / Yesterday / Jan 30...), highlights the current thread with an accent left-border, and dispatches `select` / `close` events.
4. **Header integration** — Chevron button toggles the dropdown. Thread selection updates the store and clears messages. Click-to-rename on the thread ID itself is unchanged.
5. **ChatContainer reactivity** — Replaced `onMount` with a Svelte reactive `$:` block so changing `threadId` (from the switcher) triggers a re-fetch. A generation counter guards against stale responses from rapid switching.

## Why it matters
Conversation history is one of Zane's core capabilities (dual-write JSON+MD), but it was write-only from the user's perspective. Thread switching makes past context accessible and turns the UI into a proper multi-conversation interface. This is a prerequisite for future features like search across threads and thread pinning.

## Files changed
- `core/memory/conversation.py` — Added `list_threads()` method
- `main.py` — Added `ThreadSummary`, `ThreadListResponse` models + `GET /threads` endpoint
- `ui/src/lib/types/index.ts` — Added `ThreadSummary`, `ThreadListResponse` interfaces
- `ui/src/lib/api/zane.ts` — Added `listThreads()` static method
- `ui/src/lib/components/ThreadSwitcher.svelte` — New dropdown component
- `ui/src/lib/components/Header.svelte` — Chevron button, ThreadSwitcher wiring, `position: relative`
- `ui/src/lib/components/ChatContainer.svelte` — Reactive thread loading with race condition guard
