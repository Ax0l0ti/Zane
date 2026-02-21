"""Executes tool calls from the LLM and returns results.

Maps tool names to backend functions:
  - execute_skill   -> SkillExecutor
  - search_knowledge -> KnowledgeManager
  - save_knowledge   -> KnowledgeManager
"""

import json
import logging
from typing import Any

from core.skills import SkillExecutor
from core.memory import KnowledgeManager

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes tool calls and returns JSON-safe results."""

    def __init__(
        self,
        skill_executor: SkillExecutor,
        knowledge_manager: KnowledgeManager
    ):
        self.skill_executor = skill_executor
        self.knowledge_manager = knowledge_manager

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict:
        """Execute a single tool call.

        Args:
            tool_name: The tool name from the LLM's tool_use block.
            tool_input: The parsed input dict from the LLM.

        Returns:
            JSON-serializable result dict. On error, returns
            {"error": str} so the LLM can see what went wrong.
        """
        try:
            if tool_name == "execute_skill":
                return self._execute_skill(tool_input)
            elif tool_name == "search_knowledge":
                return self._search_knowledge(tool_input)
            elif tool_name == "save_knowledge":
                return self._save_knowledge(tool_input)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.exception("Tool execution failed: %s", tool_name)
            return {"error": f"Tool '{tool_name}' failed: {str(e)}"}

    def _execute_skill(self, tool_input: dict) -> dict:
        skill_id = tool_input["skill_id"]
        user_message = tool_input.get("user_message", "")
        result = self.skill_executor.execute(
            skill_id,
            user_message=user_message
        )
        if result["success"]:
            return {"status": "success", "data": result["result"]}
        else:
            return {"status": "error", "message": result.get("error", "Unknown skill error")}

    def _search_knowledge(self, tool_input: dict) -> dict:
        query = tool_input["query"]
        template_type = tool_input.get("template_type")
        results = self.knowledge_manager.search_fulltext(
            query, template_type=template_type
        )
        if not results:
            return {"status": "no_results", "message": f"No entries found for '{query}'."}
        # Cap at 10 results, truncate body to keep context window manageable
        entries = []
        for entry in results[:10]:
            entries.append({
                "file_path": entry.get("file_path"),
                "template": entry.get("template"),
                "tags": entry.get("tags", []),
                "body": entry.get("body", "")[:500]
            })
        return {"status": "success", "count": len(entries), "entries": entries}

    def _save_knowledge(self, tool_input: dict) -> dict:
        template_type = tool_input["template_type"]
        identifier = tool_input["identifier"]
        fields = dict(tool_input.get("fields") or {})
        tags = tool_input.get("tags", [])
        # related_files can come from fields or top-level input
        related_files = fields.pop("related_files", tool_input.get("related_files"))

        # Debug logging to diagnose LLM field usage
        logger.info(
            "save_knowledge called: template=%s, identifier=%s, fields=%s, tags=%s",
            template_type, identifier, fields, tags
        )

        result = self.knowledge_manager.find_or_create_entry(
            template_type=template_type,
            identifier=identifier,
            fields=fields if fields else None,
            tags=tags,
            related_files=related_files
        )
        return result
