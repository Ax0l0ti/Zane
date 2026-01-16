import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional

from .registry import SkillRegistry


class SkillExecutionError(Exception):
    """Raised when skill execution fails."""
    pass


class SkillExecutor:
    """Executes skills via dynamic Python import.

    Safely loads and runs skill code based on skill.json manifests.
    """

    def __init__(self, registry: SkillRegistry):
        """Initialize the executor.

        Args:
            registry: The skill registry to use for lookups.
        """
        self.registry = registry
        self._loaded_modules: dict[str, Any] = {}

    def execute(
        self,
        skill_id: str,
        method: str = "run",
        **kwargs
    ) -> dict:
        """Execute a skill method.

        Args:
            skill_id: The skill identifier.
            method: The method to call on the skill class (default: "run").
            **kwargs: Arguments to pass to the skill method.

        Returns:
            Dict with 'success', 'result', and optionally 'error' keys.
        """
        manifest = self.registry.get_skill(skill_id)
        if not manifest:
            return {
                "success": False,
                "error": f"Skill not found: {skill_id}"
            }

        try:
            # Load or get cached skill class
            skill_class = self._load_skill(manifest)

            # Instantiate and call method
            instance = skill_class()

            if not hasattr(instance, method):
                return {
                    "success": False,
                    "error": f"Skill {skill_id} has no method '{method}'"
                }

            result = getattr(instance, method)(**kwargs)

            return {
                "success": True,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}"
            }

    def _load_skill(self, manifest: dict) -> type:
        """Dynamically load a skill class.

        Args:
            manifest: The skill manifest dict.

        Returns:
            The skill class (not instantiated).

        Raises:
            SkillExecutionError: If loading fails.
        """
        skill_id = manifest.get("id")

        # Check cache
        if skill_id in self._loaded_modules:
            return self._loaded_modules[skill_id]

        skill_path = Path(manifest["_path"])
        entry_point = manifest.get("entry_point", "skill.py")
        class_name = manifest.get("class_name", "Skill")

        module_path = skill_path / entry_point
        if not module_path.exists():
            raise SkillExecutionError(f"Entry point not found: {module_path}")

        try:
            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_id}",
                module_path
            )
            if spec is None or spec.loader is None:
                raise SkillExecutionError(f"Could not load spec for {module_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"skill_{skill_id}"] = module
            spec.loader.exec_module(module)

            # Get the class
            if not hasattr(module, class_name):
                raise SkillExecutionError(
                    f"Class {class_name} not found in {entry_point}"
                )

            skill_class = getattr(module, class_name)
            self._loaded_modules[skill_id] = skill_class
            return skill_class

        except Exception as e:
            raise SkillExecutionError(f"Failed to load skill: {e}")

    def reload_skill(self, skill_id: str) -> None:
        """Force reload a skill (clear from cache).

        Args:
            skill_id: The skill to reload.
        """
        if skill_id in self._loaded_modules:
            del self._loaded_modules[skill_id]

        module_name = f"skill_{skill_id}"
        if module_name in sys.modules:
            del sys.modules[module_name]
