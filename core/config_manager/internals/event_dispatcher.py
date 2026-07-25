from datetime import datetime, UTC
from threading import RLock


class ConfigEvents:

    VERSION = "1.0.0"

    def __init__(
        self,
        event_bus=None,
        logger=None
    ):

        # -------------------------------------------------
        # Manifest
        # -------------------------------------------------

        self.component_id = "core.config_events"
        self.name = "Config Events"
        self.version = self.VERSION
        self.author = "Velthor Technologies"

        self.mission = (
            "Veröffentlicht sämtliche "
            "Konfigurationsereignisse "
            "im Kernel."
        )

        # -------------------------------------------------
        # References
        # -------------------------------------------------

        self.event_bus = event_bus
        self.logger = logger

        # -------------------------------------------------
        # Runtime
        # -------------------------------------------------

        self.lock = RLock()

        self.status = "ONLINE"
        self.health = 100

        self.last_error = None

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        self.statistics = {
            "events_sent": 0,
            "failed_events": 0
        }

        # -------------------------------------------------
        # Timeline
        # -------------------------------------------------

        self.timeline = []

        # -------------------------------------------------
        # Capabilities
        # -------------------------------------------------

        self.capabilities = [
            "config_changed",
            "config_created",
            "config_deleted",
            "namespace_changed",
            "event_bus_integration"
        ]

    # =====================================================
    # Timeline
    # =====================================================

    def add_timeline_event(
        self,
        event_type,
        payload=None
    ):

        if payload is None:
            payload = {}

        with self.lock:

            self.timeline.append(
                {
                    "event": event_type,
                    "payload": payload,
                    "timestamp": datetime.now(
                        UTC
                    ).isoformat()
                }
            )

        return True

    # =====================================================
    # Publish
    # =====================================================

    def publish(
        self,
        event_name,
        payload
    ):

        try:

            if self.event_bus is not None:

                self.event_bus.publish(
                    event_name,
                    payload
                )

            self.statistics["events_sent"] += 1

            self.add_timeline_event(
                event_name,
                payload
            )

            return True

        except Exception as error:

            self.statistics["failed_events"] += 1

            self.last_error = str(error)

            return False

    # =====================================================
    # Events
    # =====================================================

    def config_changed(
        self,
        namespace,
        key,
        old_value,
        new_value
    ):

        return self.publish(

            "CONFIG_CHANGED",

            {
                "namespace": namespace,
                "key": key,
                "old": old_value,
                "new": new_value
            }

        )

    def config_created(
        self,
        namespace
    ):

        return self.publish(

            "CONFIG_CREATED",

            {
                "namespace": namespace
            }

        )

    def config_deleted(
        self,
        namespace
    ):

        return self.publish(

            "CONFIG_DELETED",

            {
                "namespace": namespace
            }

        )

    def namespace_changed(
        self,
        namespace
    ):

        return self.publish(

            "CONFIG_NAMESPACE_CHANGED",

            {
                "namespace": namespace
            }

        )

    # =====================================================
    # Status
    # =====================================================

    def get_status(self):

        return {

            "manifest": {

                "component_id": self.component_id,
                "name": self.name,
                "version": self.version,
                "author": self.author,
                "mission": self.mission,
                "capabilities": self.capabilities

            },

            "status": self.status,

            "health": self.health,

            "statistics": dict(
                self.statistics
            ),

            "timeline_count": len(
                self.timeline
            ),

            "last_error": self.last_error

        }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    events = ConfigEvents()

    events.config_created(
        "boot"
    )

    events.config_changed(
        "boot",
        "boot_mode",
        "development",
        "production"
    )

    events.namespace_changed(
        "boot"
    )

    events.config_deleted(
        "boot"
    )

    print("=== CONFIG EVENTS TEST ===")
    print()
    print(events.get_status())