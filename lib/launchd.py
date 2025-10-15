"""Launchd operations manager"""

import subprocess
from pathlib import Path
from typing import List, Optional


class LaunchdManager:
    """Manager for launchd operations (load, unload, start, stop, etc.)"""

    DEFAULT_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"

    def __init__(self, launch_agents_dir: Optional[Path] = None):
        """
        Initialize LaunchdManager

        Args:
            launch_agents_dir: Optional custom LaunchAgents directory (for testing)
        """
        self.launch_agents_dir = launch_agents_dir or self.DEFAULT_LAUNCH_AGENTS_DIR
        self.launch_agents_dir.mkdir(parents=True, exist_ok=True)

    def load(self, plist_path: str):
        """
        Load a plist file into launchd

        Args:
            plist_path: Path to plist file

        Raises:
            RuntimeError: If load fails
        """
        result = subprocess.run(
            ['launchctl', 'load', plist_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to load {plist_path}: {result.stderr}")

    def unload(self, plist_path: str):
        """
        Unload a plist file from launchd

        Args:
            plist_path: Path to plist file

        Note: Does not raise error if plist is not loaded
        """
        result = subprocess.run(
            ['launchctl', 'unload', plist_path],
            capture_output=True,
            text=True
        )

        # Ignore "Could not find specified service" errors
        if result.returncode != 0 and "Could not find" not in result.stderr:
            raise RuntimeError(f"Failed to unload {plist_path}: {result.stderr}")

    def is_loaded(self, label: str) -> bool:
        """
        Check if a service is loaded

        Args:
            label: Service label (e.g., com.itask.taskname)

        Returns:
            True if loaded, False otherwise
        """
        result = subprocess.run(
            ['launchctl', 'list', label],
            capture_output=True,
            text=True
        )

        return result.returncode == 0

    def start(self, label: str):
        """
        Start a service

        Args:
            label: Service label

        Raises:
            RuntimeError: If start fails
        """
        result = subprocess.run(
            ['launchctl', 'start', label],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start {label}: {result.stderr}")

    def stop(self, label: str):
        """
        Stop a service

        Args:
            label: Service label

        Raises:
            RuntimeError: If stop fails
        """
        result = subprocess.run(
            ['launchctl', 'stop', label],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to stop {label}: {result.stderr}")

    def list_loaded(self, filter_itask: bool = False) -> List[str]:
        """
        List loaded services

        Args:
            filter_itask: If True, only return itask services

        Returns:
            List of service labels
        """
        result = subprocess.run(
            ['launchctl', 'list'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return []

        services = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                label = parts[2]
                if not filter_itask or 'itask' in label:
                    services.append(label)

        return services

    def get_plist_path(self, label: str) -> Path:
        """
        Get plist file path for a label

        Args:
            label: Service label

        Returns:
            Path to plist file
        """
        return self.launch_agents_dir / f"{label}.plist"

    def plist_exists(self, label: str) -> bool:
        """
        Check if plist file exists

        Args:
            label: Service label

        Returns:
            True if plist exists, False otherwise
        """
        return self.get_plist_path(label).exists()

    def remove_plist(self, label: str):
        """
        Remove plist file

        Args:
            label: Service label

        Note: Does not raise error if plist doesn't exist
        """
        plist_path = self.get_plist_path(label)
        if plist_path.exists():
            plist_path.unlink()

    def reload(self, plist_path: str):
        """
        Reload a service (unload + load)

        Args:
            plist_path: Path to plist file

        Raises:
            RuntimeError: If reload fails
        """
        self.unload(plist_path)
        self.load(plist_path)
