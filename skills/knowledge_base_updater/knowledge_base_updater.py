"""Skill to update the knowledge base with new entries.

Why this exists: This skill automates the process of updating the knowledge base, 
ensuring that the information is always current and relevant.
"""

import json
from pathlib import Path

class KnowledgeBaseUpdater:
    """Skill class matching class_name in skill.json."""

    def run(self, new_entry: str) -> dict:
        """Main entry point called by executor.

        Args:
            new_entry (str): The new piece of information to add to the knowledge base.

        Returns:
            Dict with operation results. Include meaningful data.
        """
        try:
            if not isinstance(new_entry, str) or not new_entry:
                raise ValueError("new_entry must be a non-empty string.")

            result = self._update_knowledge_base(new_entry)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _update_knowledge_base(self, new_entry: str) -> dict:
        """Private method to handle the update of the knowledge base file."""
        knowledge_base_path = Path("knowledge_base.json")

        try:
            # Load existing entries
            if knowledge_base_path.exists():
                with open(knowledge_base_path, 'r') as file:
                    knowledge_data = json.load(file)
            else:
                knowledge_data = []

            # Add the new entry
            knowledge_data.append(new_entry)

            # Save back to JSON
            with open(knowledge_base_path, 'w') as file:
                json.dump(knowledge_data, file, indent=4)

            return {"message": "Knowledge base updated successfully."}
        except Exception as e:
            raise RuntimeError(f"Failed to update knowledge base: {str(e)}")