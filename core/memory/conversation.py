import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid


def _parse_month_from_id(thread_id: str) -> Optional[str]:
    """Extract YYYY-MM from thread ID. Handles both formats:
      - Old: thread_YYYYMMDD_... → YYYY-MM
      - New: t_YYMMDD_...       → 20YY-MM
    """
    old = re.match(r'^thread_(\d{4})(\d{2})\d{2}_', thread_id)
    if old:
        return f"{old.group(1)}-{old.group(2)}"
    new = re.match(r'^t_(\d{2})(\d{2})\d{2}_', thread_id)
    if new:
        return f"20{new.group(1)}-{new.group(2)}"
    return None


class ConversationManager:
    """Manages conversation persistence with dual-write (JSON + Markdown).

    Philosophy: "The File System is the Database"
    - JSON is the source of truth (machine-readable)
    - Markdown is a read-only mirror (human-readable)
    - Never parse Markdown to load context
    """

    def __init__(self, base_path: Path):
        """Initialize the conversation manager.

        Args:
            base_path: Root path for conversation storage (e.g., memory/conversations)
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_month_dir(self) -> Path:
        """Get the directory for the current month (partitioned storage)."""
        month_str = datetime.now().strftime("%Y-%m")
        month_dir = self.base_path / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir

    def _get_thread_paths(self, thread_id: str) -> tuple[Path, Path]:
        """Get paths for JSON and Markdown files for a thread.

        Parses the date from the thread ID itself so cross-month lookups
        resolve to the correct directory (not always the current month).

        Args:
            thread_id: The conversation thread identifier.

        Returns:
            Tuple of (json_path, md_path)
        """
        month_str = _parse_month_from_id(thread_id)
        if month_str:
            month_dir = self.base_path / month_str
        else:
            month_dir = self._get_month_dir()  # fallback
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir / f"{thread_id}.json", month_dir / f"{thread_id}.md"

    def create_thread(self) -> str:
        """Create a new conversation thread.

        Returns:
            The new thread ID.
        """
        thread_id = f"t_{datetime.now().strftime('%y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        json_path, md_path = self._get_thread_paths(thread_id)

        # Initialize JSON file
        thread_data = {
            "id": thread_id,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        json_path.write_text(json.dumps(thread_data, indent=2), encoding="utf-8")

        # Initialize Markdown file
        md_content = f"# Conversation: {thread_id}\n\n"
        md_content += f"*Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        md_content += "---\n\n"
        md_path.write_text(md_content, encoding="utf-8")

        return thread_id

    def save_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> None:
        """Save a message to the conversation (dual-write).

        Args:
            thread_id: The conversation thread identifier.
            role: Message role ('user' or 'assistant').
            content: The message content.
            metadata: Optional metadata dict.
        """
        json_path, md_path = self._get_thread_paths(thread_id)

        # Create thread if it doesn't exist
        if not json_path.exists():
            self.create_thread()
            json_path, md_path = self._get_thread_paths(thread_id)

        # Build message object
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            message["metadata"] = metadata

        # Append to JSON (source of truth)
        thread_data = json.loads(json_path.read_text(encoding="utf-8"))
        thread_data["messages"].append(message)
        json_path.write_text(json.dumps(thread_data, indent=2), encoding="utf-8")

        # Append to Markdown (read-only mirror)
        role_label = "**User**" if role == "user" else "**Zane**"
        timestamp = datetime.now().strftime("%H:%M:%S")
        md_entry = f"### {role_label} ({timestamp})\n\n{content}\n\n---\n\n"

        with md_path.open("a", encoding="utf-8") as f:
            f.write(md_entry)

    def load_context(self, thread_id: str) -> list[dict]:
        """Load conversation context from JSON (never from Markdown).

        Args:
            thread_id: The conversation thread identifier.

        Returns:
            List of message dicts suitable for LLM context window.
            Each dict has 'role' and 'content' keys.
        """
        json_path, _ = self._get_thread_paths(thread_id)

        if not json_path.exists():
            return []

        thread_data = json.loads(json_path.read_text(encoding="utf-8"))

        # Return only role and content for LLM context
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in thread_data.get("messages", [])
        ]

    def thread_exists(self, thread_id: str) -> bool:
        """Check if a thread exists.

        Args:
            thread_id: The conversation thread identifier.

        Returns:
            True if the thread exists, False otherwise.
        """
        json_path, _ = self._get_thread_paths(thread_id)
        return json_path.exists()

    def list_threads(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """List all conversation threads with lightweight metadata.

        Args:
            limit: Maximum number of threads to return.
            offset: Number of threads to skip (for pagination).

        Returns:
            List of dicts with id, created_at, message_count, preview.
            Sorted by created_at descending (newest first).
        """
        summaries = []
        for month_dir in self.base_path.iterdir():
            if not month_dir.is_dir() or not re.match(r'^\d{4}-\d{2}$', month_dir.name):
                continue
            for json_file in month_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    messages = data.get("messages", [])
                    preview = ""
                    for msg in messages:
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            preview = content[:80] + ("..." if len(content) > 80 else "")
                            break
                    summaries.append({
                        "id": data["id"],
                        "created_at": data.get("created_at", ""),
                        "message_count": len(messages),
                        "preview": preview or "(empty)",
                    })
                except (json.JSONDecodeError, KeyError):
                    continue
        summaries.sort(key=lambda s: s["created_at"], reverse=True)
        return summaries[offset:offset + limit]

    def rename_thread(self, old_id: str, new_id: str) -> bool:
        """Rename a thread by changing its file names and internal ID.

        Args:
            old_id: Current thread identifier.
            new_id: New thread identifier (must share the same date prefix directory).

        Returns:
            True on success.

        Raises:
            FileNotFoundError: If the old thread doesn't exist.
            FileExistsError: If the new thread ID is already taken.
        """
        old_json, old_md = self._get_thread_paths(old_id)
        new_json, new_md = self._get_thread_paths(new_id)
        if not old_json.exists():
            raise FileNotFoundError(f"Thread not found: {old_id}")
        if new_json.exists():
            raise FileExistsError(f"Thread already exists: {new_id}")
        # Update ID inside JSON
        thread_data = json.loads(old_json.read_text(encoding="utf-8"))
        thread_data["id"] = new_id
        old_json.write_text(json.dumps(thread_data, indent=2), encoding="utf-8")
        # Rename both files (same directory since date prefix is preserved)
        old_json.rename(new_json)
        if old_md.exists():
            old_md.rename(new_md)
        return True
