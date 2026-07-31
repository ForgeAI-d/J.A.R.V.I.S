from __future__ import annotations

import importlib
import importlib.util
import os
from datetime import UTC, datetime
from types import ModuleType

from core.base_manager import BaseManager


class CameraManager(BaseManager):
    COMPONENT_ID = "vision.camera_manager"
    NAME = "CameraManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True

    def __init__(
        self,
        storage_path="data/uploads/camera"
    ):
        BaseManager.__init__(self)
        self.storage_path = storage_path
        self.cameras = {}

        os.makedirs(
            self.storage_path,
            exist_ok=True
        )

    @property
    def backend_available(self) -> bool:
        return importlib.util.find_spec("cv2") is not None

    def _require_backend(self) -> ModuleType:
        if not self.backend_available:
            raise RuntimeError(
                "CameraManager backend unavailable; install optional dependency: cv2"
            )
        return importlib.import_module("cv2")

    def get_status(self):
        status = super().get_status()
        status["backend_available"] = self.backend_available
        status["optional_dependencies"] = {"cv2": self.backend_available}
        return status

    def register_camera(
        self,
        camera_id,
        source=0,
        name="Default Camera",
        camera_type="USB"
    ):
        self.cameras[camera_id] = {
            "source": source,
            "name": name,
            "type": camera_type,
            "status": "REGISTERED"
        }

        return True

    def test_camera(
        self,
        source=0
    ):
        cv2 = self._require_backend()
        camera = cv2.VideoCapture(source)

        status = camera.isOpened()

        camera.release()

        return status

    def capture_frame(
        self,
        camera_id=None,
        source=0
    ):
        cv2 = self._require_backend()
        if camera_id is not None:
            camera_config = self.cameras.get(camera_id)

            if camera_config is None:
                return None

            source = camera_config["source"]

        camera = cv2.VideoCapture(source)

        if not camera.isOpened():
            return None

        success, frame = camera.read()

        camera.release()

        if not success:
            return None

        return frame

    def capture_image(
        self,
        camera_id=None,
        source=0,
        filename=None
    ):
        cv2 = self._require_backend()
        frame = self.capture_frame(
            camera_id=camera_id,
            source=source
        )

        if frame is None:
            return None

        if filename is None:
            timestamp = datetime.now(UTC).strftime(
                "%Y%m%d_%H%M%S"
            )

            filename = f"camera_capture_{timestamp}.jpg"

        image_path = os.path.join(
            self.storage_path,
            filename
        )

        success = cv2.imwrite(
            image_path,
            frame
        )

        if not success:
            return None

        return image_path

    def list_cameras(self):
        return self.cameras

    def remove_camera(
        self,
        camera_id
    ):
        if camera_id in self.cameras:
            del self.cameras[camera_id]
            return True

        return False


if __name__ == "__main__":

    camera_manager = CameraManager()

    print("=== CAMERA TEST ===")

    print(
        "Kamera erreichbar:",
        camera_manager.test_camera(0)
    )

    image_path = camera_manager.capture_image(
        source=0
    )

    if image_path:
        print("Bild gespeichert:", image_path)
    else:
        print("Fehler beim Aufnehmen des Bildes.")
