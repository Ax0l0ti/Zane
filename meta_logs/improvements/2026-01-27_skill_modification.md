# Feature: Skill modification capability

**Date:** 2026-01-27

## Problem
DEV mode only supported creating new skills. When a user said "modify that skill", Zane generated a brand new skill instead of editing the existing one.

## Solution
Extended the DEV pipeline to distinguish "create" vs "modify" intent:

1. **Intent detection** — Router prompt now classifies DEV requests as create or modify, and identifies the target skill name.
2. **Skill file reader** — `SkillRegistry.get_skill_files()` returns manifest + source code for an existing skill.
3. **Modification-aware architect** — `plan_modification()` and `generate_modification()` include existing code in the LLM prompt so it outputs diffs, not new skills. `save_skill_to_path()` writes in-place.
4. **Routing** — `main.py` resolves the target skill (with fuzzy name matching), stores `action: "modify"` in the pending plan, and routes approved plans through the modification path.

## Why it matters
Self-extension is a core Zane capability. Without modification support, iterating on skills required manual editing or generating duplicates. The approval gate already provides a safety net, so the risk of misclassification is negligible.

## Files changed
- `core/routing/intent.py` — Added `dev_action` and `target_skill` fields
- `core/routing/detector.py` — Updated router prompt for create vs modify
- `core/skills/registry.py` — Added `get_skill_files()`
- `core/architect.py` — Added `plan_modification()`, `generate_modification()`, `save_skill_to_path()`
- `main.py` — DEV mode routing + `_execute_skill_plan()` modification path
