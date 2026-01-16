"""Skill to track gym workouts.

Why this exists: This skill helps users log exercises, sets, reps, and weight; and query their personal bests, aiding in fitness tracking and motivation.
"""

import json
from pathlib import Path

class WorkoutTracker:
    """Skill class matching class_name in skill.json."""
    
    def __init__(self, data_file: str = 'workout_data.json'):
        """Initialize with a file to store workout data."""
        self.data_file = Path(data_file)
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Ensure the data file exists and is initialized."""
        if not self.data_file.exists():
            self.data_file.write_text(json.dumps({"workouts": []}))

    def run(self, action: str, **kwargs) -> dict:
        """Main entry point called by executor.

        Args:
            action (str): The action to perform ('log' or 'query').
            kwargs: Additional parameters based on the action.

        Returns:
            Dict with operation results, including meaningful data.
        """
        try:
            if action == "log":
                return self._log_workout(**kwargs)
            elif action == "query":
                return self._query_records(**kwargs)
            else:
                return {"status": "error", "message": "Invalid action"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _log_workout(self, exercise: str, sets: int, reps: int, weight: float) -> dict:
        """Log a workout entry to the data file.

        Args:
            exercise (str): The name of the exercise.
            sets (int): The number of sets.
            reps (int): The number of reps per set.
            weight (float): The weight used for the exercise.

        Returns:
            Dict with the result of the logging.
        """
        if not isinstance(sets, int) or not isinstance(reps, int) or not isinstance(weight, (int, float)):
            return {"status": "error", "message": "Invalid input types"}

        workout_entry = {"exercise": exercise, "sets": sets, "reps": reps, "weight": weight}
        try:
            data = json.loads(self.data_file.read_text())
            data["workouts"].append(workout_entry)
            self.data_file.write_text(json.dumps(data))
            return {"status": "success", "data": workout_entry}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _query_records(self, exercise: str) -> dict:
        """Query personal records for a specific exercise.

        Args:
            exercise (str): The name of the exercise to query.

        Returns:
            Dict with the personal records for the exercise.
        """
        try:
            data = json.loads(self.data_file.read_text())
            personal_records = [
                (entry['sets'], entry['reps'], entry['weight'])
                for entry in data["workouts"]
                if entry['exercise'] == exercise
            ]
            if not personal_records:
                return {"status": "error", "message": "No records found for this exercise"}
            record = max(personal_records, key=lambda x: x[2])  # highest weight
            return {"status": "success", "record": record}
        except Exception as e:
            return {"status": "error", "message": str(e)}