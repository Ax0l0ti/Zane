# CLAUDE.md - Zane Exocortex Project Context

> Quick context for Claude in new conversations. Read this first!

## What Is This?

**Zane** is a self-extending exocortex (AI assistant) that runs locally. Key traits:
- **Calm & helpful persona**: Honest over appeasing, reserved but warm, emojis welcome
- **File system as database**: All state persists to JSON/MD immediately
- **Self-extending**: Zane can write his own Python skills
- **Git safety**: Snapshots before code generation, rollback on failure

## Quick Commands

```bash
# Install dependencies (first time only)
pixi install

# Run both backend + frontend dev servers
pixi run dev

# Run just the backend API
pixi run server

# Build frontend for production
pixi run build-ui
```

**Endpoints:**
- `http://localhost:8000` - FastAPI backend
- `http://localhost:5173` - Vite frontend (dev mode)

## Project Structure

```
Zane/
├── main.py                    # FastAPI entry, request routing
├── dev.py                     # Dev server launcher (backend + frontend)
├── pixi.toml                  # Python dependencies (pixi)
├── config/prompts/
│   ├── system_core.md         # Zane's stoic persona
│   └── architect.md           # Skill generation guidelines
├── core/                      # Stateless logic modules
│   ├── llm/                   # LLM providers (Claude, OpenAI)
│   ├── memory/                # Conversation + knowledge persistence
│   ├── routing/               # Intent detection (CHAT/SKILL/DEV)
│   ├── skills/                # Registry + executor
│   └── tools/                 # LLM tool definitions (save_knowledge, etc.)
├── skills/                    # Skill implementations
│   ├── core_ops/              # Built-in (time, git)
│   └── [user_skills]/         # Generated skills
├── ui/                        # Svelte PWA frontend
│   ├── src/                   # Svelte components + stores
│   ├── package.json           # Node dependencies
│   └── vite.config.ts         # Vite + PWA config
└── memory/
    ├── conversations/         # Chat history (JSON + MD)
    └── knowledge/             # Long-term knowledge base
        ├── templates/         # person.md, todo.md, note.md
        ├── people/            # Person entries
        ├── todos/             # Task entries
        └── notes/             # General notes
```

## Core Architecture

### Three Operating Modes

| Mode | When | What Happens |
|------|------|--------------|
| **CHAT** | General conversation | LLM responds with stoic persona |
| **SKILL** | Tool needed | Execute skill → LLM formats result |
| **DEV** | "Build a skill..." | Git snapshot → Generate → Validate → Commit/Rollback |

### Request Flow
```
POST /chat → Save user msg → Detect intent → Route (CHAT/SKILL/DEV) → Save response → Return
```

### Dual-Write Memory
- `thread_*.json` - Source of truth (never parse MD!)
- `thread_*.md` - Human-readable mirror

## Key Files to Know

| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | FastAPI endpoints, routing logic | ~336 |
| `core/routing/detector.py` | Intent classification via LLM | ~108 |
| `core/skills/executor.py` | Dynamic Python skill execution | ~142 |
| `core/memory/conversation.py` | Dual-write JSON+MD persistence | ~150 |
| `core/memory/knowledge.py` | Knowledge base CRUD (people, todos, notes) | ~750 |
| `core/tools/definitions.py` | LLM tool schemas (save_knowledge, etc.) | ~124 |
| `core/architect.py` | Skill self-generation | ~209 |
| `skills/core_ops/git_tools.py` | Snapshot/rollback/commit safety | ~100 |

## Skill System

### Skill Manifest (`skill.json`)
```json
{
  "id": "my_skill_v1",
  "name": "My Skill",
  "description": "What it does",
  "triggers": ["keyword1", "keyword2"],
  "entry_point": "my_skill.py",
  "class_name": "MySkill",
  "enabled": true
}
```

### Skill Class Pattern
```python
class MySkill:
    def __init__(self):
        # Load any persistent state from disk
        pass

    def run(self, **kwargs) -> dict:
        try:
            # kwargs contains: user_message, action, etc.
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

### Existing Skills
- `core_ops` (time_ops): Time/date operations
- `workout_tracker`: Exercise logging & PR tracking

## Knowledge Base System

Long-term memory stored as markdown files with YAML frontmatter. Three template types:

### Templates (`memory/knowledge/templates/`)

| Template | Directory | Fields |
|----------|-----------|--------|
| `person` | `people/` | relation, description, birthday, notes |
| `todo` | `todos/` | description, deadline, status |
| `note` | `notes/` | summary, details |

### How It Works

1. **LLM calls `save_knowledge` tool** with template_type, identifier, and fields
2. **`KnowledgeManager.find_or_create_entry()`** checks if entry exists
3. **Section-based parsing** fills `## SectionName` headers via regex (not exact string match)
4. **Frontmatter** tracks `created`, `updated`, `tags`, `related_files`

### Entry Linking

Entries can reference each other via `related_files` in frontmatter:
```yaml
related_files:
  - people/adam.md
  - notes/project_x.md
```

