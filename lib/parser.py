"""Schedule expression parser"""

import re
from typing import Dict, Any, Union, List


class ScheduleParser:
    """Parse human-readable schedule expressions into launchd format"""

    # Weekday mappings
    WEEKDAYS = {
        "sunday": 0, "sun": 0,
        "monday": 1, "mon": 1,
        "tuesday": 2, "tue": 2, "tues": 2,
        "wednesday": 3, "wed": 3,
        "thursday": 4, "thu": 4, "thur": 4, "thurs": 4,
        "friday": 5, "fri": 5,
        "saturday": 6, "sat": 6
    }

    # Interval unit multipliers (to seconds)
    INTERVAL_UNITS = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }

    def parse(self, expression: str) -> Dict[str, Any]:
        """
        Parse schedule expression

        Supported formats:
        - Interval: "every 30s", "every 5m", "every 2h", "every 1d"
        - Calendar: "daily at 09:00", "monday at 10:00", "mon-fri at 18:00"
        - Shortcuts: "hourly", "minutely", "at 09:00"

        Args:
            expression: Schedule expression string

        Returns:
            Dict with "type" and "schedule" keys

        Raises:
            ValueError: If expression format is invalid
        """
        if not expression or not expression.strip():
            raise ValueError("Schedule expression cannot be empty")

        expression = expression.strip().lower()

        # Try shortcuts first
        if expression == "hourly":
            return {"type": "interval", "schedule": {"seconds": 3600}}
        elif expression == "minutely":
            return {"type": "interval", "schedule": {"seconds": 60}}

        # Try interval pattern: "every 30s", "every 5m", etc.
        # First check if it's an interval pattern to give better error messages
        interval_attempt = re.match(r'every\s+(\d+)(\w+)', expression)
        if interval_attempt:
            unit = interval_attempt.group(2)
            if unit not in self.INTERVAL_UNITS:
                raise ValueError(f"Invalid interval unit: {unit}")
            return self._parse_interval(interval_attempt)

        # Try calendar patterns
        # Pattern 1: "daily at HH:MM" or "at HH:MM"
        daily_match = re.match(r'(?:daily\s+)?at\s+(\d{1,2}):(\d{2})(?::(\d{2}))?', expression)
        if daily_match:
            return self._parse_daily(daily_match)

        # Pattern 2: "1st at HH:MM" (day of month) - check before weekday!
        day_match = re.match(r'(\d{1,2})(?:st|nd|rd|th)?\s+at\s+(\d{1,2}):(\d{2})(?::(\d{2}))?', expression)
        if day_match:
            return self._parse_day_of_month(day_match)

        # Pattern 3: "mon-fri at HH:MM" (weekday range)
        weekday_range_match = re.match(r'(\w+)-(\w+)\s+at\s+(\d{1,2}):(\d{2})(?::(\d{2}))?', expression)
        if weekday_range_match:
            return self._parse_weekday_range(weekday_range_match)

        # Pattern 4: "monday at HH:MM"
        weekday_match = re.match(r'(\w+)\s+at\s+(\d{1,2}):(\d{2})(?::(\d{2}))?', expression)
        if weekday_match:
            return self._parse_weekday(weekday_match)

        raise ValueError(f"Invalid schedule format: {expression}")

    def parse_raw(self, raw_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw schedule dictionary

        Args:
            raw_dict: Dictionary with schedule information

        Returns:
            Parsed schedule dict

        Raises:
            ValueError: If schedule type is invalid
        """
        schedule_type = raw_dict.get("type")

        if schedule_type == "interval":
            return {
                "type": "interval",
                "schedule": {"seconds": raw_dict["seconds"]}
            }
        elif schedule_type == "calendar":
            schedule_data = {k: v for k, v in raw_dict.items() if k != "type"}
            return {
                "type": "calendar",
                "schedule": schedule_data
            }
        else:
            raise ValueError(f"Invalid schedule type: {schedule_type}")

    def _parse_interval(self, match) -> Dict[str, Any]:
        """Parse interval expression"""
        value = int(match.group(1))
        unit = match.group(2)

        if unit not in self.INTERVAL_UNITS:
            raise ValueError(f"Invalid interval unit: {unit}")

        seconds = value * self.INTERVAL_UNITS[unit]

        return {
            "type": "interval",
            "schedule": {"seconds": seconds}
        }

    def _parse_daily(self, match) -> Dict[str, Any]:
        """Parse daily calendar expression"""
        hour = int(match.group(1))
        minute = int(match.group(2))

        self._validate_time(hour, minute)

        return {
            "type": "calendar",
            "schedule": {
                "Hour": hour,
                "Minute": minute
            }
        }

    def _parse_weekday(self, match) -> Dict[str, Any]:
        """Parse weekday calendar expression"""
        weekday_str = match.group(1).lower()
        hour = int(match.group(2))
        minute = int(match.group(3))

        self._validate_time(hour, minute)

        if weekday_str not in self.WEEKDAYS:
            raise ValueError(f"Invalid weekday: {weekday_str}")

        weekday = self.WEEKDAYS[weekday_str]

        return {
            "type": "calendar",
            "schedule": {
                "Weekday": weekday,
                "Hour": hour,
                "Minute": minute
            }
        }

    def _parse_weekday_range(self, match) -> Dict[str, Any]:
        """Parse weekday range expression (e.g., mon-fri)"""
        start_day = match.group(1).lower()
        end_day = match.group(2).lower()
        hour = int(match.group(3))
        minute = int(match.group(4))

        self._validate_time(hour, minute)

        if start_day not in self.WEEKDAYS or end_day not in self.WEEKDAYS:
            raise ValueError(f"Invalid weekday range: {start_day}-{end_day}")

        start_num = self.WEEKDAYS[start_day]
        end_num = self.WEEKDAYS[end_day]

        # Generate schedule for each day in range
        schedules = []
        current = start_num
        while True:
            schedules.append({
                "Weekday": current,
                "Hour": hour,
                "Minute": minute
            })
            if current == end_num:
                break
            current = (current + 1) % 7

        return {
            "type": "calendar",
            "schedule": schedules
        }

    def _parse_day_of_month(self, match) -> Dict[str, Any]:
        """Parse day of month expression"""
        day = int(match.group(1))
        hour = int(match.group(2))
        minute = int(match.group(3))

        self._validate_time(hour, minute)

        if not 1 <= day <= 31:
            raise ValueError(f"Invalid day of month: {day}")

        return {
            "type": "calendar",
            "schedule": {
                "Day": day,
                "Hour": hour,
                "Minute": minute
            }
        }

    def _validate_time(self, hour: int, minute: int):
        """Validate time values"""
        if not 0 <= hour <= 23:
            raise ValueError(f"Invalid time format: hour must be 0-23, got {hour}")
        if not 0 <= minute <= 59:
            raise ValueError(f"Invalid time format: minute must be 0-59, got {minute}")
