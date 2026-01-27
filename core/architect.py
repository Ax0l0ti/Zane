"""Architect module for skill self-generation.

Why this exists:
    Zane can extend himself by writing new skills. This module handles
    the meta-loop: snapshot -> generate -> validate -> commit/rollback.

Pattern: Saga Pattern
    Each step has a compensating action. If validation fails, we rollback.
    This prevents Zane from breaking himself with bad code.
"""

import json
import re
from pathlib import Path
from typing import Optional

from core.llm.factory import BaseLLM


class SkillGenerator:
    """Generates new skills using LLM and architect prompt."""

    def __init__(
        self,
        llm: BaseLLM,
        skills_path: Path,
        architect_prompt_path: Path
    ):
        """Initialize the skill generator.

        Args:
            llm: LLM provider for code generation.
            skills_path: Root path to skills directory.
            architect_prompt_path: Path to architect.md prompt.
        """
        self.llm = llm
        self.skills_path = skills_path
        self.architect_prompt = self._load_prompt(architect_prompt_path)

    def _load_prompt(self, path: Path) -> str:
        """Load the architect system prompt."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "You are a Python engineer. Write clean, robust code."

    def plan(self, user_request: str) -> dict:
        """Generate a plan for a new skill without writing code.

        Args:
            user_request: What the user wants the skill to do.

        Returns:
            Dict with 'success', 'plan_text', 'skill_id', and optionally 'error'.
        """
        planning_prompt = f"""Based on the user's request, create a PLAN for a new Zane skill.
Do NOT write any code yet. Instead, describe:

1. **Skill Name & ID**: What the skill will be called
2. **Purpose**: What it does in 1-2 sentences
3. **Trigger Words**: What phrases will activate it
4. **Data Storage**: What files/state it needs to persist
5. **Key Methods**: The main operations it will support
6. **Dependencies**: Any external libraries needed

User Request: {user_request}

Format your response as a clear, readable plan the user can approve or suggest changes to.
"""

        try:
            response = self.llm.generate(
                messages=[{"role": "user", "content": planning_prompt}],
                system_prompt=self.architect_prompt,
                max_tokens=1024
            )

            # Extract a skill ID from the plan
            skill_id = self._extract_skill_id(response, user_request)

            return {
                "success": True,
                "plan_text": response,
                "skill_id": skill_id,
                "user_request": user_request
            }

        except Exception as e:
            return {"success": False, "error": f"Planning failed: {str(e)}"}

    def _extract_skill_id(self, plan_text: str, user_request: str) -> str:
        """Extract or generate a skill ID from plan text.

        Args:
            plan_text: The generated plan
            user_request: Original user request

        Returns:
            A snake_case skill ID
        """
        # Try to find "Skill ID: xxx" in the plan
        import re as _re
        match = _re.search(r'(?:Skill\s+ID|ID)[:\s]*[`]*([a-z_0-9]+(?:_v\d+)?)[`]*', plan_text, _re.IGNORECASE)
        if match:
            return match.group(1).lower()

        # Fallback: generate from first few words of request
        words = _re.sub(r'[^\w\s]', '', user_request.lower()).split()[:3]
        return "_".join(words) + "_v1"

    def generate(self, user_request: str) -> dict:
        """Generate a new skill based on user request.

        Args:
            user_request: What the user wants the skill to do.

        Returns:
            Dict with 'success', 'skill_id', 'files', and optionally 'error'.
        """
        # Build the generation prompt
        generation_prompt = f"""Based on the user's request, generate a new skill for the Zane system.

User Request: {user_request}

Generate:
1. A skill.json manifest (in a ```json code block)
2. The Python implementation (in a ```python code block)

Make the skill focused and practical. Use a descriptive skill ID.
"""

        try:
            # Generate code using LLM
            response = self.llm.generate(
                messages=[{"role": "user", "content": generation_prompt}],
                system_prompt=self.architect_prompt,
                max_tokens=2048
            )

            # Parse the response
            return self._parse_generated_code(response)

        except Exception as e:
            return {"success": False, "error": f"Generation failed: {str(e)}"}

    def _parse_generated_code(self, response: str) -> dict:
        """Parse LLM response to extract skill.json and Python code.

        Args:
            response: Raw LLM response containing code blocks.

        Returns:
            Dict with parsed files or error.
        """
        files = {}

        # Extract JSON block (skill.json)
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                manifest = json.loads(json_match.group(1))
                files['skill.json'] = manifest
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"Invalid JSON in manifest: {e}"}
        else:
            return {"success": False, "error": "No skill.json found in response"}

        # Extract Python block
        python_match = re.search(r'```python\s*([\s\S]*?)\s*```', response)
        if python_match:
            files['python'] = python_match.group(1).strip()
        else:
            return {"success": False, "error": "No Python code found in response"}

        # Validate manifest has required fields
        required_fields = ['id', 'name', 'entry_point', 'class_name']
        for field in required_fields:
            if field not in files['skill.json']:
                return {"success": False, "error": f"Manifest missing required field: {field}"}

        skill_id = files['skill.json']['id']
        return {
            "success": True,
            "skill_id": skill_id,
            "files": files,
            "raw_response": response
        }

    def save_skill(self, generated: dict) -> dict:
        """Save generated skill files to disk.

        Args:
            generated: Result from generate() with success=True.

        Returns:
            Dict with 'success' and 'path' or 'error'.
        """
        if not generated.get("success"):
            return {"success": False, "error": "Cannot save failed generation"}

        skill_id = generated["skill_id"]
        files = generated["files"]
        manifest = files["skill.json"]

        # Create skill directory
        # Use a clean folder name from the ID
        folder_name = re.sub(r'[^a-z0-9_]', '_', skill_id.lower().replace('_v1', ''))
        skill_dir = self.skills_path / folder_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write skill.json
            manifest_path = skill_dir / "skill.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8"
            )

            # Write Python file
            entry_point = manifest.get("entry_point", "skill.py")
            python_path = skill_dir / entry_point
            python_path.write_text(files["python"], encoding="utf-8")

            return {
                "success": True,
                "path": str(skill_dir),
                "files_created": [str(manifest_path), str(python_path)]
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to save: {str(e)}"}

    def plan_modification(self, user_request: str, existing_manifest: dict, existing_code: str) -> dict:
        """Generate a plan to modify an existing skill.

        Args:
            user_request: What the user wants to change.
            existing_manifest: The current skill.json manifest.
            existing_code: The current Python source code.

        Returns:
            Dict with 'success', 'plan_text', 'skill_id', and optionally 'error'.
        """
        planning_prompt = f"""The user wants to MODIFY an existing Zane skill. Do NOT create a new skill.

