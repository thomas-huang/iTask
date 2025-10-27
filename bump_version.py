#!/usr/bin/env python3
"""
Bump version in pyproject.toml (and keep lib/__init__.py in sync if present).

Usage:
  # Patch bump (default): 1.2.3 -> 1.2.4
  python bump_version.py

  # Minor bump: 1.2.3 -> 1.3.0
  python bump_version.py --part minor

  # Major bump: 1.2.3 -> 2.0.0
  python bump_version.py --part major

  # Dry run: only print the next version, do not modify files
  python bump_version.py --dry-run

Notes:
- No external dependencies; uses simple regex parsing.
- Only supports semantic versions in the form X.Y.Z.
- Intended to be called by CI after merging to the default branch.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).parent
PYPROJECT = ROOT / "pyproject.toml"
INIT_FILE = ROOT / "lib" / "__init__.py"


VersionTuple = Tuple[int, int, int]


def parse_version(s: str) -> VersionTuple:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", s.strip())
    if not m:
        raise ValueError(f"Unsupported version format: {s!r}. Expected X.Y.Z")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_version_tuple(v: VersionTuple, part: str) -> VersionTuple:
    major, minor, patch = v
    if part == "major":
        return major + 1, 0, 0
    if part == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def read_pyproject() -> str:
    if not PYPROJECT.exists():
        raise FileNotFoundError(f"{PYPROJECT} not found")
    return PYPROJECT.read_text(encoding="utf-8")


def write_pyproject(content: str) -> None:
    PYPROJECT.write_text(content, encoding="utf-8")


def extract_and_replace_version_in_pyproject(content: str, new_version: str | None = None) -> Tuple[str, str]:
    """Find version in [project] section; optionally replace with new_version.

    Returns (new_content, old_version).
    """
    lines = content.splitlines(keepends=True)

    # Locate [project] block boundaries
    header_re = re.compile(r"^\s*\[[^\]]+\]\s*$")
    start = -1
    for i, line in enumerate(lines):
        if line.strip() == "[project]":
            start = i
            break
    if start == -1:
        raise ValueError("[project] section not found in pyproject.toml")

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if header_re.match(lines[j]) and lines[j].strip() != "[project]":
            end = j
            break

    # Find version line within [project]
    version_idx = -1
    version_val = None
    version_line_re = re.compile(r"^(?P<indent>\s*)version\s*=\s*\"(?P<ver>[^\"]+)\"\s*$")

    for k in range(start + 1, end):
        m = version_line_re.match(lines[k])
        if m:
            version_idx = k
            version_val = m.group("ver")
            indent = m.group("indent")
            break

    if version_idx == -1 or version_val is None:
        raise ValueError("version = \"...\" not found in [project] section")

    if new_version is not None:
        lines[version_idx] = f"{indent}version = \"{new_version}\"\n"

    return ("".join(lines), version_val)


def sync_init_py_version(new_version: str) -> None:
    if not INIT_FILE.exists():
        return
    text = INIT_FILE.read_text(encoding="utf-8")
    # Replace __version__ = "..." if present; otherwise append it.
    # Use a function replacement to avoid backslash escaping issues.
    pattern = re.compile(r'^(__(?:version)__\s*=\s*")([^"]*)(")', re.M)
    m = pattern.search(text)
    if m:
        def repl(match: re.Match) -> str:
            return f'{match.group(1)}{new_version}{match.group(3)}'
        text = pattern.sub(repl, text, count=1)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += f'__version__ = "{new_version}"\n'
    INIT_FILE.write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Bump version in pyproject.toml")
    ap.add_argument("--part", choices=["major", "minor", "patch"], default="patch", help="Version segment to bump (default: patch)")
    ap.add_argument("--dry-run", action="store_true", help="Do not modify files, only print next version")

    args = ap.parse_args(argv)

    try:
        content = read_pyproject()
        content_no_change, old_version = extract_and_replace_version_in_pyproject(content)
        old_tuple = parse_version(old_version)
        new_tuple = bump_version_tuple(old_tuple, args.part)
        new_version = f"{new_tuple[0]}.{new_tuple[1]}.{new_tuple[2]}"
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(new_version)
        return 0

    # Write pyproject
    new_content, _ = extract_and_replace_version_in_pyproject(content, new_version)
    write_pyproject(new_content)

    # Sync lib/__init__.py if exists
    try:
        sync_init_py_version(new_version)
    except Exception as e:
        print(f"Warning: failed to sync lib/__init__.py: {e}", file=sys.stderr)

    print(f"Bumped version: {old_version} -> {new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
