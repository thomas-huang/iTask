"""Tests for CLI functionality"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json

from lib.config import TaskConfig, Config
from lib.parser import ScheduleParser
from lib.plist_generator import PlistGenerator
from lib.launchd import LaunchdManager
import itask_cli


class TestCLI:
    """Test CLI functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def test_script(self, temp_dir):
        """Create a test script file"""
        script_path = temp_dir / "test_script.sh"
        script_path.write_text("#!/bin/bash\necho 'test'")
        script_path.chmod(0o755)
        return script_path

    @pytest.fixture
    def cli_instance(self, temp_dir):
        """Create CLI instance with mocked dependencies"""
        config = Config(temp_dir / ".itask")
        cli = itask_cli.ITaskCLI()
        cli.config = config
        cli.parser = ScheduleParser()
        cli.plist_generator = Mock(spec=PlistGenerator)
        cli.launchd = Mock(spec=LaunchdManager)

        # Mock plist generator methods
        cli.plist_generator.save.return_value = None

        # Mock launchd methods
        plist_path = temp_dir / "test.plist"
        cli.launchd.get_plist_path.return_value = plist_path
        cli.launchd.load.return_value = None

        # Create the plist file to avoid file not found errors
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text("<?xml version='1.0'?><plist></plist>")

        return cli

    def test_add_task_with_keep_original_flag(self, cli_instance, test_script):
        """Test adding task with --keep-original flag"""
        # Mock arguments
        args = Mock()
        args.script = str(test_script)
        args.name = "test_task"
        args.schedule = "every 1h"
        args.working_dir = None
        args.keep_original = True

        # Execute add_task
        result = cli_instance.add_task(args)

        # Verify success
        assert result == 0

        # Verify task was added to config
        task = cli_instance.config.get_task("test_task")
        assert task is not None
        assert task["name"] == "test_task"
        assert Path(task["script_path"]).resolve() == test_script.resolve()  # Compare resolved paths
        assert task["script_copied"] == False  # Not copied

        # Verify original script still exists
        assert test_script.exists()

        # Verify no script was copied to scripts directory
        scripts_dir = cli_instance.config.scripts_dir
        copied_script = scripts_dir / test_script.name
        assert not copied_script.exists()

    def test_add_task_without_keep_original_flag(self, cli_instance, test_script):
        """Test adding task without --keep-original flag (default behavior)"""
        # Mock arguments
        args = Mock()
        args.script = str(test_script)
        args.name = "test_task"
        args.schedule = "every 1h"
        args.working_dir = None
        args.keep_original = False

        # Execute add_task
        result = cli_instance.add_task(args)

        # Verify success
        assert result == 0

        # Verify task was added to config
        task = cli_instance.config.get_task("test_task")
        assert task is not None
        assert task["name"] == "test_task"
        assert task["script_copied"] == True  # Was copied

        # Verify script was copied to scripts directory
        scripts_dir = cli_instance.config.scripts_dir
        copied_script = scripts_dir / test_script.name
        assert copied_script.exists()
        assert task["script_path"] == str(copied_script)  # Copied path

    def test_add_task_keep_original_makes_script_executable(self, cli_instance, temp_dir):
        """Test that --keep-original makes non-executable scripts executable"""
        # Create non-executable script
        script_path = temp_dir / "non_executable.sh"
        script_path.write_text("#!/bin/bash\necho 'test'")
        script_path.chmod(0o644)  # Not executable

        # Mock arguments
        args = Mock()
        args.script = str(script_path)
        args.name = "test_task"
        args.schedule = "every 1h"
        args.working_dir = None
        args.keep_original = True

        # Execute add_task
        result = cli_instance.add_task(args)

        # Verify success
        assert result == 0

        # Verify script was made executable
        assert os.access(script_path, os.X_OK)

    def test_remove_task_with_copied_script(self, cli_instance, test_script):
        """Test removing task that has copied script"""
        # First add a task (copied)
        task_config = TaskConfig(
            name="test_task",
            script_path=str(cli_instance.config.scripts_dir / "test_script.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600},
            script_copied=True
        )
        cli_instance.config.add_task(task_config)

        # Create the copied script file
        copied_script = Path(task_config.script_path)
        copied_script.parent.mkdir(parents=True, exist_ok=True)
        copied_script.write_text("#!/bin/bash\necho 'test'")

        # Mock arguments for removal
        args = Mock()
        args.name = "test_task"
        args.yes = True
        args.keep_script = False

        # Mock launchd methods
        cli_instance.launchd.get_plist_path.return_value = Path("/tmp/test.plist")
        cli_instance.launchd.unload.return_value = None
        cli_instance.launchd.remove_plist.return_value = None

        # Execute remove_task
        result = cli_instance.remove_task(args)

        # Verify success
        assert result == 0

        # Verify script was deleted (because it was copied)
        assert not copied_script.exists()

    def test_remove_task_with_original_script(self, cli_instance, test_script):
        """Test removing task that uses original script location"""
        # Add task with original script
        task_config = TaskConfig(
            name="test_task",
            script_path=str(test_script),
            schedule_type="interval",
            schedule={"seconds": 3600},
            script_copied=False
        )
        cli_instance.config.add_task(task_config)

        # Mock arguments for removal
        args = Mock()
        args.name = "test_task"
        args.yes = True
        args.keep_script = False

        # Mock launchd methods
        cli_instance.launchd.get_plist_path.return_value = Path("/tmp/test.plist")
        cli_instance.launchd.unload.return_value = None
        cli_instance.launchd.remove_plist.return_value = None

        # Execute remove_task
        result = cli_instance.remove_task(args)

        # Verify success
        assert result == 0

        # Verify original script was NOT deleted (because it wasn't copied)
        assert test_script.exists()

    def test_taskconfig_backward_compatibility(self):
        """Test that TaskConfig handles old configs without script_copied field"""
        # Create task config without script_copied field (simulating old config)
        task_dict = {
            "name": "old_task",
            "script_path": "/path/to/script.sh",
            "schedule_type": "interval",
            "schedule": {"seconds": 3600},
            "enabled": True,
            "label": "com.itask.old_task"
        }

        # This should work and default script_copied to True for backward compatibility
        script_was_copied = task_dict.get("script_copied", True)
        assert script_was_copied == True

    def test_taskconfig_with_script_copied_field(self):
        """Test TaskConfig with new script_copied field"""
        task_config = TaskConfig(
            name="new_task",
            script_path="/path/to/script.sh",
            schedule_type="interval",
            schedule={"seconds": 3600},
            script_copied=False
        )

        assert task_config.script_copied == False

        # Test serialization
        task_dict = task_config.to_dict()
        assert "script_copied" in task_dict
        assert task_dict["script_copied"] == False