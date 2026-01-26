"""Knowledge Base Manager - CRUD operations for knowledge entries.

Handles reading, writing, and searching markdown files with YAML frontmatter.
Files are organized by template type: people/, todos/, notes/
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


class KnowledgeManager:
    """Manages knowledge base entries with YAML frontmatter.

    Philosophy: "File System is the Database"
    - Each entry is a markdown file with YAML frontmatter
    - Templates define structure, instances live in subdirectories
    - Retrieval by type, tags, or full-text search
    """

    # Map template types to their directories
    TEMPLATE_DIRS = {
        "person": "people",
        "todo": "todos",
        "note": "notes"
    }

    def __init__(self, base_path: Path):
        """Initialize the knowledge manager.

        Args:
            base_path: Root path for knowledge storage (e.g., memory/knowledge)
        """
        self.base_path = base_path
        self.templates_path = base_path / "templates"

        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        for dir_name in self.TEMPLATE_DIRS.values():
            (self.base_path / dir_name).mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Parsing Methods
    # -------------------------------------------------------------------------

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown content.

        Args:
            content: Full markdown file content

        Returns:
            Tuple of (frontmatter_dict, body_text)
        """
        # Match YAML frontmatter between --- markers
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1)) or {}
                body = match.group(2)
                return frontmatter, body
            except yaml.YAMLError:
                return {}, content

        return {}, content

    def _serialize_frontmatter(self, frontmatter: dict, body: str) -> str:
        """Serialize frontmatter and body back to markdown.

        Args:
            frontmatter: Dict of frontmatter fields
            body: Markdown body content

        Returns:
            Full markdown content with frontmatter
        """
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n{body}"

    def _read_entry(self, file_path: Path) -> Optional[dict]:
        """Read a single knowledge entry.

        Args:
            file_path: Path to the markdown file

        Returns:
            Dict with frontmatter fields + 'body' + 'file_path', or None if not found
        """
        if not file_path.exists() or not file_path.suffix == '.md':
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            frontmatter, body = self._parse_frontmatter(content)

            return {
                **frontmatter,
                "body": body.strip(),
                "file_path": str(file_path.relative_to(self.base_path))
            }
        except Exception:
            return None

    def _get_template(self, template_type: str) -> Optional[str]:
        """Get template content for a template type.

        Args:
            template_type: Type of template (person, todo, note)

        Returns:
            Template content or None
        """
        template_path = self.templates_path / f"{template_type}.md"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return None

    def _slugify(self, text: str) -> str:
        """Convert text to a filename-safe slug.

        Args:
            text: Text to slugify

        Returns:
            Lowercase, underscore-separated slug
        """
        # Lowercase, replace spaces with underscores, remove special chars
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '_', slug)
        return slug

    def _fill_template_fields(self, template_type: str, body: str, fields: dict) -> str:
        """Fill in template sections with structured field data.

        Args:
            template_type: Type of template (person, todo, note)
            body: Template body content
            fields: Dict of field name -> value

        Returns:
            Body with fields filled in
        """
        if template_type == "person":
            # Fill Relation section
            if fields.get("relation"):
                body = body.replace(
                    "## Relation\n<!-- How do you know this person? What's their role in your life? -->",
                    f"## Relation\n{fields['relation']}"
                )
            # Fill Description section
            if fields.get("description"):
                body = body.replace(
                    "## Description\n<!-- Key details: personality, interests, profession, etc. -->",
                    f"## Description\n{fields['description']}"
                )
            # Fill Birthday section
            if fields.get("birthday"):
                body = body.replace(
                    "## Birthday\n<!-- Format: YYYY-MM-DD or \"Unknown\" -->",
                    f"## Birthday\n{fields['birthday']}"
                )
            # Fill Notes section
            if fields.get("notes"):
                body = body.replace(
                    "## Notes\n<!-- Freeform notes, memories, things to remember -->",
                    f"## Notes\n{fields['notes']}"
                )

        elif template_type == "todo":
            # Fill Description
            if fields.get("description"):
                body = body.replace(
                    "- **Description:**",
                    f"- **Description:** {fields['description']}"
                )
            # Fill Deadline
            if fields.get("deadline"):
                body = body.replace(
                    '- **Deadline:** <!-- "hard: YYYY-MM-DD" or "loose: sometime this week" or "none" -->',
                    f"- **Deadline:** {fields['deadline']}"
                )
            # Fill Status
            if fields.get("status"):
                body = body.replace(
                    "- **Status:** pending <!-- pending | in_progress | blocked | done -->",
                    f"- **Status:** {fields['status']}"
                )

        elif template_type == "note":
            # Fill Summary section
            if fields.get("summary"):
                body = body.replace(
                    "## Summary\n<!-- Brief overview of this knowledge -->",
                    f"## Summary\n{fields['summary']}"
                )
            # Fill Details section
            if fields.get("details"):
                body = body.replace(
                    "## Details\n<!-- Main content -->",
                    f"## Details\n{fields['details']}"
                )

        return body

    # -------------------------------------------------------------------------
    # Retrieval Methods
    # -------------------------------------------------------------------------

    def list_by_template(self, template_type: str) -> list[dict]:
        """List all entries of a specific template type.

        Args:
            template_type: Type of template (person, todo, note)

        Returns:
            List of entry dicts
        """
        dir_name = self.TEMPLATE_DIRS.get(template_type)
        if not dir_name:
            return []

        entries = []
        template_dir = self.base_path / dir_name

        if not template_dir.exists():
            return []

        for file_path in template_dir.glob("*.md"):
            entry = self._read_entry(file_path)
            if entry and entry.get("template") == template_type:
                entries.append(entry)

        return entries

    def search_by_tags(self, tags: list[str], match_all: bool = False) -> list[dict]:
        """Search entries by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, entry must have all tags; if False, any tag matches

        Returns:
            List of matching entry dicts
        """
        results = []
        search_tags = set(t.lower() for t in tags)

        for dir_name in self.TEMPLATE_DIRS.values():
            template_dir = self.base_path / dir_name
            if not template_dir.exists():
                continue

            for file_path in template_dir.glob("*.md"):
                entry = self._read_entry(file_path)
                if not entry:
                    continue

                entry_tags = set(t.lower() for t in entry.get("tags", []))

                if match_all:
                    if search_tags.issubset(entry_tags):
                        results.append(entry)
                else:
                    if search_tags & entry_tags:  # Any intersection
                        results.append(entry)

        return results

    def search_fulltext(
        self,
        query: str,
        template_type: Optional[str] = None
    ) -> list[dict]:
        """Full-text search across entries.

        Args:
            query: Search query (case-insensitive)
            template_type: Optional filter by template type

        Returns:
            List of matching entry dicts with relevance info
        """
        results = []
        query_lower = query.lower()

        # Determine directories to search
        if template_type and template_type in self.TEMPLATE_DIRS:
            dirs = [self.TEMPLATE_DIRS[template_type]]
        else:
            dirs = list(self.TEMPLATE_DIRS.values())

        for dir_name in dirs:
            template_dir = self.base_path / dir_name
            if not template_dir.exists():
                continue

            for file_path in template_dir.glob("*.md"):
                entry = self._read_entry(file_path)
                if not entry:
                    continue

                # Search in body and tags
                body_lower = entry.get("body", "").lower()
                tags_str = " ".join(entry.get("tags", [])).lower()
                file_name = file_path.stem.replace("_", " ").lower()

                if (query_lower in body_lower or
                    query_lower in tags_str or
                    query_lower in file_name):
                    results.append(entry)

        return results

    def retrieve_relevant(
        self,
        user_message: str,
        max_results: int = 5
    ) -> list[dict]:
        """Retrieve entries relevant to a user message.

        Heuristics:
        1. Extract capitalized names -> search people/
        2. Check task keywords (todo, deadline, remind) -> search todos/
        3. Full-text search across all entries
        4. Deduplicate and return top results

        Args:
            user_message: The user's message
            max_results: Maximum entries to return

        Returns:
            List of relevant entry dicts
        """
        results = []
        seen_paths = set()

        # 1. Extract potential names (capitalized words, 2+ chars)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        names = re.findall(name_pattern, user_message)

        for name in names:
            # Search in people
            for entry in self.list_by_template("person"):
                if name.lower() in entry.get("body", "").lower():
                    if entry["file_path"] not in seen_paths:
                        results.append(entry)
                        seen_paths.add(entry["file_path"])

                # Also check filename
                file_name = Path(entry["file_path"]).stem.replace("_", " ")
                if name.lower() in file_name.lower():
                    if entry["file_path"] not in seen_paths:
                        results.append(entry)
                        seen_paths.add(entry["file_path"])

        # 2. Check for task-related keywords
        task_keywords = ["todo", "task", "deadline", "remind", "due", "finish", "complete"]
        if any(kw in user_message.lower() for kw in task_keywords):
            for entry in self.list_by_template("todo"):
                if entry["file_path"] not in seen_paths:
                    results.append(entry)
                    seen_paths.add(entry["file_path"])

        # 3. Full-text search for remaining terms
        # Extract significant words (3+ chars, not common)
        common_words = {"the", "and", "for", "are", "but", "not", "you", "all",
                       "can", "had", "her", "was", "one", "our", "out", "has",
                       "his", "how", "its", "may", "new", "now", "old", "see",
                       "way", "who", "did", "get", "let", "say", "she", "too",
                       "use", "what", "when", "where", "which", "why", "will",
                       "with", "about", "know", "just", "like", "make", "than",
                       "that", "them", "then", "this", "time", "very", "have",
                       "from", "been", "some", "into", "your", "such", "only"}

        words = re.findall(r'\b(\w{3,})\b', user_message.lower())
        search_words = [w for w in words if w not in common_words]

        for word in search_words[:3]:  # Limit to first 3 significant words
            for entry in self.search_fulltext(word):
                if entry["file_path"] not in seen_paths:
                    results.append(entry)
                    seen_paths.add(entry["file_path"])

        return results[:max_results]

    # -------------------------------------------------------------------------
    # Update Methods
    # -------------------------------------------------------------------------

    def create_entry(
        self,
        template_type: str,
        title: str,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        related_files: Optional[list[str]] = None,
        fields: Optional[dict] = None
    ) -> dict:
        """Create a new knowledge entry.

        Args:
            template_type: Type of template (person, todo, note)
            title: Title/name for the entry
            content: Legacy - main content to add (used if fields not provided)
            tags: Optional list of tags
            related_files: Optional list of related file paths
            fields: Structured fields to fill in template sections

        Returns:
            Dict with status and created entry info
        """
        dir_name = self.TEMPLATE_DIRS.get(template_type)
        if not dir_name:
            return {"status": "error", "message": f"Unknown template type: {template_type}"}

        # Get template
        template = self._get_template(template_type)
        if not template:
            return {"status": "error", "message": f"Template not found: {template_type}"}

        # Generate filename
        slug = self._slugify(title)
        target_dir = self.base_path / dir_name
        file_path = target_dir / f"{slug}.md"

        # Handle conflicts
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = target_dir / f"{slug}_{timestamp}.md"

        # Parse template and update frontmatter
        frontmatter, body = self._parse_frontmatter(template)
        now = datetime.now().strftime("%Y-%m-%d")

        frontmatter["created"] = now
        frontmatter["updated"] = now
        frontmatter["tags"] = tags or []
        frontmatter["related_files"] = related_files or []

        # Replace placeholder in body
        body = body.replace("{Name}", title)
        body = body.replace("{Title}", title)
        body = body.replace("{Task Title}", title)

        # Fill in template sections based on fields or legacy content
        if fields:
            body = self._fill_template_fields(template_type, body, fields)
        elif content:
            # Legacy fallback - add content to notes/details section
            if template_type == "person":
                body = body.replace("## Notes\n<!-- Freeform notes, memories, things to remember -->",
                                  f"## Notes\n{content}")
            elif template_type == "note":
                body = body.replace("## Details\n<!-- Main content -->",
                                  f"## Details\n{content}")
            elif template_type == "todo":
                body = body.replace("- **Description:**",
                                  f"- **Description:** {content}")

        # Write file
        try:
            full_content = self._serialize_frontmatter(frontmatter, body)
            file_path.write_text(full_content, encoding="utf-8")

            return {
                "status": "success",
                "file_path": str(file_path.relative_to(self.base_path)),
                "template_type": template_type,
                "title": title
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_entry(
        self,
        file_path: str,
        content_updates: Optional[str] = None,
        append_content: Optional[str] = None,
        add_tags: Optional[list[str]] = None,
        remove_tags: Optional[list[str]] = None,
        fields: Optional[dict] = None,
        template_type: Optional[str] = None
    ) -> dict:
        """Update an existing knowledge entry.

        Args:
            file_path: Relative path to the entry (from knowledge base root)
            content_updates: Replace body content (if provided)
            append_content: Append to body content (if provided)
            add_tags: Tags to add
            remove_tags: Tags to remove
            fields: Structured fields to append to appropriate sections
            template_type: Type of template (needed if using fields)

        Returns:
            Dict with status and updated entry info
        """
        full_path = self.base_path / file_path

        if not full_path.exists():
            return {"status": "error", "message": f"Entry not found: {file_path}"}

        try:
            content = full_path.read_text(encoding="utf-8")
            frontmatter, body = self._parse_frontmatter(content)

            # Update tags
            current_tags = set(frontmatter.get("tags", []))
            if add_tags:
                current_tags.update(add_tags)
            if remove_tags:
                current_tags -= set(remove_tags)
            frontmatter["tags"] = list(current_tags)

            # Update timestamp
            frontmatter["updated"] = datetime.now().strftime("%Y-%m-%d")

            # Update body
            if content_updates:
                body = content_updates
            elif fields and template_type:
                # Append structured fields to appropriate sections
                body = self._append_to_fields(template_type, body, fields)
            elif append_content:
                # Legacy: Find the Notes section and append there
                if "## Notes" in body:
                    body = body.replace("## Notes\n", f"## Notes\n{append_content}\n\n", 1)
                else:
                    body += f"\n\n{append_content}"

            # Write back
            full_content = self._serialize_frontmatter(frontmatter, body)
            full_path.write_text(full_content, encoding="utf-8")

            return {
                "status": "success",
                "file_path": file_path,
                "updated": frontmatter["updated"]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _append_to_fields(self, template_type: str, body: str, fields: dict) -> str:
        """Append new content to existing template fields.

        Args:
            template_type: Type of template
            body: Current body content
            fields: Dict of field name -> value to append

        Returns:
            Updated body with appended content
        """
        if template_type == "person":
            # Append to Notes section (most common for updates)
            if fields.get("notes"):
                # Find ## Notes section and append
                if "## Notes\n" in body:
                    parts = body.split("## Notes\n", 1)
                    body = parts[0] + "## Notes\n" + fields["notes"] + "\n\n" + parts[1]
            # Update other fields if empty
            if fields.get("relation") and "<!-- How do you know this person?" in body:
                body = body.replace(
                    "## Relation\n<!-- How do you know this person? What's their role in your life? -->",
                    f"## Relation\n{fields['relation']}"
                )
            if fields.get("description") and "<!-- Key details:" in body:
                body = body.replace(
                    "## Description\n<!-- Key details: personality, interests, profession, etc. -->",
                    f"## Description\n{fields['description']}"
                )
            if fields.get("birthday") and '<!-- Format: YYYY-MM-DD' in body:
                body = body.replace(
                    "## Birthday\n<!-- Format: YYYY-MM-DD or \"Unknown\" -->",
                    f"## Birthday\n{fields['birthday']}"
                )

        elif template_type == "todo":
            if fields.get("description") and "- **Description:**\n" in body:
                body = body.replace(
                    "- **Description:**",
                    f"- **Description:** {fields['description']}"
                )

        elif template_type == "note":
            if fields.get("details"):
                if "## Details\n" in body:
                    parts = body.split("## Details\n", 1)
                    body = parts[0] + "## Details\n" + fields["details"] + "\n\n" + parts[1]

        return body

    def find_or_create_entry(
        self,
        template_type: str,
        identifier: str,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        fields: Optional[dict] = None
    ) -> dict:
        """Find an existing entry or create a new one.

        Args:
            template_type: Type of template (person, todo, note)
            identifier: Name or title to search/create
            content: Legacy - content to add (used if fields not provided)
            tags: Tags to add
            fields: Structured fields to fill/append

        Returns:
            Dict with status, action taken, and entry info
        """
        # Try to find existing entry
        slug = self._slugify(identifier)
        dir_name = self.TEMPLATE_DIRS.get(template_type)

        if not dir_name:
            return {"status": "error", "message": f"Unknown template type: {template_type}"}

        # Check for exact filename match first
        target_dir = self.base_path / dir_name
        exact_match = target_dir / f"{slug}.md"

        if exact_match.exists():
            # Update existing
            if fields:
                result = self.update_entry(
                    file_path=f"{dir_name}/{slug}.md",
                    fields=fields,
                    template_type=template_type,
                    add_tags=tags
                )
            else:
                result = self.update_entry(
                    file_path=f"{dir_name}/{slug}.md",
                    append_content=content,
                    add_tags=tags
                )
            result["action"] = "updated"
            return result

        # Search by identifier in existing entries
        for entry in self.list_by_template(template_type):
            entry_path = Path(entry["file_path"])
            if slug in entry_path.stem.lower():
                if fields:
                    result = self.update_entry(
                        file_path=entry["file_path"],
                        fields=fields,
                        template_type=template_type,
                        add_tags=tags
                    )
                else:
                    result = self.update_entry(
                        file_path=entry["file_path"],
                        append_content=content,
                        add_tags=tags
                    )
                result["action"] = "updated"
                return result

        # Not found, create new
        result = self.create_entry(
            template_type=template_type,
            title=identifier,
            content=content,
            tags=tags,
            fields=fields
        )
        result["action"] = "created"
        return result

    def format_for_context(self, entries: list[dict]) -> str:
        """Format entries for inclusion in LLM context.

        Args:
            entries: List of entry dicts

        Returns:
            Formatted string for context injection
        """
        if not entries:
            return ""

        lines = []
        for entry in entries:
            template = entry.get("template", "unknown")
            file_path = entry.get("file_path", "")
            tags = ", ".join(entry.get("tags", []))
            body = entry.get("body", "")[:500]  # Truncate long entries

            lines.append(f"### [{template}] {file_path}")
            if tags:
                lines.append(f"Tags: {tags}")
            lines.append(body)
            lines.append("")

        return "\n".join(lines)
