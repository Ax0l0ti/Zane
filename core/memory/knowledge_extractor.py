"""Knowledge Extractor - LLM-based extraction of facts from conversations.

Uses the LLM to analyze user messages and assistant responses,
deciding what factual information should be persisted to the knowledge base.
"""

import json
import re
from typing import Optional

from core.llm.factory import BaseLLM


EXTRACTION_PROMPT = """You are a knowledge extraction assistant. Analyze the conversation and identify factual information worth persisting to a knowledge base.

## Rules
1. Only extract FACTUAL information explicitly stated by the user
2. Skip general questions, chitchat, greetings, or hypotheticals
3. Skip information the assistant provided (only persist what the user tells us)
4. Focus on:
   - People: Names, relationships, details about specific individuals the user knows
   - Todos: Tasks, deadlines, commitments, reminders the user mentions
   - Notes: Facts, preferences, project info, technical knowledge

## Context
The user's knowledge base currently contains:
{knowledge_context}

## Conversation
User: {user_message}
Assistant: {assistant_response}

## Response Format
Respond with ONLY valid JSON (no markdown, no explanation).

For PERSON entries, use these fields:
{{
    "updates": [
        {{
            "action": "create" or "update",
            "template_type": "person",
            "identifier": "Person's Name",
            "fields": {{
                "relation": "how the user knows them (friend, brother, coworker, etc.)",
                "description": "key details about them (personality, interests, profession)",
                "birthday": "YYYY-MM-DD format or null if unknown",
                "notes": "any other information"
            }},
            "tags": ["relevant", "tags"]
        }}
    ],
    "reasoning": "brief explanation"
}}

For TODO entries:
{{
    "updates": [
        {{
            "action": "create" or "update",
            "template_type": "todo",
            "identifier": "Task Title",
            "fields": {{
                "description": "what needs to be done",
                "deadline": "YYYY-MM-DD or descriptive (e.g., 'by Friday') or null",
                "status": "pending"
            }},
            "tags": ["relevant", "tags"]
        }}
    ],
    "reasoning": "brief explanation"
}}

For NOTE entries:
{{
    "updates": [
        {{
            "action": "create" or "update",
            "template_type": "note",
            "identifier": "Topic Title",
            "fields": {{
                "summary": "brief overview",
                "details": "main content"
            }},
            "tags": ["relevant", "tags"]
        }}
    ],
    "reasoning": "brief explanation"
}}

If there's nothing worth persisting, return:
{{"updates": [], "reasoning": "explanation"}}
"""


class KnowledgeExtractor:
    """Extracts knowledge from conversations using LLM analysis.

    Uses the LLM to identify factual information worth persisting
    to the knowledge base, avoiding noise from general conversation.
    """

    def __init__(self, llm: BaseLLM):
        """Initialize the extractor.

        Args:
            llm: The LLM provider to use for extraction
        """
        self.llm = llm

    def extract_updates(
        self,
        user_message: str,
        assistant_response: str,
        knowledge_context: Optional[str] = None
    ) -> dict:
        """Extract knowledge updates from a conversation turn.

        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            knowledge_context: Formatted string of relevant existing knowledge

        Returns:
            Dict with 'updates' list and 'reasoning' string
        """
        # Skip very short messages (likely not information-rich)
        if len(user_message.strip()) < 10:
            return {
                "updates": [],
                "reasoning": "Message too short to contain meaningful knowledge"
            }

        # Skip obvious non-factual patterns
        skip_patterns = [
            r'^(hi|hello|hey|thanks|thank you|ok|okay|sure|yes|no|bye|goodbye)\b',
            r'^(what|how|when|where|why|who|can you|could you|would you|will you)\b',
            r'^\?',  # Starts with question mark
        ]

        msg_lower = user_message.strip().lower()
        for pattern in skip_patterns:
            if re.match(pattern, msg_lower, re.IGNORECASE):
                return {
                    "updates": [],
                    "reasoning": "Message appears to be a greeting, question, or acknowledgment"
                }

        # Build prompt
        prompt = EXTRACTION_PROMPT.format(
            knowledge_context=knowledge_context or "(empty)",
            user_message=user_message,
            assistant_response=assistant_response
        )

        try:
            # Call LLM for extraction
            response = self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a precise JSON-only extraction assistant. Output only valid JSON.",
                max_tokens=512
            )

            # Parse JSON response
            return self._parse_response(response)

        except Exception as e:
            return {
                "updates": [],
                "reasoning": f"Extraction failed: {str(e)}"
            }

    def _parse_response(self, response: str) -> dict:
        """Parse the LLM response into a structured dict.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed dict with 'updates' and 'reasoning'
        """
        # Try to extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_str = response.strip()

        try:
            result = json.loads(json_str)

            # Validate structure
            if "updates" not in result:
                result["updates"] = []
            if "reasoning" not in result:
                result["reasoning"] = "No reasoning provided"

            # Validate each update
            valid_updates = []
            for update in result.get("updates", []):
                if self._validate_update(update):
                    valid_updates.append(update)

            result["updates"] = valid_updates
            return result

        except json.JSONDecodeError:
            return {
                "updates": [],
                "reasoning": f"Failed to parse extraction response as JSON"
            }

    def _validate_update(self, update: dict) -> bool:
        """Validate an update dict has required fields.

        Args:
            update: The update dict to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required fields exist
        if "action" not in update or "template_type" not in update or "identifier" not in update:
            return False

        # Must have either 'fields' (new format) or 'content' (legacy)
        if "fields" not in update and "content" not in update:
            return False

        # Validate action
        if update["action"] not in ["create", "update"]:
            return False

        # Validate template type
        if update["template_type"] not in ["person", "todo", "note"]:
            return False

        return True
