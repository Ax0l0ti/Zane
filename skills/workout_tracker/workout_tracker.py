"""Skill to track gym workouts, query records, and retrieve logged data.

Why this exists: This skill helps users log exercises, sets, reps, and weight,
query personal bests, and retrieve logged workout data, facilitating
efficient fitness tracking and motivation.
"""

import json
import re
from pathlib import Path
from datetime import datetime

class WorkoutTracker:
    """Skill class matching class_name in skill.json."""

    def __init__(self):
        """Initialize with a file to store workout data."""
        self.data_file = Path(__file__).parent / "workout_data.json"
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Ensure the data file exists and is initialized."""
        if not self.data_file.exists():
            self.data_file.write_text(json.dumps({"workouts": []}))

    def run(self, user_message: str = "", **kwargs) -> dict:
        """Main entry point called by executor.

        Args:
            user_message: The user's natural language request.
            kwargs: Additional parameters if provided directly.

        Returns:
            Dict with operation results, including meaningful data.
        """
        try:
            msg = user_message.lower()

            if any(word in msg for word in ["log", "record", "did", "completed"]):
                return self._parse_and_log(user_message)
            elif any(word in msg for word in ["pr", "last", "best", "max", "query"]):
                return self._parse_and_query(user_message)
            elif any(word in msg for word in ["retrieve", "get", "show workouts"]):
                return self._retrieve_logged_workouts()
            else:
                return {"status": "error", "message": "No key words detected, no function activated"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _parse_and_log(self, message: str) -> dict:
        """Parse a log request and record the workout."""
        msg = message.lower()
        numbers = re.findall(r'(\d+(?:\.\d+)?)', message)

        exercises = ["bench press", "squat", "deadlift", "overhead press",
                     "barbell row", "pull up", "push up", "curl", "tricep"]
        exercise = None
        for ex in exercises:
            if ex in msg:
                exercise = ex
                break

        if not exercise:
            match = re.search(r'(?:log|workout|did|record)?[:\s]*([a-z\s]+?)(?:\d|,|$)', msg)
            if match:
                exercise = match.group(1).strip().strip(',')

        if not exercise:
            exercise = "unknown exercise"

        sets, reps, weight = 1, 1, 0
        if len(numbers) >= 3:
            sets, reps, weight = int(numbers[0]), int(numbers[1]), float(numbers[2])
        elif len(numbers) == 2:
            reps, weight = int(numbers[0]), float(numbers[1])
        elif len(numbers) == 1:
            weight = float(numbers[0])

        return self._log_workout(exercise, sets, reps, weight)

    def _parse_and_query(self, message: str) -> dict:
        """Parse a query request and return records."""
        msg = message.lower()
        exercises = ["bench press", "squat", "deadlift", "overhead press",
                     "barbell row", "pull up", "push up", "curl", "tricep"]

        for ex in exercises:
            if ex in msg:
                return self._query_records(ex)

        return {"status": "error", "message": "Could not determine which exercise to query"}

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

        date_str = datetime.now().strftime("%Y-%m-%d")
        workout_entry = {"date": date_str, "exercise": exercise, "sets": sets, "reps": reps, "weight": weight}
        try:
            data = json.loads(self.data_file.read_text())
            data["workouts"].append(workout_entry)
            self.data_file.write_text(json.dumps(data, indent= 1))
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
                (entry['date'], entry['sets'], entry['reps'], entry['weight'])
                for entry in data["workouts"]
                if entry['exercise'] == exercise
            ]
            if not personal_records:
                return {"status": "error", "message": "No records found for this exercise"}
            record = max(personal_records, key=lambda x: x[3])  # highest weight
            return {"status": "success", "record": record}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _retrieve_logged_workouts(self) -> dict:
        """Retrieve all logged workouts, grouped by date.

        Returns:
            Dict containing all logged workouts organized by date.
        """
        try:
            data = json.loads(self.data_file.read_text())
            workouts_by_date = {}
            for entry in data["workouts"]:
                date = entry['date']
                if date not in workouts_by_date:
                    workouts_by_date[date] = []
                workouts_by_date[date].append(entry)
            return {"status": "success", "data": workouts_by_date}
        except Exception as e:
            return {"status": "error", "message": str(e)}