When creating relationships (e.g., "Sara is Adam's flatmate"), update both entries.

### Key Implementation Detail

Template filling uses **regex-based section parsing**, not exact comment matching:
```python
# Finds ## Birthday header and replaces content until next ## or EOF
pattern = rf'(## {section_name}\n).*?(?=\n## |\Z)'
```

This means template comments can change without breaking the filling logic.

## Code Conventions

### Do
- Use `pathlib.Path` for all file operations
- Return dicts from skills (JSON-serializable)
- Wrap skill logic in try/except
- Persist state to JSON files immediately
- Use ISO format for timestamps

### Don't
- Parse Markdown for context (use JSON)
- Store state in memory only
- Let exceptions propagate to HTTP layer
- Hardcode API keys (use .env)

### Naming
- Skill IDs: `lowercase_snake_case`
- Classes: `PascalCase`
- Thread files: `thread_YYYYMMDD_HHMMSS_uuid.json`

## Environment Setup

```bash
# Install Python dependencies
pixi install

# Install frontend dependencies
cd ui && npm install

# Required in .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...        # Optional fallback
```

## When Modifying This Project

### Adding a New Skill Manually
1. Create folder: `skills/my_skill/`
2. Add `skill.json` manifest
3. Add `my_skill.py` with class matching `class_name`
4. Restart server or call registry.reload()

### Modifying Core Logic
- `main.py` - Add endpoints, change routing
- `core/routing/detector.py` - Adjust intent classification
- `core/llm/providers.py` - Add new LLM providers
- `config/prompts/` - Tune persona/behavior

### Git Safety for Risky Changes
```python
from skills.core_ops.git_tools import GitTools
git = GitTools()
git.snapshot("Before my change")
# ... make changes ...
# On failure: git.rollback()
# On success: git.commit("Description of change")
```

## API Response Structure

```python
class ZaneResponse:
    text: str                    # Assistant's response
    thread_id: str               # Conversation thread ID
    audio_base64: Optional[str]  # Reserved for TTS
    logs: list[LogEvent]         # Transparency logs

class LogEvent:
    type: "thought" | "tool" | "file_io" | "error"
    subtype: Optional[str]       # e.g. "read", "write", "intent", "skill_exec"
    message: str
    metadata: Optional[dict]
```

## Common Tasks

### Read a conversation thread
```python
from core.memory import ConversationManager
cm = ConversationManager()
messages = cm.load_context("thread_20260116_122834_abc123")
```

### Execute a skill directly
```python
from core.skills import SkillExecutor
executor = SkillExecutor()
result = executor.execute("time_ops", action="get_time")
```

### Check available skills
```python
from core.skills import SkillRegistry
registry = SkillRegistry()
skills = registry.list_skills()  # Returns list of manifests
```

## Philosophy Reminders

1. **Stateless**: Server can restart anytime; all state is on disk
2. **Transparency**: Log every decision in `logs` array
3. **Safety**: Git snapshot before risky operations
4. **Simplicity**: File system is the database (no complex DBs in Phase 1-4)
5. **Dual-Write**: JSON for machines, MD for humans
6. **Document improvements**: After any non-trivial improvement, write a short log to `meta_logs/improvements/YYYY-MM-DD_<slug>.md` describing the problem, solution, and why it matters

## Conversation History

Past conversations are stored in `memory/conversations/YYYY-MM/`. To understand previous context:
- Read `thread_*.json` files for full message history
- Each thread has timestamps and metadata

## Tailscale Access

Zane is accessible over Tailscale with whois-based authentication.

- **Access URL**: `http://<tailscale-ip>:8000` (backend) or `:5173` (dev frontend)
- **Auth**: Requests from Tailscale IPs are verified via `tailscale whois`. Localhost is always bypassed (dev mode).
- **Health check**: `GET /` is exempt from auth (always accessible).

### Env Vars
| Variable | Default | Purpose |
|----------|---------|---------|
| `TAILSCALE_AUTH_ENABLED` | `true` | Set to `false` to disable Tailscale auth middleware |

### Key Files
- `core/auth/tailscale.py` — `TailscaleAuth` class, whois caching, localhost bypass
- `core/auth/middleware.py` — `TailscaleAuthMiddleware` (FastAPI middleware)
- `main.py` — Dynamic CORS origins from `tailscale ip -4`, conditional middleware setup

### Auth Flow
```
Request → Is localhost? → Yes → bypass (dev mode)
                        → No  → tailscale whois → authorized? → proceed / 403
```

### Windows Firewall Note
Pixi installs its own Node.js and Python executables. These must be explicitly allowed through Windows Firewall by executable path (the standard "Allow an app" popup only fires for system-level executables). See `meta_logs/improvements/` for details.

## Current Status

- **Phases 1-4**: Complete (skeleton, memory, routing, self-extension)
- **Phase 5**: Pending (ChromaDB vector store integration)
- **Working skills**: time_ops, workout_tracker
