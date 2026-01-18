"""Records a provided text entry into a markdown file.

Why this exists: To enable users to store important information in a structured way for later retrieval.
"""

from pathlib import Path
import json
import datetime

class KnowledgeBaseRecorder:
    """Skill class matching class_name in skill.json."""

    def run(self, content: str) -> dict:
        """Main entry point called by executor.

        Args:
            content (str): The text content to be recorded in the markdown file.

        Returns:
            Dict with operation results. Include meaningful data.
        """
        if not isinstance(content, str):
            return {"status": "error", "message": "Content must be a string."}
        
        try:
            result = self._save_to_md_file(content)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _save_to_md_file(self, content: str) -> dict:
        """Saves the content to a markdown file with a timestamp.

        Args:
            content (str): The text content to be saved.

        Returns:
            Dict containing the filename where the content was saved.
        """
        file_path = Path("knowledge_base")
        file_path.mkdir(exist_ok=True)  # Create directory if it doesn't exist
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = file_path / f"entry_{timestamp}.md"
        
        with open(filename, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# Entry on {timestamp}\n\n{content}\n")

        return {"filename": str(filename)}