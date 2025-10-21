#!/usr/bin/env python3
"""
itask - macOS launchd task manager CLI

A simple CLI tool to manage launchd tasks on macOS
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from lib.config import Config, TaskConfig
from lib.parser import ScheduleParser
from lib.plist_generator import PlistGenerator
from lib.launchd import LaunchdManager


class ITaskCLI:
    """Main CLI application"""

    def __init__(self):
        self.config = Config()
        self.parser = ScheduleParser()
        self.plist_generator = PlistGenerator()
        self.launchd = LaunchdManager()

    def add_task(self, args):
        """Add a new task"""
        script_path = Path(args.script).expanduser().resolve()

        # Validate script exists
        if not script_path.exists():
            print(f"Error: Script not found: {script_path}")
            return 1

        # Determine task name
        task_name = args.name or script_path.stem

        # Check if task already exists
        if self.config.task_exists(task_name):
            print(f"Error: Task '{task_name}' already exists")
            return 1

        # Parse schedule
        try:
            if args.schedule:
                schedule_info = self.parser.parse(args.schedule)
            else:
                # Interactive mode
                print("No schedule specified. Please enter schedule:")
                print("Examples: 'every 1h', 'daily at 09:00', 'monday at 10:00'")
                schedule_str = input("Schedule: ")
                schedule_info = self.parser.parse(schedule_str)
        except ValueError as e:
            print(f"Error: {e}")
            return 1

        # Handle script path based on --keep-original option
        if args.keep_original:
            # Use original script path, ensure it's executable
            if not os.access(script_path, os.X_OK):
                print(f"Warning: Script is not executable: {script_path}")
                try:
                    script_path.chmod(script_path.stat().st_mode | 0o755)
                    print(f"Made script executable: {script_path}")
                except Exception as e:
                    print(f"Error: Cannot make script executable: {e}")
                    return 1

            final_script_path = str(script_path)
            script_copied = False
        else:
            # Copy script to itask scripts directory (current behavior)
            dest_script = self.config.scripts_dir / script_path.name
            try:
                shutil.copy2(script_path, dest_script)
                dest_script.chmod(0o755)  # Make executable
            except Exception as e:
                print(f"Error copying script: {e}")
                return 1

            final_script_path = str(dest_script)
            script_copied = True

        # Create task configuration
        task_config = TaskConfig(
            name=task_name,
            script_path=final_script_path,
            schedule_type=schedule_info["type"],
            schedule=schedule_info["schedule"],
            enabled=True,
            working_directory=args.working_dir or str(Path.cwd()),
            log_stdout=str(self.config.logs_dir / f"{task_name}.log"),
            log_stderr=str(self.config.logs_dir / f"{task_name}.err.log"),
            script_copied=script_copied
        )

        # Generate and save plist
        try:
            plist_path = self.launchd.get_plist_path(task_config.label)
            self.plist_generator.save(task_config, plist_path, str(self.config.logs_dir))

            # Backup plist to itask plists directory
            backup_plist_path = self.config.plists_dir / f"{task_config.label}.plist"
            shutil.copy2(plist_path, backup_plist_path)
        except Exception as e:
            print(f"Error generating plist: {e}")
            # Cleanup copied script only if we copied it
            if script_copied:
                Path(final_script_path).unlink()
            return 1

        # Load into launchd
        try:
            self.launchd.load(str(plist_path))
        except RuntimeError as e:
            print(f"Error loading task: {e}")
            # Cleanup
            if script_copied:
                Path(final_script_path).unlink()
            plist_path.unlink()
            return 1

        # Save to config
        try:
            self.config.add_task(task_config)
        except Exception as e:
            print(f"Error saving config: {e}")
            # Cleanup
            self.launchd.unload(str(plist_path))
            if script_copied:
                Path(final_script_path).unlink()
            plist_path.unlink()
            return 1

        print(f"✓ Task '{task_name}' added and loaded successfully")
        print(f"  Schedule: {args.schedule or schedule_str}")
        print(f"  Script: {final_script_path}")
        print(f"  Logs: {self.config.logs_dir / task_name}.{{log,err.log}}")
        return 0

    def remove_task(self, args):
        """Remove a task"""
        task_name = args.name

        # Check if task exists
        task = self.config.get_task(task_name)
        if not task:
            print(f"Error: Task '{task_name}' not found")
            return 1

        # Confirm removal
        if not args.yes:
            response = input(f"Remove task '{task_name}'? [y/N] ")
            if response.lower() != 'y':
                print("Cancelled")
                return 0

        label = task["label"]

        # Unload from launchd
        try:
            plist_path = self.launchd.get_plist_path(label)
            self.launchd.unload(str(plist_path))
        except Exception as e:
            print(f"Warning: Failed to unload task: {e}")

        # Remove plist
        self.launchd.remove_plist(label)

        # Remove backup plist
        backup_plist = self.config.plists_dir / f"{label}.plist"
        if backup_plist.exists():
            backup_plist.unlink()

        # Remove script (only if it was copied and --keep-script not specified)
        script_was_copied = task.get("script_copied", True)  # Default to True for backward compatibility
        if script_was_copied and not args.keep_script:
            script_path = Path(task["script_path"])
            if script_path.exists():
                script_path.unlink()
        elif not script_was_copied and not args.keep_script:
            print(f"Note: Script was not copied to ~/.itask/scripts/, leaving original at {task['script_path']}")

        # Remove from config
        self.config.remove_task(task_name)

        print(f"✓ Task '{task_name}' removed")
        return 0

    def list_tasks(self, args):
        """List all tasks"""
        tasks = self.config.get_all_tasks()

        if not tasks:
            print("No tasks configured")
            return 0

        print(f"{'NAME':<20} {'SCHEDULE':<30} {'STATUS':<10}")
        print("-" * 60)

        for name, task in tasks.items():
            # Format schedule
            if task["schedule_type"] == "interval":
                seconds = task["schedule"]["seconds"]
                if seconds >= 86400:
                    schedule = f"every {seconds // 86400}d"
                elif seconds >= 3600:
                    schedule = f"every {seconds // 3600}h"
                elif seconds >= 60:
                    schedule = f"every {seconds // 60}m"
                else:
                    schedule = f"every {seconds}s"
            else:
                sched = task["schedule"]
                if isinstance(sched, list):
                    schedule = f"multiple times"
                elif "Weekday" in sched:
                    days = {0: "sun", 1: "mon", 2: "tue", 3: "wed", 4: "thu", 5: "fri", 6: "sat"}
                    day = days.get(sched["Weekday"], "?")
                    schedule = f"{day} at {sched['Hour']:02d}:{sched['Minute']:02d}"
                elif "Day" in sched:
                    schedule = f"day {sched['Day']} at {sched['Hour']:02d}:{sched['Minute']:02d}"
                else:
                    schedule = f"daily at {sched['Hour']:02d}:{sched['Minute']:02d}"

            # Check if loaded
            status = "loaded" if self.launchd.is_loaded(task["label"]) else "not loaded"
            if not task.get("enabled", True):
                status = "disabled"

            print(f"{name:<20} {schedule:<30} {status:<10}")

        if args.verbose:
            print(f"\nTotal: {len(tasks)} tasks")

        return 0

    def show_task(self, args):
        """Show task details"""
        task = self.config.get_task(args.name)

        if not task:
            print(f"Error: Task '{args.name}' not found")
            return 1

        print(f"Task: {args.name}")
        print(f"Label: {task['label']}")
        print(f"Script: {task['script_path']}")
        print(f"Schedule Type: {task['schedule_type']}")
        print(f"Schedule: {task['schedule']}")
        print(f"Enabled: {task.get('enabled', True)}")
        print(f"Working Directory: {task.get('working_directory', 'N/A')}")
        print(f"Stdout Log: {task.get('log_stdout', 'N/A')}")
        print(f"Stderr Log: {task.get('log_stderr', 'N/A')}")
        print(f"Created: {task.get('created_at', 'N/A')}")
        print(f"Last Modified: {task.get('last_modified', 'N/A')}")

        # Check if loaded
        is_loaded = self.launchd.is_loaded(task["label"])
        print(f"Status: {'Loaded' if is_loaded else 'Not loaded'}")

        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='itask - macOS launchd task manager',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new task')
    add_parser.add_argument('script', help='Path to script file')
    add_parser.add_argument('--name', help='Task name (default: script filename)')
    add_parser.add_argument('--schedule', help='Schedule expression (e.g., "every 1h", "daily at 09:00")')
    add_parser.add_argument('--working-dir', help='Working directory for script')
    add_parser.add_argument('--keep-original', action='store_true',
                           help='Keep script in original location instead of copying to ~/.itask/scripts/')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a task')
    remove_parser.add_argument('name', help='Task name')
    remove_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    remove_parser.add_argument('--keep-script', action='store_true', help='Keep script file')

    # List command
    list_parser = subparsers.add_parser('list', help='List all tasks')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show task details')
    show_parser.add_argument('name', help='Task name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    cli = ITaskCLI()

    # Route to appropriate handler
    if args.command == 'add':
        return cli.add_task(args)
    elif args.command == 'remove':
        return cli.remove_task(args)
    elif args.command == 'list':
        return cli.list_tasks(args)
    elif args.command == 'show':
        return cli.show_task(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
