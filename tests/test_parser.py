"""Tests for parser.py - Schedule expression parser"""

import pytest
from lib.parser import ScheduleParser


class TestScheduleParser:
    """Test suite for ScheduleParser class"""

    @pytest.fixture
    def parser(self):
        """Create ScheduleParser instance"""
        return ScheduleParser()

    # Interval parsing tests
    def test_parse_interval_seconds(self, parser):
        """Test parsing interval in seconds"""
        result = parser.parse("every 30s")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 30

    def test_parse_interval_minutes(self, parser):
        """Test parsing interval in minutes"""
        result = parser.parse("every 5m")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 300  # 5 * 60

    def test_parse_interval_hours(self, parser):
        """Test parsing interval in hours"""
        result = parser.parse("every 2h")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 7200  # 2 * 60 * 60

    def test_parse_interval_days(self, parser):
        """Test parsing interval in days"""
        result = parser.parse("every 1d")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 86400  # 24 * 60 * 60

    def test_parse_interval_case_insensitive(self, parser):
        """Test that interval parsing is case insensitive"""
        result = parser.parse("EVERY 10M")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 600

    # Calendar parsing tests
    def test_parse_calendar_daily(self, parser):
        """Test parsing daily at specific time"""
        result = parser.parse("daily at 09:00")
        assert result["type"] == "calendar"
        assert result["schedule"]["Hour"] == 9
        assert result["schedule"]["Minute"] == 0

    def test_parse_calendar_daily_with_seconds(self, parser):
        """Test parsing daily time with seconds"""
        result = parser.parse("daily at 09:30:45")
        assert result["type"] == "calendar"
        assert result["schedule"]["Hour"] == 9
        assert result["schedule"]["Minute"] == 30

    def test_parse_calendar_weekday(self, parser):
        """Test parsing specific weekday"""
        result = parser.parse("monday at 10:00")
        assert result["type"] == "calendar"
        assert result["schedule"]["Weekday"] == 1  # Monday
        assert result["schedule"]["Hour"] == 10
        assert result["schedule"]["Minute"] == 0

    def test_parse_calendar_weekday_short(self, parser):
        """Test parsing weekday with short name"""
        result = parser.parse("mon at 10:00")
        assert result["type"] == "calendar"
        assert result["schedule"]["Weekday"] == 1

    def test_parse_calendar_all_weekdays(self, parser):
        """Test parsing all weekdays"""
        weekdays = {
            "monday": 1, "tuesday": 2, "wednesday": 3,
            "thursday": 4, "friday": 5, "saturday": 6, "sunday": 0
        }

        for day_name, day_num in weekdays.items():
            result = parser.parse(f"{day_name} at 10:00")
            assert result["schedule"]["Weekday"] == day_num

    def test_parse_calendar_weekday_range(self, parser):
        """Test parsing weekday range (mon-fri)"""
        result = parser.parse("mon-fri at 18:00")
        assert result["type"] == "calendar"
        assert isinstance(result["schedule"], list)
        assert len(result["schedule"]) == 5

        # Verify Monday through Friday
        for i, schedule_item in enumerate(result["schedule"]):
            assert schedule_item["Weekday"] == i + 1  # 1=Mon, 2=Tue, ..., 5=Fri
            assert schedule_item["Hour"] == 18
            assert schedule_item["Minute"] == 0

    def test_parse_calendar_with_day_of_month(self, parser):
        """Test parsing with specific day of month"""
        result = parser.parse("1st at 00:00")
        assert result["type"] == "calendar"
        assert result["schedule"]["Day"] == 1
        assert result["schedule"]["Hour"] == 0
        assert result["schedule"]["Minute"] == 0

    # Error handling tests
    def test_parse_invalid_format(self, parser):
        """Test that invalid format raises error"""
        with pytest.raises(ValueError, match="Invalid schedule format"):
            parser.parse("invalid schedule")

    def test_parse_invalid_interval_unit(self, parser):
        """Test that invalid interval unit raises error"""
        with pytest.raises(ValueError, match="Invalid interval unit"):
            parser.parse("every 10x")

    def test_parse_invalid_time_format(self, parser):
        """Test that invalid time format raises error"""
        with pytest.raises(ValueError, match="Invalid time format"):
            parser.parse("daily at 25:00")

    def test_parse_invalid_weekday(self, parser):
        """Test that invalid weekday raises error"""
        with pytest.raises(ValueError, match="Invalid weekday"):
            parser.parse("invalidday at 10:00")

    # Edge cases
    def test_parse_empty_string(self, parser):
        """Test that empty string raises error"""
        with pytest.raises(ValueError):
            parser.parse("")

    def test_parse_whitespace_variations(self, parser):
        """Test parsing with various whitespace"""
        result1 = parser.parse("every   5m")
        result2 = parser.parse("every 5m")
        assert result1 == result2

    def test_parse_interval_with_large_number(self, parser):
        """Test parsing interval with large number"""
        result = parser.parse("every 1000h")
        assert result["schedule"]["seconds"] == 3600000

    # Raw schedule dict tests
    def test_parse_raw_interval_dict(self, parser):
        """Test parsing raw interval dictionary"""
        raw = {"type": "interval", "seconds": 3600}
        result = parser.parse_raw(raw)
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 3600

    def test_parse_raw_calendar_dict(self, parser):
        """Test parsing raw calendar dictionary"""
        raw = {"type": "calendar", "Hour": 9, "Minute": 0}
        result = parser.parse_raw(raw)
        assert result["type"] == "calendar"
        assert result["schedule"]["Hour"] == 9
        assert result["schedule"]["Minute"] == 0

    def test_parse_raw_invalid_type(self, parser):
        """Test that invalid type in raw dict raises error"""
        with pytest.raises(ValueError, match="Invalid schedule type"):
            parser.parse_raw({"type": "invalid"})

    # Alternative formats
    def test_parse_at_notation(self, parser):
        """Test alternative 'at' notation"""
        result = parser.parse("at 09:00")
        assert result["type"] == "calendar"
        assert result["schedule"]["Hour"] == 9

    def test_parse_hourly(self, parser):
        """Test 'hourly' shortcut"""
        result = parser.parse("hourly")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 3600

    def test_parse_minutely(self, parser):
        """Test 'minutely' shortcut"""
        result = parser.parse("minutely")
        assert result["type"] == "interval"
        assert result["schedule"]["seconds"] == 60
