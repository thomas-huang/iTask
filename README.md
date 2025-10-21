# itask

A simple, elegant CLI tool for managing macOS launchd tasks.

Built with **TDD (Test-Driven Development)** - 77 tests, 95% coverage.

## Features

- **Simple CLI**: Intuitive commands for managing scheduled tasks
- **Human-Readable Schedules**: Use expressions like `"every 1h"` or `"daily at 09:00"`
- **Centralized Management**: All scripts and logs stored in `~/.itask/`
- **Full launchd Integration**: Leverages macOS native task scheduling
- **Comprehensive Testing**: 94% code coverage with pytest

## Installation

### Modern Python Package Installation (Recommended)

```bash
pip install git+https://github.com/thomas-huang/iTask.git
```

OR


```bash
# Clone the repository
git clone https://github.com/thomas-huang/iTask
cd iTask

# Install as a Python package
pip install .

# Or install in development mode (for contributors)
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
```

### Direct Installation from Source

```bash
# Clone or download the repository
cd iTask

# Make executable
chmod +x itask_cli.py

# Add to PATH (optional)
sudo ln -s "$(pwd)/itask_cli.py" /usr/local/bin/itask
```

### Requirements

- **Python 3.8+** (tested up to Python 3.13)
- **macOS** (uses launchd - macOS native task scheduler)
- **No external dependencies** (uses only Python standard library)

## Quick Start

```bash
# Add a task that runs every hour
itask add ~/scripts/backup.sh --name backup --schedule "every 1h"

# Add a task that runs daily at 9 AM
itask add ~/scripts/report.py --schedule "daily at 09:00"

# List all tasks
itask list

# Show task details
itask show backup

# Remove a task
itask remove backup
```

**Note**: If you installed via pip, use `itask` directly. If using direct installation, use `./itask_cli.py`.

## Commands

### `itask add`

Add a new scheduled task.

```bash
itask add <script> [--name NAME] [--schedule SCHEDULE] [--working-dir DIR] [--keep-original]
```

**Examples:**

```bash
# Basic usage with interactive schedule
itask add ~/scripts/cleanup.sh

# Specify everything
itask add ~/scripts/backup.sh \
  --name daily_backup \
  --schedule "daily at 02:00" \
  --working-dir /data

# Quick interval task
itask add monitor.py --schedule "every 5m"

# Keep script in original location (don't copy to ~/.itask/scripts/)
itask add ~/projects/myapp/deploy.sh \
  --name deployment \
  --schedule "daily at 01:00" \
  --keep-original
```

**Options:**
- `--name NAME`: Custom task name (defaults to script filename)
- `--schedule SCHEDULE`: Schedule expression (interactive prompt if not provided)
- `--working-dir DIR`: Working directory for script execution
- `--keep-original`: Keep script in its original location instead of copying to `~/.itask/scripts/`

**Script Management:**
By default, itask copies your script to `~/.itask/scripts/` for centralized management. This prevents issues if you move or delete the original script. However, you can use `--keep-original` to:
- Keep scripts in their original locations (useful for project-based scripts)
- Maintain scripts within version control systems
- Edit scripts in place without re-adding tasks

### `itask list`

List all configured tasks.

```bash
itask list [--verbose]
```

**Output:**
```
NAME                 SCHEDULE                       STATUS
------------------------------------------------------------
backup               every 1h                       loaded
daily_report         daily at 09:00                 loaded
cleanup              mon-fri at 18:00               loaded
```

### `itask show`

Show detailed information about a task.

```bash
itask show <name>
```

**Output:**
```
Task: backup
Label: com.itask.backup
Script: /Users/user/.itask/scripts/backup.sh
Schedule Type: interval
Schedule: {'seconds': 3600}
Enabled: True
Working Directory: /Users/user
Stdout Log: /Users/user/.itask/logs/backup.log
Stderr Log: /Users/user/.itask/logs/backup.err.log
Created: 2025-10-15T10:30:00
Last Modified: 2025-10-15T10:30:00
Status: Loaded
```

### `itask remove`

Remove a task.

```bash
itask remove <name> [--yes] [--keep-script]
```

**Options:**
- `--yes, -y`: Skip confirmation prompt
- `--keep-script`: Don't delete the script file

**Examples:**

```bash
# Remove with confirmation
itask remove backup

# Remove without confirmation
itask remove backup -y

# Remove but keep script file
itask remove backup --keep-script
```

## Schedule Expressions

### Interval-based

Run tasks at regular intervals:

```bash
"every 30s"    # Every 30 seconds
"every 5m"     # Every 5 minutes
"every 2h"     # Every 2 hours
"every 1d"     # Every day
```

### Calendar-based

Run tasks at specific times:

