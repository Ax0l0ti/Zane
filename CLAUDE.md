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
│   ├── memory/                # Conversation persistence
│   ├── routing/               # Intent detection (CHAT/SKILL/DEV)
│   └── skills/                # Registry + executor
├── skills/                    # Skill implementations
│   ├── core_ops/              # Built-in (time, git)
│   └── [user_skills]/         # Generated skills
├── ui/                        # Svelte PWA frontend
│   ├── src/                   # Svelte components + stores
│   ├── package.json           # Node dependencies
│   └── vite.config.ts         # Vite + PWA config
└── memory/
    └── conversations/         # Chat history (JSON + MD)
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

## Conversation History

Past conversations are stored in `memory/conversations/YYYY-MM/`. To understand previous context:
- Read `thread_*.json` files for full message history
- Each thread has timestamps and metadata

## Current Status

- **Phases 1-4**: Complete (skeleton, memory, routing, self-extension)
- **Phase 5**: Pending (ChromaDB vector store integration)
- **Working skills**: time_ops, workout_tracker
