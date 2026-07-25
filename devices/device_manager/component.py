from core.base_manager import BaseManager
import uuid
from datetime import datetime, timezone


class DeviceManager(BaseManager):
    COMPONENT_ID = "devices.device_manager"
    NAME = "DeviceManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True


    def __init__(self, database_manager):
        BaseManager.__init__(self)

        self.db = database_manager

    def register_device(
        self,
        owner_id,
        name,
        device_type,
        platform="UNKNOWN"
    ):

        device_id = str(
            uuid.uuid4()
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        success = self.db.execute(
            """
            INSERT INTO devices (
                device_id,
                owner_id,
                name,
                device_type,
                platform,
                trusted,
                status,
                first_seen,
                last_seen,
                device_fingerprint,
                agent_version,
                local_ip,
                public_ip,
                lost_mode,
                quarantine_mode
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                device_id,
                owner_id,
                name,
                device_type,
                platform,
                1,
                "ONLINE",
                timestamp,
                timestamp,
                None,
                "1.0",
                None,
                None,
                0,
                0
            )
        )

        if success:
            return device_id

        return None

    def get_device(
        self,
        device_id
    ):

        return self.db.fetchone(
            """
            SELECT *
            FROM devices
            WHERE device_id = ?
            """,
            (
                device_id,
            )
        )

    def get_all_devices(self):

        return self.db.fetchall(
            """
            SELECT *
            FROM devices
            ORDER BY name
            """
        )

    def get_user_devices(
        self,
        owner_id
    ):

        return self.db.fetchall(
            """
            SELECT *
            FROM devices
            WHERE owner_id = ?
            """,
            (
                owner_id,
            )
        )

    def set_online(
        self,
        device_id
    ):

        timestamp = datetime.now(timezone.utc).isoformat()

        return self.db.execute(
            """
            UPDATE devices
            SET
                status = 'ONLINE',
                last_seen = ?
            WHERE device_id = ?
            """,
            (
                timestamp,
                device_id
            )
        )

    def set_offline(
        self,
        device_id
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET status = 'OFFLINE'
            WHERE device_id = ?
            """,
            (
                device_id,
            )
        )

    def set_trusted(
        self,
        device_id,
        trusted=True
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET trusted = ?
            WHERE device_id = ?
            """,
            (
                1 if trusted else 0,
                device_id
            )
        )

    def enable_lost_mode(
        self,
        device_id
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET lost_mode = 1
            WHERE device_id = ?
            """,
            (
                device_id,
            )
        )

    def disable_lost_mode(
        self,
        device_id
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET lost_mode = 0
            WHERE device_id = ?
            """,
            (
                device_id,
            )
        )

    def enable_quarantine_mode(
        self,
        device_id
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET quarantine_mode = 1
            WHERE device_id = ?
            """,
            (
                device_id,
            )
        )

    def disable_quarantine_mode(
        self,
        device_id
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET quarantine_mode = 0
            WHERE device_id = ?
            """,
            (
                device_id,
            )
        )

    def update_fingerprint(
        self,
        device_id,
        fingerprint
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET device_fingerprint = ?
            WHERE device_id = ?
            """,
            (
                fingerprint,
                device_id
            )
        )

    def update_network_info(
        self,
        device_id,
        local_ip,
        public_ip
    ):

        return self.db.execute(
            """
            UPDATE devices
            SET
                local_ip = ?,
                public_ip = ?
            WHERE device_id = ?
            """,
            (
                local_ip,
                public_ip,
                device_id
            )
        )
