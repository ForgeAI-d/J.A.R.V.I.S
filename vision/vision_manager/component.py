from datetime import datetime, UTC

from core.base_manager import BaseManager


class VisionManager(BaseManager):
    COMPONENT_ID = "vision.vision_manager"
    NAME = "VisionManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True


    MANAGER_ID = "vision.manager"
    NAME = "Vision Manager"
    VERSION = "0.1.0"
    AUTHOR = "Velthor Technologies"
    MISSION = "Koordiniert alle visuellen Engines von J.A.R.V.I.S."
    AUTO_START = True
    PRIORITY = 100

    REQUIRES = []
    OPTIONAL = [
        "CameraManager",
        "EventManager",
        "MemoryManager"
    ]

    CAPABILITIES = [
        "vision_engine_management",
        "frame_processing",
        "camera_scanning",
        "vision_status_reporting"
    ]

    def __init__(
        self,
        camera_manager=None,
        event_manager=None,
        memory_manager=None
    ):
        super().__init__()

        self.camera_manager = camera_manager
        self.event_manager = event_manager
        self.memory_manager = memory_manager

        self.last_scan = None
        self.scan_count = 0
        self.detections = []

    def scan_camera(
        self,
        camera_id=None,
        source=0
    ):
        if self.camera_manager is None:
            self.last_error = "CameraManager nicht verbunden"
            return None

        frame = self.camera_manager.capture_frame(
            camera_id=camera_id,
            source=source
        )

        if frame is None:
            self.last_error = "Kein Kamerabild erhalten"
            return None

        return self.process_frame(
            frame=frame,
            camera_id=camera_id or "default"
        )

    def process_frame(
        self,
        frame,
        camera_id="default"
    ):
        results = []

        for engine in self.engines.values():
            if engine.status != "ONLINE":
                continue

            if not hasattr(engine, "process_frame"):
                continue

            try:
                engine_result = engine.process_frame(
                    frame=frame,
                    camera_id=camera_id
                )

                if engine_result is not None:
                    results.append(engine_result)

            except Exception as error:
                engine.set_error(error)

                self.log_event(
                    event_type="VISION_ENGINE_ERROR",
                    severity="ERROR",
                    message=f"{engine.name}: {error}"
                )

        self.last_scan = datetime.now(UTC).isoformat()
        self.scan_count += 1
        self.detections.extend(results)

        return {
            "camera_id": camera_id,
            "timestamp": self.last_scan,
            "results": results
        }

    def scan_once(
        self,
        source=0
    ):
        return self.scan_camera(
            source=source
        )

    def log_event(
        self,
        event_type,
        severity,
        message
    ):
        if self.event_manager is None:
            return False

        self.event_manager.create_event(
            event_type=event_type,
            source=self.name,
            severity=severity,
            message=message
        )

        return True

    def save_memory(
        self,
        user_id,
        content,
        importance=3
    ):
        if self.memory_manager is None:
            return False

        self.memory_manager.create_memory(
            user_id=user_id,
            category="VISION",
            content=content,
            importance=importance
        )

        return True

    def get_detections(self):
        return self.detections

    def clear_detections(self):
        self.detections = []
        return True

    def get_status(self):
        status = super().get_status()

        status.update(
            {
                "last_scan": self.last_scan,
                "scan_count": self.scan_count,
                "detection_count": len(self.detections),
                "camera_manager_connected": self.camera_manager is not None,
                "event_manager_connected": self.event_manager is not None,
                "memory_manager_connected": self.memory_manager is not None
            }
        )

        return status


if __name__ == "__main__":
    manager = VisionManager()

    print("=== VISION MANAGER TEST ===")
    print(manager.get_status())
