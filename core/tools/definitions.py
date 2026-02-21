"""Tool definitions for Claude tool-use API.

Builds tool schemas dynamically from the skill registry so newly
created skills are immediately available to the LLM.
"""


def build_tool_definitions(skill_manifests: list[dict]) -> list[dict]:
    """Build the complete tools array for a Claude API call.

    Args:
        skill_manifests: List of skill manifest dicts from SkillRegistry.list_skills().

    Returns:
        List of tool definition dicts in Claude API format.
    """
    tools = []

    # --- execute_skill: dynamic, one tool for all registered skills ---
    skill_ids = [s.get("id", "unknown") for s in skill_manifests]
    skill_descriptions = "\n".join(
        f"  - {s.get('id')}: {s.get('description', 'No description')}"
        for s in skill_manifests
    )

    if skill_ids:
        tools.append({
            "name": "execute_skill",
            "description": (
                f"Execute one of Zane's registered skills. Available skills:\n"
                f"{skill_descriptions}\n\n"
                "Pass the user's message so the skill can parse intent from it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "The skill ID to execute.",
                        "enum": skill_ids
                    },
                    "user_message": {
                        "type": "string",
                        "description": "The user's original message, passed to the skill for parsing."
                    }
                },
                "required": ["skill_id", "user_message"]
            }
        })

    # --- search_knowledge: on-demand knowledge base search ---
    tools.append({
        "name": "search_knowledge",
        "description": (
            "Search Zane's long-term knowledge base for information about people, "
            "todos, or notes. Use this when the pre-loaded context doesn't contain "
            "what you need, or when the user asks to list/find entries. "
            "Supports full-text search across all entry types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (name, keyword, or topic)."
                },
                "template_type": {
                    "type": "string",
                    "description": "Optional filter: 'person', 'todo', or 'note'. Omit to search all.",
                    "enum": ["person", "todo", "note"]
                }
            },
            "required": ["query"]
        }
    })

    # --- save_knowledge: proactive knowledge persistence ---
    tools.append({
        "name": "save_knowledge",
        "description": (
            "Save or update information in Zane's long-term knowledge base. "
            "Use this PROACTIVELY when the user shares factual information about "
            "people, tasks, or topics that should be remembered across conversations. "
            "This is idempotent: if an entry for the identifier already exists, "
            "it will be updated rather than duplicated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template_type": {
                    "type": "string",
                    "description": (
                        "Type of knowledge entry:\n"
                        "- person: For individuals (name, relation, notes, birthday). "
                        "Use fields.notes for their traits/details, NOT a separate note entry.\n"
                        "- todo: For tasks with deadlines.\n"
                        "- note: For standalone topics/facts NOT about a specific person."
                    ),
                    "enum": ["person", "todo", "note"]
                },
                "identifier": {
                    "type": "string",
                    "description": "Name or title for the entry (e.g., person's name, task title)."
                },
                "fields": {
                    "type": "object",
                    "description": (
                        "REQUIRED content for template sections. Put ALL descriptive details here, not in tags.\n"
                        "Person: {\"relation\": \"flatmate\", \"notes\": \"goes to gym, has stunning hair, met at party\", \"birthday\": \"03-15\"}\n"
                        "Todo: {\"description\": \"finish quarterly report\", \"deadline\": \"hard: 2026-02-10\", \"status\": \"pending\"}\n"
                        "Note: {\"summary\": \"Project architecture\", \"details\": \"Using FastAPI backend with Svelte frontend...\"}\n"
                        "IMPORTANT: A person's details go in fields.notes, NOT as a separate note entry!"
                    )
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Short categorization keywords ONLY (e.g., ['friend', 'work', 'urgent']). "
                        "Put actual content/descriptions in fields, not here."
                    )
                },
                "related_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Related knowledge entries as paths. Use when the user mentions a "
                        "relationship between entries. Example: when saving 'Sara' who is "
                        "Adam's flatmate, include [\"people/adam.md\"] and also update Adam's "
                        "entry with [\"people/sara.md\"]."
                    )
                }
            },
            "required": ["template_type", "identifier", "fields"]
        }
    })

    return tools
