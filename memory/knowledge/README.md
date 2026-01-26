---
template: none
tags: [system, documentation]
---

# Zane Knowledge Base

Structured long-term memory for the Exocortex.

## Structure

```
knowledge/
├── templates/       # Template definitions (don't modify instances here)
│   ├── person.md    # Template for people
│   ├── todo.md      # Template for task lists
│   └── note.md      # Template for general knowledge
├── people/          # People you know
├── todos/           # Task lists
└── notes/           # General knowledge entries
```

## Frontmatter Format

Every markdown file starts with YAML frontmatter:

```yaml
---
template: person|todo|note|none
tags: [tag1, tag2]
related_files: [path/to/related.md]
created: 2026-01-18
updated: 2026-01-18
---
```

## Creating New Entries

1. Copy the appropriate template from `templates/`
2. Fill in the frontmatter (especially `created` date)
3. Replace `{placeholders}` with actual content
4. Save in the appropriate folder

## Retrieval

Files are retrieved by:
- **Template type**: Find all people, all todos, etc.
- **Tags**: Search by tag across all files
- **Related files**: Follow links between entries
- **Full-text search**: Search content

