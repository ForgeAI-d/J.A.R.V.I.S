from core.base_manager import BaseManager
import uuid
from datetime import datetime, timezone
class EventManager(BaseManager):
    COMPONENT_ID = "events.event_manager"
    NAME = "EventManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True

    def __init__(self, database_manager):
        BaseManager.__init__(self)
        self.db = database_manager
    def create_event(
        self,
        event_type,
        source,
        severity,
        message
    ):
        event_id = str(
            uuid.uuid4()
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        success = self.db.execute(
            """
            INSERT INTO events (
                event_id,
                event_type,
                source,
                severity,
                message,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type,
                source,
                severity,
                message,
                timestamp
            )
        )
        if success:
            return event_id
        return None
    def get_event(
        self,
        event_id
    ):
        return self.db.fetchone(
            """
            SELECT *
            FROM events
            WHERE event_id = ?
            """,
            (
                event_id,
            )
        )
    def get_all_events(self):
        return self.db.fetchall(
            """
            SELECT *
            FROM events
            ORDER BY timestamp DESC
            """
        )
    def get_events_by_type(
        self,
        event_type
    ):
        return self.db.fetchall(
            """
            SELECT *
            FROM events
            WHERE event_type = ?
            ORDER BY timestamp DESC
            """,
            (
                event_type,
            )
        )
    def get_events_by_severity(
        self,
        severity
    ):
        return self.db.fetchall(
            """
            SELECT *
            FROM events
            WHERE severity = ?
            ORDER BY timestamp DESC
            """,
            (
                severity,
            )
        )
    def get_recent_events(
        self,
        limit=50
    ):
        return self.db.fetchall(
            f"""
            SELECT *
            FROM events
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
        )
    def count_events(self):
        result = self.db.fetchone(
            """
            SELECT COUNT(*) AS total
            FROM events
            """
        )
        if result:
            return result["total"]
        return 0
    def log_info(
        self,
        source,
        message
    ):
        return self.create_event(
            event_type="INFO",
            source=source,
            severity="INFO",
            message=message
        )
    def log_warning(
        self,
        source,
        message
    ):
        return self.create_event(
            event_type="WARNING",
            source=source,
            severity="WARNING",
            message=message
        )
    def log_error(
        self,
        source,
        message
    ):
        return self.create_event(
            event_type="ERROR",
            source=source,
            severity="ERROR",
            message=message
        )
    def log_security(
        self,
        source,
        message
    ):
        return self.create_event(
            event_type="SECURITY",
            source=source,
            severity="CRITICAL",
            message=message
        )
