import json
from typing import Optional

from core.llm.factory import BaseLLM
from .intent import Intent


ROUTER_PROMPT = """You are an intent classifier for Zane, an AI assistant. Analyze the user's message and classify it into one of three modes:

1. **CHAT** - General conversation, questions, explanations, advice, AND knowledge management (updating info about people, notes, todos, remembering things)
2. **SKILL** - User wants to use a specific tool/skill (check available skills below)
3. **DEV** - User explicitly wants to create, modify, or build a new Python skill/tool for Zane. Must involve programming or code generation.

DEV mode is ONLY for building or modifying Python skills. These are NOT DEV:
- "Update Adam's description" → CHAT (knowledge management)
- "Add Sara to Adam's related files" → CHAT (knowledge management)
- "Remember that Pan goes to the gym" → CHAT (knowledge management)

DEV mode examples:
- "Build me a skill that tracks my reading list" → DEV (create)
- "Dev: modify the workout tracker to add sets" → DEV (modify)

For DEV mode, also determine:
- **action**: "create" if building something new, "modify" if changing an existing skill
- **target_skill**: the name/id of the skill to modify (null if creating new)

Available skills:
{skills_list}

Respond with ONLY valid JSON (no markdown, no explanation):
{{"mode": "CHAT|SKILL|DEV", "confidence": 0.0-1.0, "skill_name": "name or null", "action": "create|modify|null", "target_skill": "skill name or null", "reasoning": "brief explanation"}}

User message: {message}"""


class IntentDetector:
    """Detects user intent using LLM classification.

    The first LLM pass to decide: Is this CHAT, SKILL, or DEV mode?
    """

    def __init__(self, llm: BaseLLM):
        """Initialize the detector.

        Args:
            llm: The LLM provider to use for classification.
        """
        self.llm = llm

    def detect(
        self,
        message: str,
        available_skills: Optional[list[dict]] = None
    ) -> Intent:
        """Detect the intent of a user message.

        Args:
            message: The user's message to classify.
            available_skills: List of skill manifests (from registry).

        Returns:
            Intent object with mode, confidence, and optional skill_name.
        """
        # Format skills list for the prompt
        if available_skills:
            skills_list = "\n".join(
                f"- {s['name']}: {s['description']} (triggers: {', '.join(s.get('triggers', []))})"
                for s in available_skills
            )
        else:
            skills_list = "(No skills available)"

        # Build the classification prompt
        prompt = ROUTER_PROMPT.format(
            skills_list=skills_list,
            message=message
        )

        # Get LLM classification
        response = self.llm.generate(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )

        # Parse response
        return self._parse_response(response)

    def _parse_response(self, response: str) -> Intent:
        """Parse LLM response into Intent object.

        Args:
            response: Raw LLM response (should be JSON).

        Returns:
            Intent object. Falls back to CHAT mode on parse failure.
        """
        try:
            # Clean up response (remove markdown if present)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            return Intent(
                mode=data.get("mode", "CHAT").upper(),
                confidence=float(data.get("confidence", 0.5)),
                skill_name=data.get("skill_name"),
                reasoning=data.get("reasoning"),
                dev_action=data.get("action"),
                target_skill=data.get("target_skill")
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Default to CHAT on any parsing error
            return Intent(
                mode="CHAT",
                confidence=0.5,
                skill_name=None,
                reasoning=f"Parse error, defaulting to CHAT. Raw: {response[:100]}"
            )
