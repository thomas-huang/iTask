"""itask - macOS launchd task manager"""

try:
    from importlib.metadata import version
    __version__ = version("itask")
except Exception:
    __version__ = "unknown"