**Existing Skill Manifest:**
```json
{json.dumps(existing_manifest, indent=2)}
```

**Existing Code:**
```python
{existing_code}
```

**User Request:** {user_request}

Create a MODIFICATION PLAN describing:
1. **What changes** are needed to the existing code
2. **Why** each change is necessary
3. **Updated trigger words** (if any)
4. **New dependencies** (if any)
5. **Risks or side effects** to watch for

Do NOT propose a new skill. Describe changes to the existing one.
"""

        try:
            response = self.llm.generate(
                messages=[{"role": "user", "content": planning_prompt}],
                system_prompt=self.architect_prompt,
                max_tokens=1024
            )

            return {
                "success": True,
                "plan_text": response,
                "skill_id": existing_manifest.get("id", "unknown"),
                "user_request": user_request
            }
        except Exception as e:
            return {"success": False, "error": f"Modification planning failed: {str(e)}"}

    def generate_modification(self, user_request: str, existing_manifest: dict, existing_code: str) -> dict:
        """Generate modified skill code based on user request and existing code.

        Args:
            user_request: What the user wants to change.
            existing_manifest: The current skill.json manifest.
            existing_code: The current Python source code.

        Returns:
            Dict with 'success', 'skill_id', 'files', and optionally 'error'.
        """
        generation_prompt = f"""Modify an existing Zane skill based on the user's request.

**Existing Skill Manifest:**
```json
{json.dumps(existing_manifest, indent=2)}
```

**Existing Code:**
```python
{existing_code}
```

**User Request:** {user_request}

Output the MODIFIED versions:
1. The updated skill.json manifest (in a ```json code block) — keep the same id
2. The updated Python implementation (in a ```python code block)

Only change what's necessary. Preserve existing functionality unless the user asks to remove it.
"""

        try:
            response = self.llm.generate(
                messages=[{"role": "user", "content": generation_prompt}],
                system_prompt=self.architect_prompt,
                max_tokens=2048
            )

            return self._parse_generated_code(response)
        except Exception as e:
            return {"success": False, "error": f"Modification generation failed: {str(e)}"}

    def save_skill_to_path(self, generated: dict, target_dir: Path) -> dict:
        """Save generated skill files to a specific directory (for in-place updates).

        Args:
            generated: Result from generate() or generate_modification().
            target_dir: The existing skill directory to write into.

        Returns:
            Dict with 'success' and 'path' or 'error'.
        """
        if not generated.get("success"):
            return {"success": False, "error": "Cannot save failed generation"}

        files = generated["files"]
        manifest = files["skill.json"]

        try:
            manifest_path = target_dir / "skill.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8"
            )

            entry_point = manifest.get("entry_point", "skill.py")
            python_path = target_dir / entry_point
            python_path.write_text(files["python"], encoding="utf-8")

            return {
                "success": True,
                "path": str(target_dir),
                "files_created": [str(manifest_path), str(python_path)]
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to save: {str(e)}"}

    def validate_skill(self, skill_path: Path) -> dict:
        """Basic validation of generated skill.

        Why: Before committing, we check the code is at least syntactically valid.
             Full testing would require pytest, which we skip for simplicity.

        Args:
            skill_path: Path to the skill directory.

        Returns:
            Dict with 'valid' bool and optional 'errors'.
        """
        errors = []

        # Check skill.json exists and is valid
        manifest_path = skill_path / "skill.json"
        if not manifest_path.exists():
            errors.append("skill.json not found")
        else:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                entry_point = manifest.get("entry_point", "skill.py")
            except json.JSONDecodeError:
                errors.append("skill.json is not valid JSON")
                entry_point = "skill.py"

        # Check Python file exists and compiles
        python_path = skill_path / entry_point
        if not python_path.exists():
            errors.append(f"{entry_point} not found")
        else:
            try:
                code = python_path.read_text(encoding="utf-8")
                compile(code, str(python_path), 'exec')
            except SyntaxError as e:
                errors.append(f"Syntax error in {entry_point}: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors if errors else None
        }
