from core.base_manager import BaseManager
import uuid
import json
import os
from datetime import datetime, timezone

import numpy as np
import face_recognition
import cv2


class FaceManager(BaseManager):
    COMPONENT_ID = "vision.face_manager"
    NAME = "FaceManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True


    def __init__(
        self,
        database_manager,
        storage_path="data/face_profiles"
    ):
        BaseManager.__init__(self)
        self.db = database_manager
        self.storage_path = storage_path

        os.makedirs(
            self.storage_path,
            exist_ok=True
        )

    def register_face(
        self,
        user_id,
        image_path,
        profile_name="default"
    ):
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

        timestamp = datetime.now(timezone.utc).isoformat()

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
            return face_profile_id

        return None

    def get_user_faces(
        self,
        user_id
    ):
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

    def delete_face(
        self,
        user_id
    ):
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

    def identify_face(
        self,
        image_path,
        tolerance=0.6
    ):
        image = face_recognition.load_image_file(
            image_path
        )

        unknown_encodings = face_recognition.face_encodings(
            image
        )

        if len(unknown_encodings) == 0:
            return None

        unknown_encoding = unknown_encodings[0]

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

        if best_distance > tolerance:
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
                datetime.now(timezone.utc).isoformat(),
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
    if __name__ == "__main__":
        print("FaceManager erfolgreich geladen")
