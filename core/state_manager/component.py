from core.base_manager import BaseManager
import json
from copy import deepcopy
from datetime import datetime, UTC
from threading import Lock


class StateManager(BaseManager):

    COMPONENT_ID = "core.state_manager"
    MANAGER_ID = "core.state_manager"
    NAME = "State Manager"
    PRIORITY = 30
    AUTO_START = True

    VERSION = "0.1.0"

    def __init__(self):
        BaseManager.__init__(self)
        self.name = "State Manager"
        self.component_id = "core.state_manager"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Verwaltet den aktuellen Runtime-Zustand "
            "von J.A.R.V.I.S. ohne Fachlogik."
        )

        self.status = "OFFLINE"
        self.health = 0

        self.states = {}
        self.snapshots = {}

        self.lock = Lock()

        self.reads = 0
        self.writes = 0
        self.deletes = 0
        self.updates = 0
        self.snapshots_created = 0
        self.restores = 0
        self.exports = 0
        self.imports = 0

        self.last_read_at = None
        self.last_write_at = None
        self.last_snapshot_at = None
        self.last_restore_at = None
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
            "state_set",
            "state_get",
            "state_update",
            "state_delete",
            "state_exists",
            "state_increment",
            "state_decrement",
            "state_toggle",
            "namespace_clear",
            "snapshot_create",
            "snapshot_restore",
            "json_export",
            "json_import",
            "thread_safe_access"
        ]

    def initialize(self):
        self.lifecycle["initialized"] = True
        return True

    def start(self):
        if not self.lifecycle["initialized"]:
            self.initialize()

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

    def set(
        self,
        namespace,
        key,
        value
    ):
        with self.lock:
            if namespace not in self.states:
                self.states[namespace] = {}

            self.states[namespace][key] = value

            self.writes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def get(
        self,
        namespace,
        key=None,
        default=None
    ):
        with self.lock:
            self.reads += 1
            self.last_read_at = datetime.now(UTC).isoformat()

            if namespace not in self.states:
                return default

            if key is None:
                return deepcopy(
                    self.states[namespace]
                )

            return self.states[namespace].get(
                key,
                default
            )

    def update(
        self,
        namespace,
        values
    ):
        if not isinstance(values, dict):
            self.last_error = "State update values must be a dictionary"
            return False

        with self.lock:
            if namespace not in self.states:
                self.states[namespace] = {}

            self.states[namespace].update(
                values
            )

            self.updates += 1
            self.writes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def delete(
        self,
        namespace,
        key
    ):
        with self.lock:
            if namespace not in self.states:
                return False

            if key not in self.states[namespace]:
                return False

            del self.states[namespace][key]

            self.deletes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def exists(
        self,
        namespace,
        key
    ):
        with self.lock:
            self.reads += 1
            self.last_read_at = datetime.now(UTC).isoformat()

            return (
                namespace in self.states
                and key in self.states[namespace]
            )

    def increment(
        self,
        namespace,
        key,
        amount=1
    ):
        with self.lock:
            if namespace not in self.states:
                self.states[namespace] = {}

            current_value = self.states[namespace].get(
                key,
                0
            )

            if not isinstance(
                current_value,
                (int, float)
            ):
                self.last_error = "State value is not numeric"
                return False

            self.states[namespace][key] = current_value + amount

            self.writes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def decrement(
        self,
        namespace,
        key,
        amount=1
    ):
        return self.increment(
            namespace=namespace,
            key=key,
            amount=-amount
        )

    def toggle(
        self,
        namespace,
        key
    ):
        with self.lock:
            if namespace not in self.states:
                self.states[namespace] = {}

            current_value = self.states[namespace].get(
                key,
                False
            )

            self.states[namespace][key] = not bool(
                current_value
            )

            self.writes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def clear_namespace(
        self,
        namespace
    ):
        with self.lock:
            if namespace not in self.states:
                return False

            del self.states[namespace]

            self.deletes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def clear_all(self):
        with self.lock:
            self.states = {}

            self.deletes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def get_namespace(
        self,
        namespace
    ):
        return self.get(
            namespace=namespace,
            key=None,
            default={}
        )

    def get_all_states(self):
        with self.lock:
            self.reads += 1
            self.last_read_at = datetime.now(UTC).isoformat()

            return deepcopy(
                self.states
            )

    def snapshot(
        self,
        snapshot_id=None
    ):
        if snapshot_id is None:
            snapshot_id = datetime.now(UTC).strftime(
                "%Y%m%d_%H%M%S"
            )

        with self.lock:
            self.snapshots[snapshot_id] = deepcopy(
                self.states
            )

            self.snapshots_created += 1
            self.last_snapshot_at = datetime.now(UTC).isoformat()

        return snapshot_id

    def restore(
        self,
        snapshot_id
    ):
        with self.lock:
            if snapshot_id not in self.snapshots:
                return False

            self.states = deepcopy(
                self.snapshots[snapshot_id]
            )

            self.restores += 1
            self.last_restore_at = datetime.now(UTC).isoformat()

        return True

    def export_json(self):
        with self.lock:
            self.exports += 1

            return json.dumps(
                self.states,
                indent=4,
                ensure_ascii=False
            )

    def import_json(
        self,
        json_data
    ):
        try:
            data = json.loads(
                json_data
            )

            if not isinstance(data, dict):
                self.last_error = "Imported JSON must be a dictionary"
                return False

            with self.lock:
                self.states = data
                self.imports += 1
                self.last_write_at = datetime.now(UTC).isoformat()

            return True

        except Exception as error:
            self.last_error = str(error)
            self.health = 50
            return False

    def health_check(self):
        if not isinstance(
            self.states,
            dict
        ):
            self.health = 0
            self.status = "ERROR"
            self.lifecycle["healthy"] = False
            self.last_error = "States object is invalid"
        else:
            self.health = 100
            self.lifecycle["healthy"] = True
            self.last_error = None

        return self.get_health()

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
        state_count = sum(
            len(namespace_data)
            for namespace_data in self.states.values()
        )

        return {
            "namespace_count": len(self.states),
            "state_count": state_count,
            "snapshot_count": len(self.snapshots),
            "reads": self.reads,
            "writes": self.writes,
            "updates": self.updates,
            "deletes": self.deletes,
            "snapshots_created": self.snapshots_created,
            "restores": self.restores,
            "exports": self.exports,
            "imports": self.imports,
            "last_read_at": self.last_read_at,
            "last_write_at": self.last_write_at,
            "last_snapshot_at": self.last_snapshot_at,
            "last_restore_at": self.last_restore_at
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
    state = StateManager()

    state.initialize()
    state.start()

    state.set(
        namespace="system",
        key="mode",
        value="NORMAL"
    )

    state.set(
        namespace="system",
        key="booted",
        value=True
    )

    state.set(
        namespace="vision",
        key="faces_detected",
        value=2
    )

    state.increment(
        namespace="vision",
        key="frames_processed",
        amount=1
    )

    state.toggle(
        namespace="voice",
        key="listening"
    )

    snapshot_id = state.snapshot(
        "test_snapshot"
    )

    state.set(
        namespace="system",
        key="mode",
        value="SAFE_MODE"
    )

    state.restore(
        snapshot_id
    )

    exported = state.export_json()

    print("=== STATE MANAGER TEST ===")
    print()
    print("System:")
    print(
        state.get_namespace("system")
    )

    print()
    print("Vision:")
    print(
        state.get_namespace("vision")
    )

    print()
    print("Export:")
    print(exported)

    print()
    print("Status:")
    print(
        state.get_status()
    )