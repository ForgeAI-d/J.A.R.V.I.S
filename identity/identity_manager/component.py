from core.base_manager import BaseManager
import uuid
from datetime import datetime, timezone
class IdentityManager(BaseManager):
    COMPONENT_ID = "identity.identity_manager"
    NAME = "IdentityManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True

    def __init__(self, database_manager):
        BaseManager.__init__(self)
        self.db = database_manager
    def create_user(
        self,
        name,
        role="USER",
        relationship="FRIEND",
        status="ACTIVE"
    ):
        user_id = str(
            uuid.uuid4()
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        success = self.db.execute(
            """
            INSERT INTO users (
                user_id,
                name,
                display_name,
                role,
                relationship,
                status,
                voice_profile_id,
                profile_metadata,
                created_at,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                name,
                role,
                relationship,
                status,
                None,
                "{}",
                timestamp,
                timestamp
            )
        )
        if success:
            return user_id
        return None
    def get_user(
        self,
        user_id
    ):
        return self.db.fetchone(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )
    def get_user_by_name(
        self,
        name
    ):
        return self.db.fetchone(
            """
            SELECT *
            FROM users
            WHERE name = ?
            """,
            (
                name,
            )
        )
    def get_all_users(self):
        return self.db.fetchall(
            """
            SELECT *
            FROM users
            ORDER BY name
            """
        )
    def user_exists(
        self,
        name
    ):
        user = self.get_user_by_name(
            name
        )
        return user is not None
    def update_last_seen(
        self,
        user_id
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        return self.db.execute(
            """
            UPDATE users
            SET last_seen = ?
            WHERE user_id = ?
            """,
            (
                timestamp,
                user_id
            )
        )
    def activate_user(
        self,
        user_id
    ):
        return self.db.execute(
            """
            UPDATE users
            SET status = 'ACTIVE'
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )
    def deactivate_user(
        self,
        user_id
    ):
        return self.db.execute(
            """
            UPDATE users
            SET status = 'INACTIVE'
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )
    def block_user(
        self,
        user_id
    ):
        return self.db.execute(
            """
            UPDATE users
            SET status = 'BLOCKED'
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )
    def is_admin(
        self,
        user_id
    ):
        user = self.get_user(
            user_id
        )
        if not user:
            return False
        return (
            user["role"]
            in [
                "ADMIN",
                "OWNER"
            ]
        )
    def assign_voice_profile(
        self,
        user_id,
        voice_profile_id
    ):
        return self.db.execute(
            """
            UPDATE users
            SET voice_profile_id = ?
            WHERE user_id = ?
            """,
            (
                voice_profile_id,
                user_id
            )
        )
    def get_user_devices(
        self,
        user_id
    ):
        return self.db.fetchall(
            """
            SELECT *
            FROM devices
            WHERE owner_id = ?
            """,
            (
                user_id,
            )
        )
    def get_identity_score(
        self,
        face_match=False,
        voice_match=False,
        device_match=False
    ):
        score = 0
        if device_match:
            score += 40
        if voice_match:
            score += 35
        if face_match:
            score += 25
        return score
    def verify_identity(
        self,
        face_match=False,
        voice_match=False,
        device_match=False
    ):
        score = self.get_identity_score(
            face_match,
            voice_match,
            device_match
        )
        return score >= 75
