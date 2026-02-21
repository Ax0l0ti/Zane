# Flexible Knowledge Template Filling

**Date**: 2026-02-05
**Problem**: Knowledge entries were not being populated correctly

## The Issue

The `_fill_template_fields()` function in `core/memory/knowledge.py` used exact `str.replace()` calls to match HTML comments in templates. For example:

```python
body = body.replace(
    "## Birthday\n<!-- Format: YYYY-MM-DD or \"Unknown\" -->",
    f"## Birthday\n{fields['birthday']}"
)
```

When the template changed (the actual template had `<!-- Format: MM-DD or YYYY-MM-DD -->`), the replacement silently failed. This caused:

- **Empty entries**: `alex.md` had correct tags but all sections empty
- **Raw dict dumps**: `isaac.md`/`reuben.md` had raw dict strings in Notes section
- **Silent failures**: No errors, just unfilled templates

## The Solution

### Section-Based Parsing

Replaced exact string matching with regex-based section parsing that's agnostic to comment content:

```python
def _replace_section_content(self, body: str, section_name: str, content: str) -> str:
    """Find ## {section_name} and replace everything until next ## or EOF."""
    pattern = rf'(## {re.escape(section_name)}\n).*?(?=\n## |\Z)'
    return re.subn(pattern, rf'\g<1>{content}\n', body, count=1, flags=re.DOTALL)[0]
```

This approach:
1. Finds `## SectionName\n` header
2. Matches everything until the next `## ` or end-of-file
3. Replaces with new content, regardless of what comments were there

### New Helper Methods

| Method | Purpose |
|--------|---------|
| `_replace_section_content()` | Replace section content (for create) |
| `_append_to_section()` | Append to section, or replace if only comments |
| `_fill_todo_fields()` | Handle todo's special `- **Key:** value` format |

### Field-to-Section Mapping

Added a `FIELD_TO_SECTION` dict to map API field names to markdown headers:

```python
FIELD_TO_SECTION = {
    "relation": "Relation",
    "description": "Description",
    "birthday": "Birthday",
    "notes": "Notes",
    "summary": "Summary",
    "details": "Details",
}
```

## Additional Improvements

### Better Tool Descriptions (`core/tools/definitions.py`)

Before:
```
"Person: {relation, description, birthday, notes}."
```

After:
```
"Person: {\"relation\": \"friend from university\", \"description\": \"likes pilates\", \"birthday\": \"03-15\"}"
```

Concrete examples help the LLM understand expected format.

### Linking Example (`config/prompts/system_core.md`)

Added explicit guidance on bidirectional linking:
```
When saving "Sara" who is Adam's flatmate, include related_files: ["people/adam.md"]
on Sara's entry, and also update Adam's entry with related_files: ["people/sara.md"].
```

### Birthday Format Sync (`core/memory/knowledge_extractor.py`)

Updated extraction prompt to match template: `"MM-DD or YYYY-MM-DD format"` instead of just `"YYYY-MM-DD format"`.

## Files Changed

1. `core/memory/knowledge.py` — Main parsing rewrite (~100 lines changed)
2. `core/tools/definitions.py` — Tool schema improvements
3. `config/prompts/system_core.md` — Linking documentation
4. `core/memory/knowledge_extractor.py` — Birthday format sync

## Why This Matters

1. **Robustness**: Template comments can now change without breaking filling logic
2. **Maintainability**: Single regex pattern handles all section-based templates
3. **Correctness**: All knowledge entries will now be populated correctly
4. **Discoverability**: Better tool descriptions help the LLM use the right format

## Testing

- Unit tests for all new helper methods
- End-to-end test creating and updating a person entry
- Verified all sections populate correctly
- Verified append preserves existing content
