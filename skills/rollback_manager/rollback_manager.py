"""Handles rollback operations for data changes.

Why this exists: This skill provides a mechanism to revert changes made to data, enabling users to recover from mistakes efficiently.
"""

import json
import pathlib

class RollbackManager:
    """Skill class matching class_name in skill.json."""

    def run(self, **kwargs) -> dict:
        """Main entry point called by executor.

        Returns:
            Dict with operation results. Include meaningful data.
        """
        try:
            rollback_state = kwargs.get("rollback_state")
            if not rollback_state:
                return {"status": "error", "message": "No rollback state provided."}
            
            result = self._perform_rollback(rollback_state)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _perform_rollback(self, rollback_state: dict) -> dict:
        """Reverts changes based on the provided rollback state.

        Args:
            rollback_state (dict): Dictionary containing the state to rollback to.

        Returns:
            dict: Confirmation of rollback.
        """
        try:
            # Assuming we have a method to save state
            self._save_state(rollback_state)
            return {"message": "Rollback successful", "rollback_to": rollback_state}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _save_state(self, state: dict) -> None:
        """Saves the provided state to a JSON file.

        Args:
            state (dict): The state to be saved.
        """
        try:
            file_path = pathlib.Path("data/rollback_state.json")
            with open(file_path, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            raise RuntimeError(f"Failed to save state: {str(e)}")