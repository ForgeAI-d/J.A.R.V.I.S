"""Optional smoke test for the vision pipeline."""
from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("face_recognition")

from vision.engines.face_engine import FaceEngine
from vision.vision_manager import VisionManager


def test_vision_pipeline_registration() -> None:
    camera_manager = Mock()
    vision_manager = VisionManager(camera_manager=camera_manager)
    face_engine = FaceEngine()

    vision_manager.register_engine(face_engine)

    assert vision_manager.get_status() is not None
    assert face_engine.get_status() is not None
