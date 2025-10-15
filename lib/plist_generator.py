"""Plist generator for launchd tasks"""

import plistlib
from pathlib import Path
from typing import Union
from lib.config import TaskConfig


class PlistGenerator:
    """Generate launchd plist files from task configurations"""

    def generate(self, task: TaskConfig, log_dir: str) -> str:
        """
        Generate plist content for a task

        Args:
            task: TaskConfig object
            log_dir: Directory for log files

        Returns:
            Plist content as string

        Raises:
            ValueError: If schedule_type is invalid
        """
        log_dir_path = Path(log_dir)

        # Build plist structure
        plist_dict = {
            "Label": task.label,
            "ProgramArguments": [task.script_path],
        }

        # Add schedule configuration
        if task.schedule_type == "interval":
            plist_dict["StartInterval"] = task.schedule["seconds"]
        elif task.schedule_type == "calendar":
            plist_dict["StartCalendarInterval"] = task.schedule
        else:
            raise ValueError(f"Invalid schedule_type: {task.schedule_type}")

        # Add working directory if specified
        if task.working_directory:
            plist_dict["WorkingDirectory"] = task.working_directory

        # Add environment variables if specified
        if task.environment:
            plist_dict["EnvironmentVariables"] = task.environment

        # Add log paths
        if task.log_stdout:
            plist_dict["StandardOutPath"] = task.log_stdout
        else:
            plist_dict["StandardOutPath"] = str(log_dir_path / f"{task.name}.log")

        if task.log_stderr:
            plist_dict["StandardErrorPath"] = task.log_stderr
        else:
            plist_dict["StandardErrorPath"] = str(log_dir_path / f"{task.name}.err.log")

        # Add optional settings
        plist_dict["RunAtLoad"] = task.run_at_load
        plist_dict["KeepAlive"] = task.keep_alive

        # Convert to plist XML format
        plist_bytes = plistlib.dumps(plist_dict, fmt=plistlib.FMT_XML)
        return plist_bytes.decode('utf-8')

    def save(self, task: TaskConfig, plist_path: Union[str, Path], log_dir: str):
        """
        Generate and save plist to file

        Args:
            task: TaskConfig object
            plist_path: Path where plist should be saved
            log_dir: Directory for log files
        """
        plist_content = self.generate(task, log_dir)

        plist_path = Path(plist_path)
        plist_path.parent.mkdir(parents=True, exist_ok=True)

        with open(plist_path, 'w') as f:
            f.write(plist_content)
