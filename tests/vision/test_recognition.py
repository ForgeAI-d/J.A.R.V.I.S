"""Optional smoke test for the face-recognition dependency."""
from __future__ import annotations

from pathlib import Path

import pytest

face_recognition = pytest.importorskip("face_recognition")


@pytest.mark.hardware
def test_face_recognition_with_local_test_image() -> None:
    image_path = Path(__file__).resolve().parents[2] / "test.jpg"
    if not image_path.exists():
        pytest.skip("test.jpg ist nicht vorhanden")

    image = face_recognition.load_image_file(str(image_path))
    faces = face_recognition.face_locations(image)
    encodings = face_recognition.face_encodings(image)

    assert isinstance(faces, list)
    assert isinstance(encodings, list)
