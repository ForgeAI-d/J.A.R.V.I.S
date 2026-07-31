"""Reusable hardware availability helpers."""
from __future__ import annotations

from typing import Any

import pytest

from .optional import require_module


def require_camera(index: int = 0) -> Any:
    """Open a camera for a hardware test or skip when unavailable."""

    cv2 = require_module("cv2", purpose="Kameratests")
    capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        pytest.skip(f"Keine Kamera am Index {index} verfügbar")
    return capture
