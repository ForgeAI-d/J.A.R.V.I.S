import os
import time
from copy import deepcopy
from datetime import datetime, UTC
from threading import Event, RLock, Thread, current_thread


class ConfigWatcher:

    VERSION = "1.0.0"

    def __init__(
        self,
        config_path="config",
        callback=None,
        poll_interval=1.0,
        logger=None
    ):
        # -------------------------------------------------
        # Identity
        # -------------------------------------------------

        self.name = "Config Watcher"
        self.component_id = "core.config_watcher"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Überwacht Konfigurationsdateien auf Änderungen "
            "und löst kontrollierte Reload-Ereignisse aus."
        )

        # -------------------------------------------------
        # Connections
        # -------------------------------------------------

        self.config_path = config_path
        self.callback = callback
        self.logger = logger

        # -------------------------------------------------
        # Runtime
        # -------------------------------------------------

        self.poll_interval = float(poll_interval)

        self.status = "OFFLINE"
        self.health = 0

        self.file_state = {}
        self.timeline = []

        self.lock = RLock()
        self.stop_event = Event()
        self.thread = None

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        self.scan_count = 0
        self.files_discovered = 0
        self.changes_detected = 0
        self.files_created = 0
        self.files_modified = 0
        self.files_deleted = 0
        self.callback_count = 0
        self.callback_errors = 0

        # -------------------------------------------------
        # Runtime Information
        # -------------------------------------------------

        self.created_at = datetime.now(UTC).isoformat()
        self.last_scan_at = None
        self.last_change_at = None
        self.last_started = None
        self.last_stopped = None
        self.last_error = None

        # -------------------------------------------------
        # Lifecycle
        # -------------------------------------------------

        self.lifecycle = {
            "initialized": False,
            "started": False,
            "healthy": False
        }

        # -------------------------------------------------
        # Capabilities
        # -------------------------------------------------

        self.capabilities = [
            "config_directory_watch",
            "config_change_detection",
            "config_create_detection",
            "config_modify_detection",
            "config_delete_detection",
            "callback_notification",
            "background_thread",
            "manual_scan",
            "thread_safe_access"
        ]

    # =====================================================
    # Lifecycle
    # =====================================================

    def initialize(self):
        try:
            os.makedirs(
                self.config_path,
                exist_ok=True
            )

            with self.lock:
                self.file_state = self._collect_file_state()
                self.files_discovered = len(self.file_state)

                self.lifecycle["initialized"] = True
                self.last_error = None

            self.add_timeline_event(
                event_type="CONFIG_WATCHER_INITIALIZED",
                payload={
                    "files_discovered": self.files_discovered
                }
            )

            return True

        except Exception as error:
            return self.set_error(error)

    def start(self):
        if self.lifecycle["started"]:
            return True

        if not self.lifecycle["initialized"]:
            if not self.initialize():
                return False

        if self.poll_interval <= 0:
            return self.set_error(
                "Poll interval must be greater than zero."
            )

        try:
            self.stop_event.clear()

            self.thread = Thread(
                target=self._watch_loop,
                name="ConfigWatcherThread",
                daemon=True
            )

            self.thread.start()

            with self.lock:
                self.status = "ONLINE"
                self.health = 100
                self.last_started = datetime.now(UTC).isoformat()
                self.last_error = None

                self.lifecycle["started"] = True
                self.lifecycle["healthy"] = True

            self.add_timeline_event(
                "CONFIG_WATCHER_STARTED"
            )

            return True

        except Exception as error:
            return self.set_error(error)

    def stop(self):
        if not self.lifecycle["started"]:
            return True

        self.stop_event.set()

        thread = self.thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not current_thread()
        ):
            thread.join(
                timeout=max(
                    1.0,
                    self.poll_interval * 2
                )
            )

        with self.lock:
            self.thread = None
            self.status = "OFFLINE"
            self.health = 0
            self.last_stopped = datetime.now(UTC).isoformat()

            self.lifecycle["started"] = False
            self.lifecycle["healthy"] = False

        self.add_timeline_event(
            "CONFIG_WATCHER_STOPPED"
        )

        return True

    # =====================================================
    # Watching
    # =====================================================

    def scan_once(self):
        try:
            current_state = self._collect_file_state()

            with self.lock:
                previous_state = deepcopy(
                    self.file_state
                )

            changes = self._compare_states(
                previous_state=previous_state,
                current_state=current_state
            )

            with self.lock:
                self.file_state = current_state
                self.scan_count += 1
                self.last_scan_at = datetime.now(UTC).isoformat()

            if changes:
                self._handle_changes(changes)

            return changes

        except Exception as error:
            self.set_error(
                error,
                critical=False
            )

            return []

    def _watch_loop(self):
        while not self.stop_event.is_set():
            self.scan_once()

            self.stop_event.wait(
                self.poll_interval
            )

    def _collect_file_state(self):
        state = {}

        if not os.path.exists(
            self.config_path
        ):
            return state

        for filename in os.listdir(
            self.config_path
        ):
            if not filename.endswith(".json"):
                continue

            path = os.path.join(
                self.config_path,
                filename
            )

            if not os.path.isfile(path):
                continue

            stat = os.stat(path)

            namespace = filename[:-5]

            state[namespace] = {
                "filename": filename,
                "path": path,
                "modified_ns": stat.st_mtime_ns,
                "size": stat.st_size
            }

        return state

    def _compare_states(
        self,
        previous_state,
        current_state
    ):
        changes = []

        previous_namespaces = set(
            previous_state.keys()
        )

        current_namespaces = set(
            current_state.keys()
        )

        created = (
            current_namespaces
            -
            previous_namespaces
        )

        deleted = (
            previous_namespaces
            -
            current_namespaces
        )

        existing = (
            previous_namespaces
            &
            current_namespaces
        )

        for namespace in sorted(created):
            changes.append(
                {
                    "change_type": "CREATED",
                    "namespace": namespace,
                    "current": deepcopy(
                        current_state[namespace]
                    ),
                    "previous": None,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        for namespace in sorted(deleted):
            changes.append(
                {
                    "change_type": "DELETED",
                    "namespace": namespace,
                    "current": None,
                    "previous": deepcopy(
                        previous_state[namespace]
                    ),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        for namespace in sorted(existing):
            previous = previous_state[namespace]
            current = current_state[namespace]

            modified = (
                previous["modified_ns"]
                != current["modified_ns"]
                or previous["size"]
                != current["size"]
            )

            if modified:
                changes.append(
                    {
                        "change_type": "MODIFIED",
                        "namespace": namespace,
                        "current": deepcopy(current),
                        "previous": deepcopy(previous),
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                )

        return changes

    def _handle_changes(
        self,
        changes
    ):
        for change in changes:
            change_type = change["change_type"]

            with self.lock:
                self.changes_detected += 1
                self.last_change_at = change["timestamp"]

                if change_type == "CREATED":
                    self.files_created += 1

                elif change_type == "MODIFIED":
                    self.files_modified += 1

                elif change_type == "DELETED":
                    self.files_deleted += 1

            self.add_timeline_event(
                event_type=f"CONFIG_FILE_{change_type}",
                payload=change
            )

            self._notify_callback(change)

        return True

    def _notify_callback(
        self,
        change
    ):
        if self.callback is None:
            return False

        try:
            self.callback(
                deepcopy(change)
            )

            with self.lock:
                self.callback_count += 1

            return True

        except Exception as error:
            with self.lock:
                self.callback_errors += 1
                self.last_error = str(error)

            self.add_timeline_event(
                event_type="CONFIG_WATCHER_CALLBACK_ERROR",
                payload={
                    "error": str(error),
                    "change": change
                }
            )

            self._log(
                level="error",
                message=str(error),
                payload={
                    "change": change
                }
            )

            return False

    # =====================================================
    # Public API
    # =====================================================

    def set_callback(
        self,
        callback
    ):
        if callback is not None and not callable(callback):
            self.last_error = "Callback must be callable or None."
            return False

        with self.lock:
            self.callback = callback
            self.last_error = None

        return True

    def set_poll_interval(
        self,
        poll_interval
    ):
        try:
            poll_interval = float(
                poll_interval
            )

            if poll_interval <= 0:
                self.last_error = (
                    "Poll interval must be greater than zero."
                )
                return False

        except (TypeError, ValueError):
            self.last_error = (
                "Poll interval must be numeric."
            )
            return False

        with self.lock:
            self.poll_interval = poll_interval
            self.last_error = None

        return True

    def refresh_baseline(self):
        try:
            state = self._collect_file_state()

            with self.lock:
                self.file_state = state
                self.files_discovered = len(state)
                self.last_error = None

            self.add_timeline_event(
                event_type="CONFIG_WATCHER_BASELINE_REFRESHED",
                payload={
                    "files_discovered": len(state)
                }
            )

            return True

        except Exception as error:
            return self.set_error(
                error,
                critical=False
            )

    def list_watched_namespaces(self):
        with self.lock:
            return sorted(
                self.file_state.keys()
            )

    # =====================================================
    # Information
    # =====================================================

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "mission": self.mission,
            "capabilities": deepcopy(
                self.capabilities
            )
        }

    def get_statistics(self):
        with self.lock:
            return {
                "scan_count": self.scan_count,
                "files_discovered": self.files_discovered,
                "changes_detected": self.changes_detected,
                "files_created": self.files_created,
                "files_modified": self.files_modified,
                "files_deleted": self.files_deleted,
                "callback_count": self.callback_count,
                "callback_errors": self.callback_errors,
                "poll_interval": self.poll_interval,
                "watched_namespaces": sorted(
                    self.file_state.keys()
                ),
                "timeline_count": len(self.timeline),
                "created_at": self.created_at,
                "last_scan_at": self.last_scan_at,
                "last_change_at": self.last_change_at
            }

    def get_status(self):
        thread_alive = (
            self.thread is not None
            and self.thread.is_alive()
        )

        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": deepcopy(
                self.lifecycle
            ),
            "thread_alive": thread_alive,
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

    # =====================================================
    # Timeline and Errors
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
                    "event_type": event_type,
                    "component_id": self.component_id,
                    "payload": deepcopy(payload),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        return True

    def set_error(
        self,
        error,
        critical=True
    ):
        with self.lock:
            self.last_error = str(error)

            if critical:
                self.status = "ERROR"
                self.health = 0
                self.lifecycle["healthy"] = False
            else:
                self.health = min(
                    self.health,
                    50
                )

        self.add_timeline_event(
            event_type="CONFIG_WATCHER_ERROR",
            payload={
                "error": str(error),
                "critical": critical
            }
        )

        self._log(
            level="error",
            message=str(error)
        )

        return False

    def _log(
        self,
        level,
        message,
        payload=None
    ):
        if self.logger is None:
            return False

        if payload is None:
            payload = {}

        log_method = getattr(
            self.logger,
            level,
            None
        )

        if log_method is None:
            return False

        log_method(
            message=message,
            source=self.component_id,
            payload=payload
        )

        return True


if __name__ == "__main__":

    def test_callback(change):
        print()
        print("Änderung erkannt:")
        print(change)

    watcher = ConfigWatcher(
        config_path="config",
        callback=test_callback,
        poll_interval=1.0
    )

    watcher.initialize()

    print("=== CONFIG WATCHER TEST ===")
    print()

    print("Überwachte Namespaces:")
    print(
        watcher.list_watched_namespaces()
    )

    print()
    print(
        "Ändere jetzt innerhalb von zehn Sekunden "
        "eine Datei unter config/."
    )

    watcher.start()

    try:
        time.sleep(10)
    finally:
        watcher.stop()

    print()
    print("Status:")
    print(
        watcher.get_status()
    )