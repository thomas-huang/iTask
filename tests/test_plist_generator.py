"""Tests for plist_generator.py - Plist generation for launchd"""

import tempfile
from pathlib import Path
import pytest
import plistlib
from lib.plist_generator import PlistGenerator
from lib.config import TaskConfig


class TestPlistGenerator:
    """Test suite for PlistGenerator class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def interval_task(self, temp_dir):
        """Create interval-based task config"""
        return TaskConfig(
            name="test_interval",
            script_path=str(temp_dir / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600},
            enabled=True,
            label="com.itask.test_interval"
        )

    @pytest.fixture
    def calendar_task(self, temp_dir):
        """Create calendar-based task config"""
        return TaskConfig(
            name="test_calendar",
            script_path=str(temp_dir / "test.sh"),
            schedule_type="calendar",
            schedule={"Hour": 9, "Minute": 0},
            enabled=True,
            label="com.itask.test_calendar"
        )

    def test_generate_interval_plist(self, interval_task, temp_dir):
        """Test generating plist for interval-based task"""
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        # Parse plist to verify structure
        plist_data = plistlib.loads(plist_content.encode())

        assert plist_data["Label"] == "com.itask.test_interval"
        assert "ProgramArguments" in plist_data
        assert plist_data["ProgramArguments"][0] == interval_task.script_path
        assert plist_data["StartInterval"] == 3600
        assert "StartCalendarInterval" not in plist_data

    def test_generate_calendar_plist(self, calendar_task, temp_dir):
        """Test generating plist for calendar-based task"""
        generator = PlistGenerator()
        plist_content = generator.generate(calendar_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert plist_data["Label"] == "com.itask.test_calendar"
        assert "StartCalendarInterval" in plist_data
        assert plist_data["StartCalendarInterval"]["Hour"] == 9
        assert plist_data["StartCalendarInterval"]["Minute"] == 0
        assert "StartInterval" not in plist_data

    def test_plist_includes_program_arguments(self, interval_task, temp_dir):
        """Test that plist includes program arguments"""
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert "ProgramArguments" in plist_data
        assert isinstance(plist_data["ProgramArguments"], list)
        assert len(plist_data["ProgramArguments"]) >= 1
        assert plist_data["ProgramArguments"][0] == interval_task.script_path

    def test_plist_includes_log_paths(self, interval_task, temp_dir):
        """Test that plist includes stdout and stderr log paths"""
        log_dir = str(temp_dir / "logs")
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=log_dir)

        plist_data = plistlib.loads(plist_content.encode())

        assert "StandardOutPath" in plist_data
        assert "StandardErrorPath" in plist_data
        assert log_dir in plist_data["StandardOutPath"]
        assert log_dir in plist_data["StandardErrorPath"]

    def test_plist_working_directory(self, interval_task, temp_dir):
        """Test that plist includes working directory if specified"""
        interval_task.working_directory = str(temp_dir)
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert "WorkingDirectory" in plist_data
        assert plist_data["WorkingDirectory"] == str(temp_dir)

    def test_plist_environment_variables(self, interval_task, temp_dir):
        """Test that plist includes environment variables if specified"""
        interval_task.environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/Users/test"
        }
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert "EnvironmentVariables" in plist_data
        assert plist_data["EnvironmentVariables"]["PATH"] == "/usr/local/bin:/usr/bin:/bin"
        assert plist_data["EnvironmentVariables"]["HOME"] == "/Users/test"

    def test_plist_keep_alive(self, interval_task, temp_dir):
        """Test that plist includes KeepAlive setting"""
        interval_task.keep_alive = True
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert "KeepAlive" in plist_data
        assert plist_data["KeepAlive"] is True

    def test_plist_run_at_load(self, interval_task, temp_dir):
        """Test that plist includes RunAtLoad setting"""
        interval_task.run_at_load = True
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert "RunAtLoad" in plist_data
        assert plist_data["RunAtLoad"] is True

    def test_save_plist_to_file(self, interval_task, temp_dir):
        """Test saving plist to file"""
        generator = PlistGenerator()
        plist_path = temp_dir / "test.plist"

        generator.save(interval_task, plist_path, log_dir=str(temp_dir / "logs"))

        assert plist_path.exists()

        # Verify file is valid plist
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)

        assert plist_data["Label"] == "com.itask.test_interval"

    def test_generate_invalid_schedule_type(self, interval_task, temp_dir):
        """Test that invalid schedule type raises error"""
        interval_task.schedule_type = "invalid"
        generator = PlistGenerator()

        with pytest.raises(ValueError, match="Invalid schedule_type"):
            generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

    def test_calendar_with_multiple_times(self, temp_dir):
        """Test calendar schedule with multiple time entries"""
        task = TaskConfig(
            name="test_multi",
            script_path=str(temp_dir / "test.sh"),
            schedule_type="calendar",
            schedule=[
                {"Hour": 9, "Minute": 0},
                {"Hour": 17, "Minute": 30}
            ],
            label="com.itask.test_multi"
        )

        generator = PlistGenerator()
        plist_content = generator.generate(task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert "StartCalendarInterval" in plist_data
        assert isinstance(plist_data["StartCalendarInterval"], list)
        assert len(plist_data["StartCalendarInterval"]) == 2
        assert plist_data["StartCalendarInterval"][0]["Hour"] == 9
        assert plist_data["StartCalendarInterval"][1]["Hour"] == 17

    def test_plist_valid_xml(self, interval_task, temp_dir):
        """Test that generated plist is valid XML"""
        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        # Should not raise exception
        plistlib.loads(plist_content.encode())

    def test_custom_log_paths(self, interval_task, temp_dir):
        """Test that custom log paths are used if provided"""
        custom_stdout = str(temp_dir / "custom_out.log")
        custom_stderr = str(temp_dir / "custom_err.log")

        interval_task.log_stdout = custom_stdout
        interval_task.log_stderr = custom_stderr

        generator = PlistGenerator()
        plist_content = generator.generate(interval_task, log_dir=str(temp_dir / "logs"))

        plist_data = plistlib.loads(plist_content.encode())

        assert plist_data["StandardOutPath"] == custom_stdout
        assert plist_data["StandardErrorPath"] == custom_stderr
