"""Version helpers for itask."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from importlib.metadata import PackageNotFoundError, version as metadata_version
except Exception:  # pragma: no cover - fallback for very old Python
    PackageNotFoundError = Exception  # type: ignore[assignment]
    metadata_version = None  # type: ignore[assignment]


_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']\s*$')


def _read_pyproject_version() -> str | None:
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None

    try:
        lines = pyproject.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None

    in_project = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if not in_project:
            continue
        match = _VERSION_RE.match(line)
        if match:
            return match.group(1)
    return None


def get_version() -> str:
    """Return the canonical version string.

    Prefer pyproject.toml when present (repo truth). Fall back to package metadata
    for installed distributions.
    """
    repo_version = _read_pyproject_version()
    if repo_version:
        return repo_version

    if metadata_version is None:
        return "unknown"

    try:
        return metadata_version("itask")
    except PackageNotFoundError:
        return "unknown"
    except Exception:
        return "unknown"


__version__ = get_version()
