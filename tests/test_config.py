"""Tests for config.py - Configuration management"""

import json
import os
import tempfile
from pathlib import Path
import pytest
from lib.config import Config, TaskConfig


class TestConfig:
    """Test suite for Config class"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config(self, temp_config_dir):
        """Create Config instance with temp directory"""
        return Config(config_dir=temp_config_dir)

    def test_init_creates_directory(self, temp_config_dir):
        """Test that initialization creates config directory"""
        config_path = temp_config_dir / "test_config"
        config = Config(config_dir=config_path)
        assert config_path.exists()
        assert (config_path / "scripts").exists()
        assert (config_path / "plists").exists()
        assert (config_path / "logs").exists()

    def test_init_creates_config_file(self, temp_config_dir):
        """Test that initialization creates config.json with default structure"""
        config = Config(config_dir=temp_config_dir)
        config_file = temp_config_dir / "config.json"
        assert config_file.exists()

        with open(config_file) as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert "tasks" in data
        assert isinstance(data["tasks"], dict)

    def test_add_task(self, config, temp_config_dir):
        """Test adding a new task"""
        task_config = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600},
            enabled=True,
            label="com.itask.test_task"
        )

        config.add_task(task_config)

        # Verify task was added
        tasks = config.get_all_tasks()
        assert "test_task" in tasks
        assert tasks["test_task"]["schedule_type"] == "interval"
        assert tasks["test_task"]["schedule"]["seconds"] == 3600

    def test_add_task_duplicate_raises_error(self, config, temp_config_dir):
        """Test that adding duplicate task raises error"""
        task_config = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600}
        )

        config.add_task(task_config)

        with pytest.raises(ValueError, match="Task 'test_task' already exists"):
            config.add_task(task_config)

    def test_get_task(self, config, temp_config_dir):
        """Test getting a specific task"""
        task_config = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600}
        )

        config.add_task(task_config)

        task = config.get_task("test_task")
        assert task is not None
        assert task["script_path"] == str(temp_config_dir / "scripts" / "test.sh")
        assert task["schedule_type"] == "interval"

    def test_get_task_not_found(self, config):
        """Test getting non-existent task returns None"""
        task = config.get_task("nonexistent")
        assert task is None

    def test_remove_task(self, config, temp_config_dir):
        """Test removing a task"""
        task_config = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600}
        )

        config.add_task(task_config)
        assert config.get_task("test_task") is not None

        config.remove_task("test_task")
        assert config.get_task("test_task") is None

    def test_remove_task_not_found(self, config):
        """Test removing non-existent task raises error"""
        with pytest.raises(ValueError, match="Task 'nonexistent' not found"):
            config.remove_task("nonexistent")

    def test_update_task(self, config, temp_config_dir):
        """Test updating task configuration"""
        task_config = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600},
            enabled=True
        )

        config.add_task(task_config)

        # Update task
        config.update_task("test_task", {"enabled": False, "schedule": {"seconds": 7200}})

        task = config.get_task("test_task")
        assert task["enabled"] is False
        assert task["schedule"]["seconds"] == 7200

    def test_get_all_tasks(self, config, temp_config_dir):
        """Test getting all tasks"""
        task1 = TaskConfig(
            name="task1",
            script_path=str(temp_config_dir / "scripts" / "task1.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600}
        )
        task2 = TaskConfig(
            name="task2",
            script_path=str(temp_config_dir / "scripts" / "task2.sh"),
            schedule_type="calendar",
            schedule={"Hour": 9, "Minute": 0}
        )

        config.add_task(task1)
        config.add_task(task2)

        tasks = config.get_all_tasks()
        assert len(tasks) == 2
        assert "task1" in tasks
        assert "task2" in tasks

    def test_task_count(self, config, temp_config_dir):
        """Test getting task count"""
        assert config.task_count() == 0

        task = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600}
        )

        config.add_task(task)
        assert config.task_count() == 1

    def test_atomic_write(self, config, temp_config_dir):
        """Test that config writes are atomic (temp file -> rename)"""
        task = TaskConfig(
            name="test_task",
            script_path=str(temp_config_dir / "scripts" / "test.sh"),
            schedule_type="interval",
            schedule={"seconds": 3600}
        )

        config.add_task(task)

        # Verify no temp files left behind
        temp_files = list(temp_config_dir.glob("*.tmp"))
        assert len(temp_files) == 0

        # Verify config file is valid JSON
        config_file = temp_config_dir / "config.json"
        with open(config_file) as f:
            data = json.load(f)
        assert "test_task" in data["tasks"]


class TestTaskConfig:
    """Test suite for TaskConfig dataclass"""

    def test_task_config_creation(self):
        """Test TaskConfig creation with minimal parameters"""
        task = TaskConfig(
            name="test",
            script_path="/path/to/script.sh",
            schedule_type="interval",
            schedule={"seconds": 3600}
        )

        assert task.name == "test"
        assert task.script_path == "/path/to/script.sh"
        assert task.schedule_type == "interval"
        assert task.enabled is True  # default value
        assert task.label == "com.itask.test"  # auto-generated

    def test_task_config_to_dict(self):
        """Test TaskConfig conversion to dictionary"""
        task = TaskConfig(
            name="test",
            script_path="/path/to/script.sh",
            schedule_type="interval",
            schedule={"seconds": 3600},
            enabled=False
        )

        task_dict = task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict["name"] == "test"
        assert task_dict["enabled"] is False
        assert "created_at" in task_dict
        assert "last_modified" in task_dict

    def test_task_config_custom_label(self):
        """Test TaskConfig with custom label"""
        task = TaskConfig(
            name="test",
            script_path="/path/to/script.sh",
            schedule_type="interval",
            schedule={"seconds": 3600},
            label="com.custom.label"
        )

        assert task.label == "com.custom.label"

    def test_task_config_with_environment(self):
        """Test TaskConfig with environment variables"""
        task = TaskConfig(
            name="test",
            script_path="/path/to/script.sh",
            schedule_type="interval",
            schedule={"seconds": 3600},
            environment={"PATH": "/usr/local/bin:/usr/bin", "HOME": "/Users/test"}
        )

        assert task.environment["PATH"] == "/usr/local/bin:/usr/bin"
        assert task.environment["HOME"] == "/Users/test"
