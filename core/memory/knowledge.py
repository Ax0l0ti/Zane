"""
Implicit knowledge management - automatically extracts and retrieves facts.

This is NOT a skill. It runs on every conversation turn:
1. After user message: Extract any facts worth remembering
2. Before response: Retrieve relevant context to inject

Data is stored in memory/knowledge/facts.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.llm.factory import BaseLLM


EXTRACTION_PROMPT = """Analyze this message and extract any facts worth remembering long-term.

Focus on:
- People (names, relationships, roles, preferences)
- Projects (names, status, technologies)
- Preferences (user likes/dislikes, habits)
- Important dates or events
- Technical decisions or context

Message: "{message}"

Respond with a JSON array of facts. Each fact should be a simple, atomic statement.
If there's nothing worth remembering, respond with an empty array [].

Example response:
["Noah's friend Marcus works at Google", "The Zane project uses FastAPI"]

JSON array:"""


RETRIEVAL_PROMPT = """Given these stored facts and the current message, select which facts are relevant.

Stored facts:
{facts}

Current message: "{message}"

Return a JSON array of indices (0-based) for relevant facts.
If none are relevant, return [].

Example: [0, 3, 5]

JSON array:"""


class KnowledgeStore:
    """Manages long-term factual memory."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path("memory/knowledge")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.facts_file = self.storage_dir / "facts.json"
        self._load()

    def _load(self):
        """Load facts from disk."""
        if self.facts_file.exists():
            data = json.loads(self.facts_file.read_text(encoding="utf-8"))
            self.facts = data.get("facts", [])
        else:
            self.facts = []

    def _save(self):
        """Persist facts to disk."""
        data = {
            "updated_at": datetime.now().isoformat(),
            "facts": self.facts
        }
        self.facts_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_fact(self, fact: str) -> bool:
        """Add a fact if it's not a duplicate."""
        # Simple deduplication - exact match
        normalized = fact.strip().lower()
        existing = [f["text"].strip().lower() for f in self.facts]

        if normalized in existing:
            return False

        self.facts.append({
            "text": fact.strip(),
            "added_at": datetime.now().isoformat()
        })
        self._save()
        return True

    def get_all_facts(self) -> list[str]:
        """Return all stored facts as strings."""
        return [f["text"] for f in self.facts]

    def get_facts_by_indices(self, indices: list[int]) -> list[str]:
        """Return facts at specific indices."""
        result = []
        for i in indices:
            if 0 <= i < len(self.facts):
                result.append(self.facts[i]["text"])
        return result


class KnowledgeManager:
    """Orchestrates implicit knowledge extraction and retrieval."""

    def __init__(self, llm: BaseLLM, storage_dir: Optional[Path] = None):
        self.llm = llm
        self.store = KnowledgeStore(storage_dir)

    def extract_and_store(self, message: str) -> list[str]:
        """
        Extract facts from a message and store them.
        Called after each user message.

        Returns list of newly added facts.
        """
        prompt = EXTRACTION_PROMPT.format(message=message)

        try:
            response = self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You extract factual information. Respond only with valid JSON.",
                max_tokens=256
            )

            # Parse JSON response
            facts = json.loads(response.strip())
            if not isinstance(facts, list):
                return []

            added = []
            for fact in facts:
                if isinstance(fact, str) and fact.strip():
                    if self.store.add_fact(fact):
                        added.append(fact)

            return added

        except (json.JSONDecodeError, Exception):
            # Fail silently - extraction is best-effort
            return []

    def retrieve_relevant(self, message: str, max_facts: int = 5) -> list[str]:
        """
        Retrieve facts relevant to the current message.
        Called before generating a response.

        Returns list of relevant facts to inject into context.
        """
        all_facts = self.store.get_all_facts()

        if not all_facts:
            return []

        # Format facts with indices for the LLM
        facts_formatted = "\n".join(
            f"[{i}] {fact}" for i, fact in enumerate(all_facts)
        )

        prompt = RETRIEVAL_PROMPT.format(
            facts=facts_formatted,
            message=message
        )

        try:
            response = self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You select relevant information. Respond only with valid JSON.",
                max_tokens=64
            )

            indices = json.loads(response.strip())
            if not isinstance(indices, list):
                return []

            # Get facts at those indices, limited to max_facts
            relevant = self.store.get_facts_by_indices(indices[:max_facts])
            return relevant

        except (json.JSONDecodeError, Exception):
            return []
