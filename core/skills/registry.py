import json
from pathlib import Path
from typing import Optional


class SkillRegistry:
    """Registry for loading and managing skill manifests.

    Scans the skills directory for skill.json files and maintains
    a registry of available skills.
    """

    def __init__(self, skills_path: Path):
        """Initialize the registry.

        Args:
            skills_path: Root path to the skills directory.
        """
        self.skills_path = skills_path
        self.skills: dict[str, dict] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Scan skills directory and load all skill.json manifests."""
        if not self.skills_path.exists():
            return

        # Scan all subdirectories for skill.json files
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue

            manifest_path = skill_dir / "skill.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if manifest.get("enabled", True):
                        skill_id = manifest.get("id", skill_dir.name)
                        manifest["_path"] = str(skill_dir)
                        self.skills[skill_id] = manifest
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Warning: Failed to load skill from {skill_dir}: {e}")

    def reload(self) -> None:
        """Reload all skills from disk."""
        self.skills.clear()
        self._load_skills()

    def get_skill(self, skill_id: str) -> Optional[dict]:
        """Get a skill manifest by ID or name.

        Args:
            skill_id: The skill identifier or name.

        Returns:
            Skill manifest dict or None if not found.
        """
        # Try by ID first
        if skill_id in self.skills:
            return self.skills[skill_id]

        # Try by name (case-insensitive)
        skill_id_lower = skill_id.lower()
        for skill in self.skills.values():
            if skill.get("name", "").lower() == skill_id_lower:
                return skill
            if skill.get("id", "").lower() == skill_id_lower:
                return skill

        return None

    def find_by_trigger(self, message: str) -> Optional[dict]:
        """Find a skill that matches trigger phrases in a message.

        Args:
            message: User message to check against triggers.

        Returns:
            Matching skill manifest or None.
        """
        message_lower = message.lower()
        for skill in self.skills.values():
            triggers = skill.get("triggers", [])
            for trigger in triggers:
                if trigger.lower() in message_lower:
                    return skill
        return None

    def list_skills(self) -> list[dict]:
        """Get list of all enabled skill manifests.

        Returns:
            List of skill manifest dicts.
        """
        return list(self.skills.values())

    def get_skill_names(self) -> list[str]:
        """Get list of all skill names.

        Returns:
            List of skill names.
        """
        return [s.get("name", s.get("id", "unknown")) for s in self.skills.values()]
