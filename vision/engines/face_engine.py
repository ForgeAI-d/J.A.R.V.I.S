from __future__ import annotations

import importlib
import importlib.util
import json
import os
import uuid
from datetime import UTC, datetime
from types import ModuleType

from core.base_engine import BaseEngine


class _FaceBackend:
    def __init__(self) -> None:
        self._face_recognition: ModuleType | None = None
        self._numpy: ModuleType | None = None

    @staticmethod
    def package_available(package_name: str) -> bool:
        return importlib.util.find_spec(package_name) is not None

    @property
    def missing_packages(self) -> list[str]:
        return [
            name
            for name in ("numpy", "face_recognition", "face_recognition_models")
            if not self.package_available(name)
        ]

    @property
    def available(self) -> bool:
        return not self.missing_packages

    def load(self) -> tuple[ModuleType, ModuleType]:
        missing = self.missing_packages
        if missing:
            raise RuntimeError(
                "FaceEngine backend unavailable; install optional dependencies: "
                + ", ".join(missing)
            )
        if self._numpy is None:
            self._numpy = importlib.import_module("numpy")
        if self._face_recognition is None:
            self._face_recognition = importlib.import_module("face_recognition")
        return self._face_recognition, self._numpy


_FACE_BACKEND = _FaceBackend()
class FaceEngine(BaseEngine):

    ENGINE_ID = "vision.face"
    NAME = "Face Engine"
    VERSION = "0.1.0"
    AUTHOR = "Velthor Technologies"
    MANAGER = "VisionManager"
    MISSION = "Erkennt bekannte Personen anhand von Gesichtern."
    AUTO_START = True
    PRIORITY = 100

    # Python packages are optional runtime capabilities, not kernel components.
    REQUIRES = []
    OPTIONAL_PACKAGES = ("face_recognition", "numpy")

    OPTIONAL = [
        "DatabaseManager",
        "EventManager",
        "MemoryManager"
    ]

    CAPABILITIES = [
        "face_detection",
        "face_encoding",
        "face_identification",
        "face_registration",
        "face_learning",
        "vision_manager_integration"
    ]

    def __init__(
        self,
        database_manager=None,
        event_manager=None,
        memory_manager=None,
        storage_path="data/face_profiles",
        tolerance=0.6
    ):
        super().__init__()

        self.db = database_manager
        self.event_manager = event_manager
        self.memory_manager = memory_manager

        self.storage_path = storage_path
        self.tolerance = tolerance

        self.faces_detected = 0
        self.faces_identified = 0
        self.faces_unknown = 0
        self.frames_processed = 0
        self.last_detection = None

        os.makedirs(
            self.storage_path,
            exist_ok=True
        )

    @property
    def backend_available(self) -> bool:
        return _FACE_BACKEND.available

    @property
    def missing_optional_dependencies(self) -> list[str]:
        return _FACE_BACKEND.missing_packages

    def _require_backend(self) -> tuple[ModuleType, ModuleType]:
        return _FACE_BACKEND.load()

    def process_frame(
        self,
        frame,
        camera_id="default"
    ):
        face_recognition, _ = self._require_backend()
        self.frames_processed += 1

        face_locations = face_recognition.face_locations(
            frame
        )

        face_encodings = face_recognition.face_encodings(
            frame,
            face_locations
        )

        results = []

        for face_location, face_encoding in zip(
            face_locations,
            face_encodings
        ):
            self.faces_detected += 1

            match = self.identify_encoding(
                face_encoding
            )

            if match:
                self.faces_identified += 1

                result = {
                    "type": "known_face",
                    "camera_id": camera_id,
                    "user_id": match["user_id"],
                    "face_profile_id": match["face_profile_id"],
                    "profile_name": match["profile_name"],
                    "confidence": match["confidence"],
                    "distance": match["distance"],
                    "location": face_location,
                    "timestamp": datetime.now(UTC).isoformat()
                }

                self.log_event(
                    event_type="FACE_IDENTIFIED",
                    severity="INFO",
                    message=(
                        "Bekanntes Gesicht erkannt: "
                        f"{match['profile_name']}"
                    )
                )

            else:
                self.faces_unknown += 1

                result = {
                    "type": "unknown_face",
                    "camera_id": camera_id,
                    "user_id": None,
                    "face_profile_id": None,
                    "profile_name": "UNKNOWN",
                    "confidence": 0,
                    "distance": None,
                    "location": face_location,
                    "timestamp": datetime.now(UTC).isoformat()
                }

                self.log_event(
                    event_type="UNKNOWN_FACE",
                    severity="WARNING",
                    message="Unbekanntes Gesicht erkannt"
                )

            results.append(
                result
            )

        self.last_detection = datetime.now(UTC).isoformat()

        return {
            "engine_id": self.engine_id,
            "engine_name": self.name,
            "camera_id": camera_id,
            "faces_found": len(results),
            "results": results,
            "timestamp": self.last_detection
        }

    def identify_encoding(
        self,
        unknown_encoding
    ):
        face_recognition, np = self._require_backend()
        if self.db is None:
            return None

        profiles = self.db.fetchall(
            """
            SELECT *
            FROM face_profiles
            """
        )

        best_match = None
        best_distance = 999

        for profile in profiles:
            encoding_path = profile["encoding_path"]

            if not encoding_path:
                continue

            if not os.path.exists(
                encoding_path
            ):
                continue

            with open(
                encoding_path,
                "r",
                encoding="utf-8"
            ) as file:
                known_encoding = np.array(
                    json.load(file)
                )

            distance = face_recognition.face_distance(
                [
                    known_encoding
                ],
                unknown_encoding
            )[0]

            if distance < best_distance:
                best_distance = distance
                best_match = profile

        if best_match is None:
            return None

        if best_distance > self.tolerance:
            return None

        confidence = round(
            (1 - best_distance) * 100,
            2
        )

        self.db.execute(
            """
            UPDATE face_profiles
            SET
                last_seen = ?,
                confidence = ?
            WHERE face_profile_id = ?
            """,
            (
                datetime.now(UTC).isoformat(),
                confidence,
                best_match["face_profile_id"]
            )
        )

        return {
            "face_profile_id": best_match["face_profile_id"],
            "user_id": best_match["user_id"],
            "profile_name": best_match["profile_name"],
            "confidence": confidence,
            "distance": float(best_distance)
        }

    def register_face_from_image(
        self,
        user_id,
        image_path,
        profile_name="default"
    ):
        face_recognition, _ = self._require_backend()
        if self.db is None:
            return None

        image = face_recognition.load_image_file(
            image_path
        )

        encodings = face_recognition.face_encodings(
            image
        )

        if len(encodings) == 0:
            return None

        face_encoding = encodings[0]

        face_profile_id = str(
            uuid.uuid4()
        )

        user_folder = os.path.join(
            self.storage_path,
            user_id
        )

        os.makedirs(
            user_folder,
            exist_ok=True
        )

        encoding_path = os.path.join(
            user_folder,
            f"{face_profile_id}.json"
        )

        with open(
            encoding_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                face_encoding.tolist(),
                file
            )

        timestamp = datetime.now(UTC).isoformat()

        success = self.db.execute(
            """
            INSERT INTO face_profiles (
                face_profile_id,
                user_id,
                profile_name,
                encoding_path,
                created_at,
                last_seen,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                face_profile_id,
                user_id,
                profile_name,
                encoding_path,
                timestamp,
                None,
                0
            )
        )

        if success:
            self.log_event(
                event_type="FACE_REGISTERED",
                severity="INFO",
                message=f"Gesichtsprofil registriert: {profile_name}"
            )

            return face_profile_id

        return None

    def get_user_faces(
        self,
        user_id
    ):
        if self.db is None:
            return []

        return self.db.fetchall(
            """
            SELECT *
            FROM face_profiles
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )

    def delete_user_faces(
        self,
        user_id
    ):
        if self.db is None:
            return False

        faces = self.get_user_faces(
            user_id
        )

        for face in faces:
            encoding_path = face["encoding_path"]

            if encoding_path and os.path.exists(
                encoding_path
            ):
                os.remove(
                    encoding_path
                )

        return self.db.execute(
            """
            DELETE FROM face_profiles
            WHERE user_id = ?
            """,
            (
                user_id,
            )
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
            category="FACE",
            content=content,
            importance=importance
        )

        return True

    def health_check(self):
        if self.db is None:
            self.health = 50
            self.last_error = "DatabaseManager nicht verbunden"
            self.lifecycle["healthy"] = False
            return self.get_health()

        self.health = 100
        self.last_error = None
        self.lifecycle["healthy"] = True

        return self.get_health()

    def get_statistics(self):
        return {
            "frames_processed": self.frames_processed,
            "faces_detected": self.faces_detected,
            "faces_identified": self.faces_identified,
            "faces_unknown": self.faces_unknown,
            "last_detection": self.last_detection
        }

    def get_status(self):
        status = super().get_status()

        status.update(
            {
                "tolerance": self.tolerance,
                "storage_path": self.storage_path,
                "statistics": self.get_statistics(),
                "database_connected": self.db is not None,
                "event_manager_connected": self.event_manager is not None,
                "memory_manager_connected": self.memory_manager is not None
            }
        )

        return status


if __name__ == "__main__":
    engine = FaceEngine()

    engine.initialize()
    engine.start()

    print("=== FACE ENGINE TEST ===")
    print(engine.get_status())