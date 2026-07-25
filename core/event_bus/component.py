from core.common import BaseKernelComponent
import traceback
from datetime import datetime, UTC
from collections import defaultdict


class EventBus(BaseKernelComponent):

    COMPONENT_ID = "core.event_bus"
    NAME = "Event Bus"
    PRIORITY = 15
    AUTO_START = True

    VERSION = "0.1.0"

    def __init__(self):
        BaseKernelComponent.__init__(self)
        self.name = "Event Bus"
        self.component_id = "core.event_bus"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Verteilt Ereignisse zwischen J.A.R.V.I.S. Komponenten "
            "ohne direkte Kopplung."
        )

        self.status = "OFFLINE"
        self.health = 0

        self.listeners = defaultdict(list)
        self.event_history = []
        self.errors = []

        self.events_published = 0
        self.events_handled = 0
        self.listeners_registered = 0

        self.last_event_at = None
        self.last_started = None
        self.last_stopped = None
        self.last_error = None

        self.lifecycle = {
            "registered": False,
            "dependencies_resolved": True,
            "initialized": False,
            "started": False,
            "healthy": False
        }

        self.capabilities = [
            "event_publish",
            "event_subscribe",
            "event_unsubscribe",
            "event_history",
            "listener_priority",
            "error_isolation",
            "event_statistics"
        ]

    def initialize(self):
        self.lifecycle["initialized"] = True
        return True

    def start(self):
        self.status = "ONLINE"
        self.health = 100
        self.last_started = datetime.now(UTC).isoformat()
        self.last_error = None

        self.lifecycle["started"] = True
        self.lifecycle["healthy"] = True

        return True

    def stop(self):
        self.status = "OFFLINE"
        self.health = 0
        self.last_stopped = datetime.now(UTC).isoformat()

        self.lifecycle["started"] = False
        self.lifecycle["healthy"] = False

        return True

    def subscribe(
        self,
        event_type,
        callback,
        priority=100
    ):
        listener = {
            "callback": callback,
            "priority": priority,
            "registered_at": datetime.now(UTC).isoformat()
        }

        self.listeners[event_type].append(listener)

        self.listeners[event_type] = sorted(
            self.listeners[event_type],
            key=lambda item: item["priority"]
        )

        self.listeners_registered += 1

        return True

    def unsubscribe(
        self,
        event_type,
        callback
    ):
        if event_type not in self.listeners:
            return False

        original_count = len(
            self.listeners[event_type]
        )

        self.listeners[event_type] = [
            listener
            for listener in self.listeners[event_type]
            if listener["callback"] != callback
        ]

        return len(self.listeners[event_type]) < original_count

    def publish(
        self,
        event_type,
        payload=None,
        source="UNKNOWN",
        severity="INFO"
    ):
        if payload is None:
            payload = {}

        event = {
            "event_type": event_type,
            "payload": payload,
            "source": source,
            "severity": severity,
            "timestamp": datetime.now(UTC).isoformat()
        }

        self.event_history.append(event)
        self.events_published += 1
        self.last_event_at = event["timestamp"]

        listeners = self.listeners.get(
            event_type,
            []
        )

        for listener in listeners:
            try:
                listener["callback"](event)
                self.events_handled += 1

            except Exception as error:
                self.record_error(
                    event_type=event_type,
                    error=error
                )

        return event

    def emit(
        self,
        event
    ):
        if isinstance(event, dict):
            event_type = event.get(
                "event_type",
                "UNKNOWN"
            )

            return self.publish(
                event_type=event_type,
                payload=event.get(
                    "payload",
                    {}
                ),
                source=event.get(
                    "source",
                    "UNKNOWN"
                ),
                severity=event.get(
                    "severity",
                    "INFO"
                )
            )

        return self.publish(
            event_type=str(event),
            payload={},
            source="UNKNOWN",
            severity="INFO"
        )

    def record_error(
        self,
        event_type,
        error
    ):
        error_data = {
            "event_type": event_type,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(UTC).isoformat()
        }

        self.errors.append(error_data)
        self.last_error = str(error)

        self.health = max(
            0,
            self.health - 5
        )

        if self.health == 0:
            self.status = "ERROR"
            self.lifecycle["healthy"] = False

        return True

    def clear_history(self):
        self.event_history = []
        return True

    def clear_errors(self):
        self.errors = []
        self.last_error = None

        if self.status == "ERROR":
            self.status = "ONLINE"
            self.health = 100
            self.lifecycle["healthy"] = True

        return True

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "mission": self.mission,
            "capabilities": self.capabilities
        }

    def get_statistics(self):
        return {
            "events_published": self.events_published,
            "events_handled": self.events_handled,
            "listeners_registered": self.listeners_registered,
            "event_types": list(self.listeners.keys()),
            "history_count": len(self.event_history),
            "error_count": len(self.errors),
            "last_event_at": self.last_event_at
        }

    def get_status(self):
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": self.lifecycle,
            "statistics": self.get_statistics(),
            "last_started": self.last_started,
            "last_stopped": self.last_stopped,
            "last_error": self.last_error
        }

    def get_health(self):
        return {
            "component_id": self.component_id,
            "status": self.status,
            "health": self.health,
            "healthy": self.lifecycle["healthy"],
            "last_error": self.last_error
        }


if __name__ == "__main__":

    event_bus = EventBus()

    event_bus.initialize()
    event_bus.start()

    def test_listener(event):
        print("Listener erhalten:", event)

    event_bus.subscribe(
        event_type="TEST_EVENT",
        callback=test_listener,
        priority=100
    )

    event_bus.publish(
        event_type="TEST_EVENT",
        payload={
            "message": "EventBus funktioniert"
        },
        source="EventBusTest",
        severity="INFO"
    )

    print()
    print("=== EVENT BUS STATUS ===")
    print(
        event_bus.get_status()
    )