from core.base_manager import BaseManager
import json
import uuid
from copy import deepcopy
from datetime import datetime, UTC
from threading import Lock


class TaskManager(BaseManager):

    COMPONENT_ID = "core.task_manager"
    MANAGER_ID = "core.task_manager"
    NAME = "Task Manager"
    PRIORITY = 40
    AUTO_START = True

    VERSION = "0.1.0"

    PRIORITY_LOW = 25
    PRIORITY_NORMAL = 50
    PRIORITY_HIGH = 75
    PRIORITY_CRITICAL = 100

    VALID_STATUSES = [
        "CREATED",
        "QUEUED",
        "RUNNING",
        "PAUSED",
        "FINISHED",
        "FAILED",
        "CANCELLED"
    ]

    FINAL_STATUSES = [
        "FINISHED",
        "FAILED",
        "CANCELLED"
    ]

    def __init__(
        self,
        event_bus=None,
        logger=None,
        registry=None
    ):
        BaseManager.__init__(self)
        self.name = "Task Manager"
        self.component_id = "core.task_manager"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Verwaltet den Lebenszyklus von Aufgaben innerhalb "
            "von J.A.R.V.I.S. ohne Fachlogik."
        )

        self.event_bus = event_bus
        self.logger = logger
        self.registry = registry

        self.status = "OFFLINE"
        self.health = 0

        self.tasks = {}
        self.history = []
        self.snapshots = {}

        self.lock = Lock()

        self.tasks_created = 0
        self.tasks_queued = 0
        self.tasks_started = 0
        self.tasks_paused = 0
        self.tasks_resumed = 0
        self.tasks_finished = 0
        self.tasks_failed = 0
        self.tasks_cancelled = 0
        self.tasks_deleted = 0
        self.progress_updates = 0
        self.snapshots_created = 0
        self.restores = 0
        self.exports = 0
        self.imports = 0

        self.last_task_at = None
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
            "task_create",
            "task_queue",
            "task_start",
            "task_pause",
            "task_resume",
            "task_finish",
            "task_fail",
            "task_cancel",
            "task_delete",
            "task_progress",
            "task_result",
            "task_error",
            "task_query",
            "task_history",
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

    def create_task(
        self,
        name,
        namespace="system",
        component=None,
        priority=PRIORITY_NORMAL,
        metadata=None,
        queued=False
    ):
        if metadata is None:
            metadata = {}

        task_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()

        status = "QUEUED" if queued else "CREATED"

        task = {
            "task_id": task_id,
            "name": name,
            "namespace": namespace,
            "component": component,
            "status": status,
            "priority": priority,
            "progress": 0,
            "created_at": timestamp,
            "queued_at": timestamp if queued else None,
            "started_at": None,
            "paused_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
            "metadata": metadata
        }

        with self.lock:
            self.tasks[task_id] = task
            self.tasks_created += 1

            if queued:
                self.tasks_queued += 1

            self.last_task_at = timestamp

        self._record_history(
            task_id=task_id,
            action="TASK_CREATED",
            status=status
        )

        self._emit_event(
            event_type="TASK_CREATED",
            task=task
        )

        return task_id

    def queue_task(
        self,
        task_id
    ):
        return self._change_status(
            task_id=task_id,
            new_status="QUEUED",
            action="TASK_QUEUED",
            timestamp_field="queued_at",
            counter_name="tasks_queued"
        )

    def start_task(
        self,
        task_id
    ):
        return self._change_status(
            task_id=task_id,
            new_status="RUNNING",
            action="TASK_STARTED",
            timestamp_field="started_at",
            counter_name="tasks_started"
        )

    def pause_task(
        self,
        task_id
    ):
        return self._change_status(
            task_id=task_id,
            new_status="PAUSED",
            action="TASK_PAUSED",
            timestamp_field="paused_at",
            counter_name="tasks_paused"
        )

    def resume_task(
        self,
        task_id
    ):
        return self._change_status(
            task_id=task_id,
            new_status="RUNNING",
            action="TASK_RESUMED",
            counter_name="tasks_resumed"
        )

    def finish_task(
        self,
        task_id,
        result=None
    ):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task["status"] = "FINISHED"
            task["progress"] = 100
            task["result"] = result
            task["finished_at"] = datetime.now(UTC).isoformat()

            self.tasks_finished += 1
            self.last_task_at = task["finished_at"]

            task_copy = deepcopy(task)

        self._record_history(
            task_id=task_id,
            action="TASK_FINISHED",
            status="FINISHED"
        )

        self._emit_event(
            event_type="TASK_FINISHED",
            task=task_copy
        )

        return True

    def fail_task(
        self,
        task_id,
        error
    ):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task["status"] = "FAILED"
            task["error"] = str(error)
            task["finished_at"] = datetime.now(UTC).isoformat()

            self.tasks_failed += 1
            self.last_error = str(error)
            self.last_task_at = task["finished_at"]

            task_copy = deepcopy(task)

        self._record_history(
            task_id=task_id,
            action="TASK_FAILED",
            status="FAILED"
        )

        self._emit_event(
            event_type="TASK_FAILED",
            task=task_copy
        )

        return True

    def cancel_task(
        self,
        task_id,
        reason=None
    ):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task["status"] = "CANCELLED"
            task["error"] = reason
            task["finished_at"] = datetime.now(UTC).isoformat()

            self.tasks_cancelled += 1
            self.last_task_at = task["finished_at"]

            task_copy = deepcopy(task)

        self._record_history(
            task_id=task_id,
            action="TASK_CANCELLED",
            status="CANCELLED"
        )

        self._emit_event(
            event_type="TASK_CANCELLED",
            task=task_copy
        )

        return True

    def update_progress(
        self,
        task_id,
        progress
    ):
        progress = max(
            0,
            min(
                100,
                progress
            )
        )

        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task["progress"] = progress
            self.progress_updates += 1
            self.last_task_at = datetime.now(UTC).isoformat()

            task_copy = deepcopy(task)

        self._record_history(
            task_id=task_id,
            action="TASK_PROGRESS",
            status=task_copy["status"]
        )

        self._emit_event(
            event_type="TASK_PROGRESS",
            task=task_copy
        )

        return True

    def set_result(
        self,
        task_id,
        result
    ):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task["result"] = result
            self.last_task_at = datetime.now(UTC).isoformat()

        return True

    def set_error(
        self,
        task_id,
        error
    ):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task["error"] = str(error)
            self.last_error = str(error)
            self.last_task_at = datetime.now(UTC).isoformat()

        return True

    def delete_task(
        self,
        task_id
    ):
        with self.lock:
            if task_id not in self.tasks:
                return False

            del self.tasks[task_id]
            self.tasks_deleted += 1
            self.last_task_at = datetime.now(UTC).isoformat()

        self._record_history(
            task_id=task_id,
            action="TASK_DELETED",
            status="DELETED"
        )

        self._emit_event(
            event_type="TASK_DELETED",
            task={
                "task_id": task_id
            }
        )

        return True

    def clear_finished(self):
        with self.lock:
            finished_ids = [
                task_id
                for task_id, task in self.tasks.items()
                if task["status"] in self.FINAL_STATUSES
            ]

            for task_id in finished_ids:
                del self.tasks[task_id]
                self.tasks_deleted += 1

        return len(finished_ids)

    def get_task(
        self,
        task_id
    ):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return None

            return deepcopy(task)

    def get_all_tasks(self):
        with self.lock:
            return deepcopy(self.tasks)

    def get_tasks_by_status(
        self,
        status
    ):
        with self.lock:
            return {
                task_id: deepcopy(task)
                for task_id, task in self.tasks.items()
                if task["status"] == status
            }

    def get_running_tasks(self):
        return self.get_tasks_by_status(
            "RUNNING"
        )

    def get_finished_tasks(self):
        with self.lock:
            return {
                task_id: deepcopy(task)
                for task_id, task in self.tasks.items()
                if task["status"] in self.FINAL_STATUSES
            }

    def get_tasks_by_namespace(
        self,
        namespace
    ):
        with self.lock:
            return {
                task_id: deepcopy(task)
                for task_id, task in self.tasks.items()
                if task["namespace"] == namespace
            }

    def snapshot(
        self,
        snapshot_id=None
    ):
        if snapshot_id is None:
            snapshot_id = datetime.now(UTC).strftime(
                "%Y%m%d_%H%M%S"
            )

        with self.lock:
            self.snapshots[snapshot_id] = {
                "tasks": deepcopy(self.tasks),
                "history": deepcopy(self.history)
            }

            self.snapshots_created += 1

        return snapshot_id

    def restore(
        self,
        snapshot_id
    ):
        with self.lock:
            if snapshot_id not in self.snapshots:
                return False

            snapshot_data = self.snapshots[snapshot_id]

            self.tasks = deepcopy(
                snapshot_data["tasks"]
            )

            self.history = deepcopy(
                snapshot_data["history"]
            )

            self.restores += 1

        return True

    def export_json(self):
        with self.lock:
            self.exports += 1

            return json.dumps(
                {
                    "tasks": self.tasks,
                    "history": self.history
                },
                indent=4,
                ensure_ascii=False
            )

    def import_json(
        self,
        json_data
    ):
        try:
            data = json.loads(json_data)

            if not isinstance(data, dict):
                self.last_error = "Imported JSON must be a dictionary"
                return False

            with self.lock:
                self.tasks = data.get("tasks", {})
                self.history = data.get("history", [])
                self.imports += 1

            return True

        except Exception as error:
            self.last_error = str(error)
            self.health = 50
            return False

    def health_check(self):
        if not isinstance(self.tasks, dict):
            self.status = "ERROR"
            self.health = 0
            self.lifecycle["healthy"] = False
            self.last_error = "Tasks object is invalid"

        elif not isinstance(self.history, list):
            self.status = "ERROR"
            self.health = 0
            self.lifecycle["healthy"] = False
            self.last_error = "History object is invalid"

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
        with self.lock:
            active_tasks = len(
                [
                    task
                    for task in self.tasks.values()
                    if task["status"] not in self.FINAL_STATUSES
                ]
            )

            finished_tasks = len(
                [
                    task
                    for task in self.tasks.values()
                    if task["status"] in self.FINAL_STATUSES
                ]
            )

            return {
                "task_count": len(self.tasks),
                "active_tasks": active_tasks,
                "finished_tasks": finished_tasks,
                "history_count": len(self.history),
                "snapshot_count": len(self.snapshots),
                "tasks_created": self.tasks_created,
                "tasks_queued": self.tasks_queued,
                "tasks_started": self.tasks_started,
                "tasks_paused": self.tasks_paused,
                "tasks_resumed": self.tasks_resumed,
                "tasks_finished": self.tasks_finished,
                "tasks_failed": self.tasks_failed,
                "tasks_cancelled": self.tasks_cancelled,
                "tasks_deleted": self.tasks_deleted,
                "progress_updates": self.progress_updates,
                "snapshots_created": self.snapshots_created,
                "restores": self.restores,
                "exports": self.exports,
                "imports": self.imports,
                "last_task_at": self.last_task_at
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

    def _change_status(
        self,
        task_id,
        new_status,
        action,
        timestamp_field=None,
        counter_name=None
    ):
        if new_status not in self.VALID_STATUSES:
            self.last_error = f"Invalid task status: {new_status}"
            return False

        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            if task["status"] in self.FINAL_STATUSES:
                return False

            task["status"] = new_status

            if timestamp_field:
                task[timestamp_field] = datetime.now(UTC).isoformat()

            if counter_name:
                setattr(
                    self,
                    counter_name,
                    getattr(self, counter_name) + 1
                )

            self.last_task_at = datetime.now(UTC).isoformat()
            task_copy = deepcopy(task)

        self._record_history(
            task_id=task_id,
            action=action,
            status=new_status
        )

        self._emit_event(
            event_type=action,
            task=task_copy
        )

        return True

    def _record_history(
        self,
        task_id,
        action,
        status
    ):
        with self.lock:
            self.history.append(
                {
                    "task_id": task_id,
                    "action": action,
                    "status": status,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        return True

    def _emit_event(
        self,
        event_type,
        task
    ):
        if self.event_bus is not None:
            self.event_bus.publish(
                event_type=event_type,
                payload={
                    "task": deepcopy(task)
                },
                source=self.component_id,
                severity="INFO"
            )

        if self.logger is not None:
            self.logger.info(
                message=event_type,
                source=self.component_id,
                payload={
                    "task_id": task.get("task_id")
                }
            )

        return True


if __name__ == "__main__":
    task_manager = TaskManager()

    task_manager.initialize()
    task_manager.start()

    task_id = task_manager.create_task(
        name="Test Task",
        namespace="system",
        component="TaskManagerTest",
        priority=TaskManager.PRIORITY_HIGH,
        metadata={
            "purpose": "Kernel test"
        },
        queued=True
    )

    task_manager.start_task(task_id)
    task_manager.update_progress(task_id, 25)
    task_manager.update_progress(task_id, 75)
    task_manager.finish_task(
        task_id,
        result={
            "message": "Task erfolgreich abgeschlossen"
        }
    )

    snapshot_id = task_manager.snapshot(
        "test_snapshot"
    )

    exported = task_manager.export_json()

    print("=== TASK MANAGER TEST ===")
    print()
    print("Task:")
    print(
        task_manager.get_task(task_id)
    )

    print()
    print("Snapshot:")
    print(snapshot_id)

    print()
    print("Export:")
    print(exported)

    print()
    print("Status:")
    print(
        task_manager.get_status()
    )