from __future__ import annotations

import subprocess
import sys


def _run_import(module_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_face_manager_import_is_silent() -> None:
    result = _run_import("vision.face_manager")
    assert result.returncode == 0, result.stderr
    assert "Please install `face_recognition_models`" not in result.stdout
    assert "Please install `face_recognition_models`" not in result.stderr


def test_face_engine_import_is_silent() -> None:
    result = _run_import("vision.engines.face_engine")
    assert result.returncode == 0, result.stderr
    assert "Please install `face_recognition_models`" not in result.stdout
    assert "Please install `face_recognition_models`" not in result.stderr


def test_camera_manager_import_does_not_require_opencv() -> None:
    result = _run_import("vision.camera_manager")
    assert result.returncode == 0, result.stderr
