from datetime import datetime
import time


class TimeSkill:
    """Skill for time and date operations."""

    def run(self, **kwargs) -> dict:
        """Get current time and date information.

        Returns:
            Dict with time, date, timestamp, and timezone info.
        """
        now = datetime.now()
        return {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "day_of_week": now.strftime("%A"),
            "timestamp": int(time.time()),
            "iso": now.isoformat(),
            "formatted": now.strftime("%A, %B %d, %Y at %I:%M %p")
        }

    def get_time(self) -> str:
        """Get just the current time."""
        return datetime.now().strftime("%H:%M:%S")

    def get_date(self) -> str:
        """Get just the current date."""
        return datetime.now().strftime("%Y-%m-%d")
