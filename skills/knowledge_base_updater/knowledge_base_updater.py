"""Skill to update the knowledge base with user-defined entries in Markdown format.

Why this exists: To allow users to easily store and organize information in a structured format for retrieval.
"""

from pathlib import Path
import json

class KnowledgeBaseUpdater:
    """Skill class matching class_name in skill.json."""

    def run(self, entry: str, filename: str) -> dict:
        """Main entry point called by executor.

        Args:
            entry (str): The content to add to the knowledge base.
            filename (str): The name of the Markdown file to write to (without extension).

        Returns:
            Dict with operation results including success message or error details.
        """
        # Validate input types
        if not isinstance(entry, str) or not isinstance(filename, str):
            return {"status": "error", "message": "Invalid input types. Expected strings."}
        
        try:
            result = self._update_knowledge_base(entry, filename)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _update_knowledge_base(self, entry: str, filename: str) -> str:
        """Handles the logic of appending entry to the Markdown file.

        Args:
            entry (str): The content to save.
            filename (str): The name of the Markdown file.

        Returns:
            str: Confirmation message.
        """
        try:
            # Define the file path using pathlib
            file_path = Path("knowledge_base") / f"{filename}.md"
            # Append the entry to the Markdown file
            with file_path.open(mode='a', encoding='utf-8') as md_file:
                md_file.write(f"{entry}\n\n")
            return "Entry successfully added to the knowledge base."
        except IOError as e:
            raise Exception(f"Failed to write to file: {e}")