```bash
"daily at 09:00"           # Every day at 9 AM
"at 14:30"                 # Every day at 2:30 PM
"monday at 10:00"          # Every Monday at 10 AM
"mon-fri at 18:00"         # Weekdays at 6 PM
"1st at 00:00"             # First day of month at midnight
```

### Shortcuts

```bash
"hourly"       # Every hour
"minutely"     # Every minute
```

## Directory Structure

```
~/.itask/
├── scripts/              # Copied task scripts
│   ├── backup.sh
│   └── cleanup.py
├── plists/              # Backup of plist files
│   ├── com.itask.backup.plist
│   └── com.itask.cleanup.plist
├── logs/                # Task logs
│   ├── backup.log
│   ├── backup.err.log
│   └── cleanup.log
└── config.json          # Task configuration database
```

Actual launchd plists are stored in: `~/Library/LaunchAgents/`

## Development

### Running Tests

```bash
# Install in development mode with test dependencies
pip install -e .[dev]

# Or install test dependencies separately
pip install -r requirements.dev.txt

# Run all tests
pytest

# Run with coverage (configured in pyproject.toml)
pytest --cov=lib --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py -v
```

### Test Results

```
77 tests passed
95% code coverage

Test breakdown:
- config.py: 16 tests, 95% coverage
- plist_generator.py: 13 tests, 100% coverage
- parser.py: 25 tests, 96% coverage
- launchd.py: 16 tests, 92% coverage
- cli.py: 7 tests (new CLI functionality)
```

### Project Structure

```
itask/
├── itask_cli.py               # Main CLI executable
├── pyproject.toml            # Modern Python package configuration
├── requirements.txt          # Runtime dependencies (empty - no external deps)
├── requirements.dev.txt      # Development dependencies
├── lib/
│   ├── __init__.py
│   ├── config.py             # Configuration management
│   ├── launchd.py            # launchd operations
│   ├── parser.py             # Schedule expression parser
│   └── plist_generator.py    # Plist file generation
├── tests/
│   ├── test_config.py
│   ├── test_launchd.py
│   ├── test_parser.py
│   └── test_plist_generator.py
├── pytest.ini               # Legacy pytest config (superseded by pyproject.toml)
└── README.md
```

## Architecture Highlights

### 1. Configuration Management (`config.py`)
- JSON-based task database
- Atomic file writes (temp file + rename)
- CRUD operations with validation
- Dataclass-based TaskConfig

### 2. Schedule Parser (`parser.py`)
- Human-readable expression parsing
- Support for interval and calendar schedules
- Extensive error handling
- Weekday ranges (mon-fri)

### 3. Plist Generator (`plist_generator.py`)
- Template-based plist generation
- Support for all launchd features
- Environment variables
- Working directory support

### 4. Launchd Manager (`launchd.py`)
- Wrapper around launchctl commands
- Load/unload operations
- Service status checking
- Error handling for common edge cases

## Troubleshooting

### Task not running

```bash
# Check if task is loaded
itask list

# View logs
tail -f ~/.itask/logs/<taskname>.log
tail -f ~/.itask/logs/<taskname>.err.log

# Check launchd status
launchctl list | grep itask
```

### Permission denied

```bash
# Make sure script is executable
chmod +x ~/.itask/scripts/<script>

# For tasks using --keep-original, check original script
chmod +x /path/to/original/script

# Check script path in task config
itask show <taskname>
```

### Script moved or deleted

For tasks created with `--keep-original`, if you move or delete the original script:

```bash
# Check current script path
itask show <taskname>

# Remove and re-add the task with new path
itask remove <taskname> -y
itask add /new/path/to/script --name <taskname> --schedule "..." --keep-original
```

### Remove stuck task

```bash
# Manually unload from launchd
launchctl unload ~/Library/LaunchAgents/com.itask.<taskname>.plist

# Remove plist
rm ~/Library/LaunchAgents/com.itask.<taskname>.plist

# Update config
itask remove <taskname> -y
```

## Technical Details

### Why launchd over cron?

- **Native to macOS**: Recommended by Apple
- **Better reliability**: Handles system sleep/wake
- **Process management**: Auto-restart on crash
- **Resource limits**: CPU, memory throttling
- **User context**: Runs in user session

### Design Decisions

1. **Copy scripts by default**: Avoids issues with moved/deleted files
2. **Optional `--keep-original`**: For users who prefer managing scripts in their original locations
3. **JSON config**: Human-readable, version control friendly
4. **Atomic writes**: Prevents corruption on crash
5. **Backup plists**: Easy debugging and recovery
6. **TDD approach**: 77 tests ensure reliability

## Contributing

This project was built with TDD. When contributing:

1. Write tests first
2. Implement to pass tests
3. Maintain >90% coverage
4. Follow existing patterns

## License

MIT License

## Credits

Built with Python 3, pytest, and a love for clean code and TDD methodology.
