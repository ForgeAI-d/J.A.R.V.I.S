"""General-purpose test helpers."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


@contextmanager
def temporary_project_dir() -> Iterator[Path]:
    """Yield an automatically cleaned temporary project directory."""

    with TemporaryDirectory(prefix="jarvis-test-") as directory:
        yield Path(directory)
