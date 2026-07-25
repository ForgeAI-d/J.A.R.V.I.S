"""Hardware smoke test for OpenCV camera access.

The test is skipped automatically when no camera is available, so importing the
module never terminates the complete pytest run.
"""
from __future__ import annotations

import cv2
import pytest


@pytest.mark.hardware
def test_camera_can_capture_frame() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap.release()
        pytest.skip("Keine Kamera verfügbar")

    try:
        ret, frame = cap.read()
        assert ret, "Konnte kein Bild aufnehmen"
        assert frame is not None
    finally:
        cap.release()
