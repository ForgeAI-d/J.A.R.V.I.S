from copy import deepcopy
from datetime import datetime, UTC
from threading import RLock
from uuid import uuid4


class ConfigTransaction:

    VERSION = "1.0.0"

    STATUS_PENDING = "PENDING"
    STATUS_COMMITTED = "COMMITTED"
    STATUS_ROLLED_BACK = "ROLLED_BACK"
    STATUS_FAILED = "FAILED"

    def __init__(
        self,
        config_manager=None,
        name=None
    ):
        # -------------------------------------------------
        # Identity
        # -------------------------------------------------

        self.name = name or "Config Transaction"
        self.component_id = "core.config_transaction"
        self.transaction_id = str(uuid4())
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Bündelt mehrere Konfigurationsänderungen "
            "zu einer atomaren Transaktion."
        )

        # -------------------------------------------------
        # Connections
        # -------------------------------------------------

        self.config_manager = config_manager

        # -------------------------------------------------
        # Runtime
        # -------------------------------------------------

        self.status = self.STATUS_PENDING
        self.health = 100

        self.original_values = {}
        self.pending_changes = {}
        self.applied_changes = []

        self.lock = RLock()

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        self.read_count = 0
        self.write_count = 0
        self.delete_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.failed_operations = 0

        # -------------------------------------------------
        # Runtime Information
        # -------------------------------------------------

        self.created_at = datetime.now(UTC).isoformat()
        self.committed_at = None
        self.rolled_back_at = None
        self.last_error = None

        self.timeline = []

        # -------------------------------------------------
        # Capabilities
        # -------------------------------------------------

        self.capabilities = [
            "transaction_get",
            "transaction_set",
            "transaction_update",
            "transaction_delete",
            "transaction_commit",
            "transaction_rollback",
            "transaction_preview",
            "atomic_config_update",
            "thread_safe_access"
        ]

    # =====================================================
    # Public API
    # =====================================================

    def get(
        self,
        namespace,
        key=None,
        default=None
    ):
        if not self._is_pending():
            return deepcopy(default)

        with self.lock:
            self.read_count += 1

            namespace_data = self._get_effective_namespace(
                namespace
            )

            if key is None:
                return deepcopy(namespace_data)

            return deepcopy(
                namespace_data.get(
                    key,
                    default
                )
            )

    def set(
        self,
        namespace,
        key,
        value
    ):
        if not self._is_pending():
            return False

        if not self._ensure_namespace_snapshot(namespace):
            return False

        with self.lock:
            namespace_changes = self.pending_changes.setdefault(
                namespace,
                {}
            )

            namespace_changes[key] = {
                "operation": "SET",
                "value": deepcopy(value)
            }

            self.write_count += 1

        self.add_timeline_event(
            event_type="TRANSACTION_VALUE_SET",
            payload={
                "namespace": namespace,
                "key": key
            }
        )

        return True

    def update(
        self,
        namespace,
        values
    ):
        if not isinstance(values, dict):
            return self._set_error(
                "Transaction update values must be a dictionary."
            )

        success = True

        for key, value in values.items():
            if not self.set(
                namespace=namespace,
                key=key,
                value=value
            ):
                success = False

        return success

    def delete(
        self,
        namespace,
        key
    ):
        if not self._is_pending():
            return False

        if not self._ensure_namespace_snapshot(namespace):
            return False

        effective = self._get_effective_namespace(namespace)

        if key not in effective:
            return False

        with self.lock:
            namespace_changes = self.pending_changes.setdefault(
                namespace,
                {}
            )

            namespace_changes[key] = {
                "operation": "DELETE"
            }

            self.delete_count += 1

        self.add_timeline_event(
            event_type="TRANSACTION_VALUE_DELETED",
            payload={
                "namespace": namespace,
                "key": key
            }
        )

        return True

    def commit(self):
        if not self._is_pending():
            return False

        if self.config_manager is None:
            return self._fail(
                "No ConfigManager connected."
            )

        namespaces = self.list_changed_namespaces()

        try:
            for namespace in namespaces:
                final_config = self._get_effective_namespace(
                    namespace
                )

                validation = self.config_manager.validator.validate(
                    namespace=namespace,
                    config=final_config
                )

                valid, validated_config = validation

                if not valid:
                    report = self.config_manager.validator.get_report()

                    return self._fail(
                        (
                            f"Validation failed for '{namespace}': "
                            f"{report['errors']}"
                        )
                    )

                self.pending_changes[namespace][
                    "__validated_config__"
                ] = {
                    "operation": "INTERNAL",
                    "value": deepcopy(validated_config)
                }

            for namespace in namespaces:
                validated_config = self.pending_changes[
                    namespace
                ].pop(
                    "__validated_config__"
                )["value"]

                self.config_manager.cache.set(
                    namespace=namespace,
                    value=validated_config
                )

                saved = self.config_manager.save(
                    namespace=namespace,
                    create_backup=True
                )

                if not saved:
                    raise RuntimeError(
                        f"Could not save namespace '{namespace}'."
                    )

                self.applied_changes.append(namespace)

            with self.lock:
                self.status = self.STATUS_COMMITTED
                self.committed_at = datetime.now(UTC).isoformat()
                self.commit_count += 1
                self.last_error = None

            self.add_timeline_event(
                event_type="TRANSACTION_COMMITTED",
                payload={
                    "namespaces": namespaces
                }
            )

            return True

        except Exception as error:
            self._restore_original_values()

            return self._fail(error)

    def rollback(self):
        if self.status == self.STATUS_COMMITTED:
            return self._set_error(
                "Committed transaction cannot be rolled back."
            )

        if self.status == self.STATUS_ROLLED_BACK:
            return True

        with self.lock:
            self.pending_changes = {}
            self.status = self.STATUS_ROLLED_BACK
            self.rolled_back_at = datetime.now(UTC).isoformat()
            self.rollback_count += 1
            self.last_error = None

        self.add_timeline_event(
            "TRANSACTION_ROLLED_BACK"
        )

        return True

    # =====================================================
    # Preview and Information
    # =====================================================

    def preview(self):
        result = {}

        for namespace in self.list_changed_namespaces():
            result[namespace] = {
                "before": deepcopy(
                    self.original_values.get(
                        namespace,
                        {}
                    )
                ),
                "after": self._get_effective_namespace(
                    namespace
                ),
                "changes": deepcopy(
                    self.pending_changes.get(
                        namespace,
                        {}
                    )
                )
            }

        return result

    def list_changed_namespaces(self):
        with self.lock:
            return sorted(
                self.pending_changes.keys()
            )

    def has_changes(self):
        with self.lock:
            return bool(
                self.pending_changes
            )

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "transaction_id": self.transaction_id,
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
                "read_count": self.read_count,
                "write_count": self.write_count,
                "delete_count": self.delete_count,
                "commit_count": self.commit_count,
                "rollback_count": self.rollback_count,
                "failed_operations": self.failed_operations,
                "changed_namespaces": sorted(
                    self.pending_changes.keys()
                ),
                "applied_changes": deepcopy(
                    self.applied_changes
                ),
                "timeline_count": len(self.timeline),
                "created_at": self.created_at,
                "committed_at": self.committed_at,
                "rolled_back_at": self.rolled_back_at
            }

    def get_status(self):
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "has_changes": self.has_changes(),
            "statistics": self.get_statistics(),
            "last_error": self.last_error
        }

    # =====================================================
    # Internal Helpers
    # =====================================================

    def _ensure_namespace_snapshot(
        self,
        namespace
    ):
        if self.config_manager is None:
            return self._set_error(
                "No ConfigManager connected."
            )

        with self.lock:
            if namespace in self.original_values:
                return True

        original = self.config_manager.get(
            namespace
        )

        if original is None:
            return self._set_error(
                f"Could not load namespace '{namespace}'."
            )

        with self.lock:
            self.original_values[namespace] = deepcopy(
                original
            )

        return True

    def _get_effective_namespace(
        self,
        namespace
    ):
        if namespace in self.original_values:
            result = deepcopy(
                self.original_values[namespace]
            )

        elif self.config_manager is not None:
            result = self.config_manager.get(
                namespace
            )

        else:
            result = {}

        changes = self.pending_changes.get(
            namespace,
            {}
        )

        for key, change in changes.items():
            if key == "__validated_config__":
                continue

            operation = change.get(
                "operation"
            )

            if operation == "SET":
                result[key] = deepcopy(
                    change.get("value")
                )

            elif operation == "DELETE":
                result.pop(
                    key,
                    None
                )

        return result

    def _restore_original_values(self):
        if self.config_manager is None:
            return False

        restored = True

        for namespace in self.applied_changes:
            original = self.original_values.get(
                namespace
            )

            if original is None:
                continue

            self.config_manager.cache.set(
                namespace=namespace,
                value=original
            )

            if not self.config_manager.save(
                namespace=namespace,
                create_backup=False
            ):
                restored = False

        return restored

    def _is_pending(self):
        return self.status == self.STATUS_PENDING

    def _fail(
        self,
        error
    ):
        with self.lock:
            self.status = self.STATUS_FAILED
            self.health = 0
            self.failed_operations += 1
            self.last_error = str(error)

        self.add_timeline_event(
            event_type="TRANSACTION_FAILED",
            payload={
                "error": str(error)
            }
        )

        return False

    def _set_error(
        self,
        error
    ):
        with self.lock:
            self.last_error = str(error)
            self.failed_operations += 1

        self.add_timeline_event(
            event_type="TRANSACTION_ERROR",
            payload={
                "error": str(error)
            }
        )

        return False

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
                    "event_type": event_type,
                    "transaction_id": self.transaction_id,
                    "payload": deepcopy(payload),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        return True


if __name__ == "__main__":
    from core.config_manager import ConfigManager

    config = ConfigManager()
    config.initialize()
    config.start()

    transaction = ConfigTransaction(
        config_manager=config,
        name="Boot Mode Test"
    )

    transaction.set(
        namespace="boot",
        key="boot_mode",
        value="testing"
    )

    transaction.set(
        namespace="boot",
        key="safe_mode",
        value=True
    )

    print("=== CONFIG TRANSACTION TEST ===")
    print()

    print("Preview:")
    print(
        transaction.preview()
    )

    print()
    print("Commit:")
    print(
        transaction.commit()
    )

    print()
    print("Boot Config:")
    print(
        config.get("boot")
    )

    print()
    print("Transaction Status:")
    print(
        transaction.get_status()
    )