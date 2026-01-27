# Fix: Plural tag retrieval in knowledge base

**Date:** 2026-01-27

## Problem
"list all people" returned nothing because the tag `"person"` is not a substring of `"people"`. Same issue would affect "todos" → "todo" and "notes" → "note".

## Solution
Added a `PLURAL_ALIASES` dict in `retrieve_relevant()` that maps common plurals to their singular tag counterparts. After direct substring matching, plural forms are also checked.

## Why it matters
Knowledge retrieval is a core loop — if users can't list entries with natural phrasing, the knowledge base feels broken. This is a minimal fix (5-line map) that covers all template types without overengineering.

## Files changed
- `core/memory/knowledge.py` — `retrieve_relevant()` step 0
