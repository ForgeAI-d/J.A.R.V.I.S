from core.base_manager import BaseManager
import uuid
from datetime import datetime, timezone


class PermissionManager(BaseManager):
    COMPONENT_ID = "permissions.permission_manager"
    NAME = "PermissionManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True


    def __init__(self, database_manager):
        BaseManager.__init__(self)

        self.db = database_manager

    def grant_permission(
        self,
        user_id,
        permission_name,
        critical=False
    ):

        permission_id = str(
            uuid.uuid4()
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        return self.db.execute(
            """
            INSERT INTO permissions (
                permission_id,
                user_id,
                permission_name,
                allowed,
                critical,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                permission_id,
                user_id,
                permission_name,
                1,
                1 if critical else 0,
                timestamp
            )
        )

    def revoke_permission(
        self,
        user_id,
        permission_name
    ):

        return self.db.execute(
            """
            UPDATE permissions
            SET allowed = 0
            WHERE user_id = ?
            AND permission_name = ?
            """,
            (
                user_id,
                permission_name
            )
        )

    def has_permission(
        self,
        user_id,
        permission_name
    ):

        permission = self.db.fetchone(
            """
            SELECT *
            FROM permissions
            WHERE user_id = ?
            AND permission_name = ?
            AND allowed = 1
            """,
            (
                user_id,
                permission_name
            )
        )

        return permission is not None

    def get_permissions(
        self,
        user_id
    ):

        return self.db.fetchall(
            """
            SELECT *
            FROM permissions
            WHERE user_id = ?
            ORDER BY permission_name
            """,
            (
                user_id,
            )
        )

    def log_permission_check(
        self,
        user_id,
        permission_name,
        result,
        source=None,
        device_id=None,
        reason=None
    ):

        log_id = str(
            uuid.uuid4()
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        return self.db.execute(
            """
            INSERT INTO permission_logs (
                log_id,
                user_id,
                device_id,
                permission_name,
                result,
                reason,
                source,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                user_id,
                device_id,
                permission_name,
                result,
                reason,
                source,
                timestamp
            )
        )

    def check_permission(
        self,
        user_id,
        permission_name,
        source="UNKNOWN",
        device_id=None
    ):

        allowed = self.has_permission(
            user_id,
            permission_name
        )

        self.log_permission_check(
            user_id=user_id,
            permission_name=permission_name,
            result="GRANTED" if allowed else "DENIED",
            source=source,
            device_id=device_id
        )

        return allowed

    def assign_default_role_permissions(
        self,
        user_id,
        role
    ):

        role = role.upper()

        if role == "OWNER":

            permissions = [
                "system.shutdown",
                "system.restart",
                "door.unlock",
                "security.override",
                "device.manage",
                "user.manage",
                "ai.training"
            ]

        elif role == "ADMIN":

            permissions = [
                "door.unlock",
                "device.manage",
                "user.manage"
            ]

        elif role == "FRIEND":

            permissions = [
                "lights.control",
                "music.control"
            ]

        else:

            permissions = []

        for permission in permissions:

            self.grant_permission(
                user_id,
                permission
            )

        return True
