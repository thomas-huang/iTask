"""Configuration management for itask"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class TaskConfig:
    """Configuration for a single task"""

    name: str
    script_path: str
    schedule_type: str  # "interval" or "calendar"
    schedule: Dict[str, Any]
    enabled: bool = True
    label: str = ""
    working_directory: Optional[str] = None
    environment: Optional[Dict[str, str]] = None
    log_stdout: Optional[str] = None
    log_stderr: Optional[str] = None
    keep_alive: bool = False
    run_at_load: bool = False
    script_copied: bool = True  # Whether script was copied to ~/.itask/scripts/
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Post-initialization processing"""
        # Auto-generate label if not provided
        if not self.label:
            self.label = f"com.itask.{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskConfig to dictionary"""
        return asdict(self)


class Config:
    """Configuration manager for itask"""

    DEFAULT_CONFIG_DIR = Path.home() / ".itask"
    CONFIG_VERSION = "1.0"

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Optional custom config directory (for testing)
        """
        self.config_dir = Path(config_dir) if config_dir else self.DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / "config.json"
        self.scripts_dir = self.config_dir / "scripts"
        self.plists_dir = self.config_dir / "plists"
        self.logs_dir = self.config_dir / "logs"

        self._ensure_directories()
        self._ensure_config_file()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(exist_ok=True)
        self.plists_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    def _ensure_config_file(self):
        """Create default config file if it doesn't exist"""
        if not self.config_file.exists():
            default_config = {
                "version": self.CONFIG_VERSION,
                "tasks": {}
            }
            self._write_config(default_config)

    def _read_config(self) -> Dict[str, Any]:
        """Read configuration from file"""
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def _write_config(self, config: Dict[str, Any]):
        """
        Write configuration to file atomically

        Uses temp file + rename for atomic writes
        """
        temp_file = self.config_file.with_suffix('.json.tmp')

        try:
            # Write to temp file
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)

            # Atomic rename
            temp_file.replace(self.config_file)
        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def add_task(self, task_config: TaskConfig):
        """
        Add a new task

        Args:
            task_config: TaskConfig object

        Raises:
            ValueError: If task already exists
        """
        config = self._read_config()

        if task_config.name in config["tasks"]:
            raise ValueError(f"Task '{task_config.name}' already exists")

        config["tasks"][task_config.name] = task_config.to_dict()
        self._write_config(config)

    def get_task(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get task configuration by name

        Args:
            name: Task name

        Returns:
            Task configuration dict or None if not found
        """
        config = self._read_config()
        return config["tasks"].get(name)

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks

        Returns:
            Dictionary of all tasks
        """
        config = self._read_config()
        return config["tasks"]

    def remove_task(self, name: str):
        """
        Remove a task

        Args:
            name: Task name

        Raises:
            ValueError: If task not found
        """
        config = self._read_config()

        if name not in config["tasks"]:
            raise ValueError(f"Task '{name}' not found")

        del config["tasks"][name]
        self._write_config(config)

    def update_task(self, name: str, updates: Dict[str, Any]):
        """
        Update task configuration

        Args:
            name: Task name
            updates: Dictionary of fields to update

        Raises:
            ValueError: If task not found
        """
        config = self._read_config()

        if name not in config["tasks"]:
            raise ValueError(f"Task '{name}' not found")

        # Update last_modified timestamp
        updates["last_modified"] = datetime.now().isoformat()

        # Merge updates
        config["tasks"][name].update(updates)
        self._write_config(config)

    def task_count(self) -> int:
        """
        Get number of tasks

        Returns:
            Number of tasks
        """
        config = self._read_config()
        return len(config["tasks"])

    def task_exists(self, name: str) -> bool:
        """
        Check if task exists

        Args:
            name: Task name

        Returns:
            True if task exists, False otherwise
        """
        config = self._read_config()
        return name in config["tasks"]
