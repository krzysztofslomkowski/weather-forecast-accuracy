"""Basic I/O helpers for file-system paths used in the project."""

from pathlib import Path


def ensure_directory(path: str) -> Path:
    """Create directory if it does not exist and return it as Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
