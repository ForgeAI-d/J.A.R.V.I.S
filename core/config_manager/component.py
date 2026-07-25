from core.base_manager import BaseManager
import json
import os
import shutil
from copy import deepcopy
from datetime import datetime, UTC
from threading import RLock

from .internals import (
    CONFIG_VERSION,
    DEFAULT_CONFIGS,
    ConfigCache,
    ConfigEvents,
    ConfigMigrator,
    ConfigSourceResolver,
    ConfigStorage,
    ConfigTransaction,
    ConfigValidator,
    ConfigWatcher,
    build_typed_config,
)


class ConfigManager(BaseManager):

    COMPONENT_ID = "core.config_manager"
    MANAGER_ID = "core.config_manager"
    NAME = "Config Manager"
    PRIORITY = 10
    AUTO_START = True

    VERSION = "1.0.0-alpha"

    def __init__(
        self,
        config_path="config",
        backup_path="backups/config",
        cache_ttl=None,
        cache_max_entries=1000,
        watcher_enabled=True,
        watcher_poll_interval=1.0,
        event_bus=None,
        logger=None
    ):
        BaseManager.__init__(self)
        # -------------------------------------------------
        # Identity
        # -------------------------------------------------

        self.name = "Config Manager"
        self.component_id = "core.config_manager"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Zentrale, selbstverwaltende Konfigurationsverwaltung "
            "für den J.A.R.V.I.S.-Kernel."
        )

        # -------------------------------------------------
        # Optional Kernel Connections
        # -------------------------------------------------

        self.event_bus = event_bus
        self.logger = logger

        # -------------------------------------------------
        # Config Subsystem
        # -------------------------------------------------

        self.storage = ConfigStorage(
            config_path=config_path,
            backup_path=backup_path
        )

        self.validator = ConfigValidator()
        self.migrator = ConfigMigrator()

        self.cache = ConfigCache(
            default_ttl=cache_ttl,
            max_entries=cache_max_entries
        )

        self.events = ConfigEvents(
            event_bus=event_bus,
            logger=logger
        )

        self.watcher = ConfigWatcher(
            config_path=config_path,
            callback=self._handle_watcher_change,
            poll_interval=watcher_poll_interval,
            logger=logger
        )

        self.watcher_enabled = bool(watcher_enabled)
        self.sources = ConfigSourceResolver()

        self.config_path = config_path
        self.backup_path = backup_path

        # -------------------------------------------------
        # Runtime
        # -------------------------------------------------

        self.status = "OFFLINE"
        self.health = 0
        self.lock = RLock()

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        self.files_created = 0
        self.files_loaded = 0
        self.files_saved = 0
        self.files_reloaded = 0

        self.validations_run = 0
        self.validation_errors = 0
        self.defaults_added = 0

        self.migrations_run = 0
        self.backups_created = 0
        self.restores_completed = 0

        self.values_read = 0
        self.values_written = 0
        self.values_deleted = 0

        self.exports_created = 0
        self.imports_completed = 0

        self.transactions_created = 0
        self.watcher_reloads = 0
        self.recovered_config_files = 0

        # -------------------------------------------------
        # Runtime Information
        # -------------------------------------------------

        self.created_at = datetime.now(UTC).isoformat()

        self.last_loaded_at = None
        self.last_saved_at = None
        self.last_validation_at = None
        self.last_migration_at = None
        self.last_backup_at = None
        self.last_restore_at = None
        self.last_watcher_change_at = None
        self.last_started = None
        self.last_stopped = None
        self.last_error = None

        # -------------------------------------------------
        # Lifecycle
        # -------------------------------------------------

        self.lifecycle = {
            "registered": False,
            "dependencies_resolved": True,
            "initialized": False,
            "started": False,
            "healthy": False
        }

        # -------------------------------------------------
        # Capabilities
        # -------------------------------------------------

        self.capabilities = [
            "config_auto_create",
            "config_load",
            "config_reload",
            "config_save",
            "config_get",
            "config_set",
            "config_update",
            "config_delete",
            "config_validation",
            "config_migration",
            "config_reset",
            "config_backup",
            "config_restore",
            "config_export",
            "config_import",
            "config_cache",
            "config_cache_ttl",
            "config_cache_lru",
            "config_cache_statistics",
            "config_events",
            "config_transactions",
            "config_watcher",
            "config_live_reload",
            "config_file_recovery",
            "config_versioning",
            "thread_safe_access",
            "event_bus_compatible",
            "logger_compatible"
        ]

        self.timeline = []

    # =====================================================
    # Lifecycle
    # =====================================================

    def initialize(self):
        try:
            os.makedirs(
                self.config_path,
                exist_ok=True
            )

            os.makedirs(
                self.backup_path,
                exist_ok=True
            )

            self.ensure_default_configs()

            if not self.watcher.initialize():
                raise RuntimeError(
                    self.watcher.last_error
                    or "ConfigWatcher konnte nicht initialisiert werden."
                )

            with self.lock:
                self.lifecycle["initialized"] = True
                self.last_error = None

            self.add_timeline_event(
                "CONFIG_MANAGER_INITIALIZED"
            )

            return True

        except Exception as error:
            return self.set_error(error)

    def start(self):
        if not self.lifecycle["initialized"]:
            if not self.initialize():
                return False

        try:
            self.reload_all()

            if self.watcher_enabled:
                self.watcher.refresh_baseline()

                if not self.watcher.start():
                    raise RuntimeError(
                        self.watcher.last_error
                        or "ConfigWatcher konnte nicht gestartet werden."
                    )

            with self.lock:
                self.status = "ONLINE"
                self.health = 100
                self.last_started = datetime.now(UTC).isoformat()
                self.last_error = None

                self.lifecycle["started"] = True
                self.lifecycle["healthy"] = True

            self.add_timeline_event(
                "CONFIG_MANAGER_STARTED"
            )

            self.events.publish(
                event_name="CONFIG_MANAGER_STARTED",
                payload={
                    "namespaces": self.list_namespaces(),
                    "watcher_enabled": self.watcher_enabled
                }
            )

            return True

        except Exception as error:
            return self.set_error(error)

    def stop(self):
        try:
            if self.watcher.lifecycle["started"]:
                self.watcher.stop()

            self.save_all()

            with self.lock:
                self.status = "OFFLINE"
                self.health = 0
                self.last_stopped = datetime.now(UTC).isoformat()

                self.lifecycle["started"] = False
                self.lifecycle["healthy"] = False

            self.add_timeline_event(
                "CONFIG_MANAGER_STOPPED"
            )

            self.events.publish(
                event_name="CONFIG_MANAGER_STOPPED",
                payload={}
            )

            return True

        except Exception as error:
            return self.set_error(error)

    # =====================================================
    # Environment Creation
    # =====================================================

    def ensure_default_configs(self):
        for namespace, defaults in DEFAULT_CONFIGS.items():
            if self.storage.exists(namespace):
                continue

            success = self.storage.save(
                namespace=namespace,
                data=deepcopy(defaults),
                create_backup=False
            )

            if success:
                with self.lock:
                    self.files_created += 1

                self.add_timeline_event(
                    event_type="CONFIG_CREATED",
                    payload={
                        "namespace": namespace
                    }
                )

                self.events.config_created(
                    namespace
                )

        return True

    # =====================================================
    # Loading
    # =====================================================

    def load(
        self,
        namespace,
        use_cache=True
    ):
        if use_cache and self.cache.has(namespace):
            return self.cache.get(
                namespace,
                default={}
            )

        defaults = deepcopy(
            DEFAULT_CONFIGS.get(
                namespace,
                {}
            )
        )

        if namespace not in DEFAULT_CONFIGS:
            self.set_error(
                f"Unbekannter Konfigurations-Namespace: {namespace}",
                critical=False
            )

            return defaults

        try:
            config = self.storage.load(
                namespace=namespace,
                default=defaults
            )

            migrated_config, migration_report = self.migrator.migrate(
                namespace=namespace,
                config=config,
                target_version=CONFIG_VERSION
            )

            valid, validated_config = self.validator.validate(
                namespace=namespace,
                config=migrated_config
            )

            validator_report = self.validator.get_report()

            with self.lock:
                self.validations_run += 1
                self.last_validation_at = datetime.now(UTC).isoformat()

                self.defaults_added += len(
                    validator_report["changes"]
                )

                if not valid:
                    self.validation_errors += len(
                        validator_report["errors"]
                    )

            if not valid:
                raise ValueError(
                    f"Ungültige Konfiguration '{namespace}': "
                    f"{validator_report['errors']}"
                )

            config_changed = (
                validated_config != config
                or migration_report["migrated"]
            )

            if migration_report["migrated"]:
                with self.lock:
                    self.migrations_run += 1
                    self.last_migration_at = datetime.now(UTC).isoformat()

            if config_changed:
                backup_was_possible = self.storage.exists(namespace)

                self.storage.save(
                    namespace=namespace,
                    data=validated_config,
                    create_backup=True
                )

                with self.lock:
                    self.files_saved += 1
                    self.last_saved_at = datetime.now(UTC).isoformat()

                    if backup_was_possible:
                        self.backups_created += 1
                        self.last_backup_at = self.last_saved_at

            self.cache.set(
                namespace=namespace,
                value=validated_config
            )

            with self.lock:
                self.files_loaded += 1
                self.last_loaded_at = datetime.now(UTC).isoformat()
                self.last_error = None

            self.add_timeline_event(
                event_type="CONFIG_LOADED",
                payload={
                    "namespace": namespace,
                    "migrated": migration_report["migrated"],
                    "defaults_added": len(
                        validator_report["changes"]
                    )
                }
            )

            return deepcopy(
                validated_config
            )

        except Exception as error:
            self.set_error(
                error,
                critical=False
            )

            if defaults:
                self.cache.set(
                    namespace=namespace,
                    value=defaults
                )

            return defaults

    def reload(
        self,
        namespace
    ):
        self.cache.delete(namespace)

        config = self.load(
            namespace=namespace,
            use_cache=False
        )

        with self.lock:
            self.files_reloaded += 1

        self.add_timeline_event(
            event_type="CONFIG_RELOADED",
            payload={
                "namespace": namespace
            }
        )

        return config

    def reload_all(self):
        self.ensure_default_configs()

        loaded = {}

        for namespace in sorted(DEFAULT_CONFIGS.keys()):
            loaded[namespace] = self.reload(namespace)

        return loaded

    # =====================================================
    # Saving
    # =====================================================

    def save(
        self,
        namespace,
        create_backup=True
    ):
        if not self.cache.has(namespace):
            return False

        data = self.cache.get(
            namespace,
            default={}
        )

        valid, validated_data = self.validator.validate(
            namespace=namespace,
            config=data
        )

        validator_report = self.validator.get_report()

        with self.lock:
            self.validations_run += 1
            self.last_validation_at = datetime.now(UTC).isoformat()
            self.defaults_added += len(
                validator_report["changes"]
            )

        if not valid:
            with self.lock:
                self.validation_errors += len(
                    validator_report["errors"]
                )

                self.last_error = (
                    f"Konfiguration '{namespace}' konnte nicht "
                    f"gespeichert werden: {validator_report['errors']}"
                )

            return False

        try:
            backup_was_possible = (
                create_backup
                and self.storage.exists(namespace)
            )

            success = self.storage.save(
                namespace=namespace,
                data=validated_data,
                create_backup=create_backup
            )

            if not success:
                return False

            self.cache.set(
                namespace=namespace,
                value=validated_data
            )

            with self.lock:
                self.files_saved += 1
                self.last_saved_at = datetime.now(UTC).isoformat()
                self.last_error = None

                if backup_was_possible:
                    self.backups_created += 1
                    self.last_backup_at = self.last_saved_at

            self.add_timeline_event(
                event_type="CONFIG_SAVED",
                payload={
                    "namespace": namespace
                }
            )

            self.events.publish(
                event_name="CONFIG_SAVED",
                payload={
                    "namespace": namespace
                }
            )

            if self.watcher.lifecycle["initialized"]:
                self.watcher.refresh_baseline()

            return True

        except Exception as error:
            return self.set_error(error)

    def save_all(self):
        namespaces = self.cache.list_namespaces()
        success = True

        for namespace in namespaces:
            if not self.save(namespace):
                success = False

        return success

    # =====================================================
    # Public Config API
    # =====================================================

    def get(
        self,
        namespace,
        key=None,
        default=None
    ):
        if not self.cache.has(namespace):
            self.load(namespace)

        config = self.cache.get(
            namespace,
            default={}
        )

        with self.lock:
            self.values_read += 1

        if key is None:
            return deepcopy(config)

        return deepcopy(
            config.get(
                key,
                default
            )
        )

    def get_resolved(
        self,
        namespace,
        key=None,
        default=None
    ):
        """Return persisted configuration with environment/runtime overrides."""
        persisted = self.get(namespace)
        resolved = self.sources.resolve(namespace, persisted)
        if key is None:
            return resolved
        return deepcopy(resolved.get(key, default))

    def get_typed(self, namespace, resolved=True):
        """Return an immutable typed configuration model where one exists."""
        data = self.get_resolved(namespace) if resolved else self.get(namespace)
        return build_typed_config(namespace, data)

    def set_runtime_override(self, namespace, key, value):
        if namespace not in DEFAULT_CONFIGS or key not in DEFAULT_CONFIGS[namespace]:
            return False
        self.sources.set_runtime(namespace, key, value)
        self.add_timeline_event("CONFIG_RUNTIME_OVERRIDE_SET", {"namespace": namespace, "key": key})
        return True

    def clear_runtime_overrides(self, namespace=None, key=None):
        self.sources.clear_runtime(namespace, key)
        self.add_timeline_event("CONFIG_RUNTIME_OVERRIDES_CLEARED", {"namespace": namespace, "key": key})
        return True

    def set(
        self,
        namespace,
        key,
        value,
        save=True
    ):
        if namespace not in DEFAULT_CONFIGS:
            with self.lock:
                self.last_error = (
                    f"Unbekannter Konfigurations-Namespace: {namespace}"
                )

            return False

        if not self.cache.has(namespace):
            self.load(namespace)

        config = self.cache.get(
            namespace,
            default=deepcopy(
                DEFAULT_CONFIGS[namespace]
            )
        )

        old_value = deepcopy(
            config.get(key)
        )

        config[key] = deepcopy(value)

        if not self.cache.set(
            namespace=namespace,
            value=config
        ):
            return False

        with self.lock:
            self.values_written += 1

        self.add_timeline_event(
            event_type="CONFIG_VALUE_SET",
            payload={
                "namespace": namespace,
                "key": key
            }
        )

        self.events.config_changed(
            namespace=namespace,
            key=key,
            old_value=old_value,
            new_value=deepcopy(value)
        )

        if save:
            return self.save(namespace)

        return True

    def update(
        self,
        namespace,
        values,
        save=True
    ):
        if not isinstance(values, dict):
            with self.lock:
                self.last_error = (
                    "Config update values must be a dictionary."
                )

            return False

        if namespace not in DEFAULT_CONFIGS:
            with self.lock:
                self.last_error = (
                    f"Unbekannter Konfigurations-Namespace: {namespace}"
                )

            return False

        if not self.cache.has(namespace):
            self.load(namespace)

        config = self.cache.get(
            namespace,
            default=deepcopy(
                DEFAULT_CONFIGS[namespace]
            )
        )

        old_values = {
            key: deepcopy(
                config.get(key)
            )
            for key in values
        }

        config.update(
            deepcopy(values)
        )

        if not self.cache.set(
            namespace=namespace,
            value=config
        ):
            return False

        with self.lock:
            self.values_written += len(values)

        self.add_timeline_event(
            event_type="CONFIG_UPDATED",
            payload={
                "namespace": namespace,
                "keys": list(values.keys())
            }
        )

        for key, value in values.items():
            self.events.config_changed(
                namespace=namespace,
                key=key,
                old_value=old_values[key],
                new_value=deepcopy(value)
            )

        self.events.namespace_changed(
            namespace
        )

        if save:
            return self.save(namespace)

        return True

    def delete(
        self,
        namespace,
        key,
        save=True
    ):
        if not self.cache.has(namespace):
            self.load(namespace)

        config = self.cache.get(
            namespace,
            default={}
        )

        if key not in config:
            return False

        old_value = deepcopy(
            config[key]
        )

        del config[key]

        if not self.cache.set(
            namespace=namespace,
            value=config
        ):
            return False

        with self.lock:
            self.values_deleted += 1

        self.add_timeline_event(
            event_type="CONFIG_VALUE_DELETED",
            payload={
                "namespace": namespace,
                "key": key
            }
        )

        self.events.publish(
            event_name="CONFIG_VALUE_DELETED",
            payload={
                "namespace": namespace,
                "key": key,
                "old_value": old_value
            }
        )

        if save:
            return self.save(namespace)

        return True

    # =====================================================
    # Transactions
    # =====================================================

    def begin_transaction(
        self,
        name=None
    ):
        transaction = ConfigTransaction(
            config_manager=self,
            name=name
        )

        with self.lock:
            self.transactions_created += 1

        self.add_timeline_event(
            event_type="CONFIG_TRANSACTION_CREATED",
            payload={
                "transaction_id": transaction.transaction_id,
                "name": transaction.name
            }
        )

        self.events.publish(
            event_name="CONFIG_TRANSACTION_CREATED",
            payload={
                "transaction_id": transaction.transaction_id,
                "name": transaction.name
            }
        )

        return transaction

    # =====================================================
    # Watcher
    # =====================================================

    def start_watcher(self):
        self.watcher_enabled = True
        self.watcher.refresh_baseline()

        return self.watcher.start()

    def stop_watcher(self):
        self.watcher_enabled = False

        return self.watcher.stop()

    def get_watcher_status(self):
        return self.watcher.get_status()

    def _handle_watcher_change(
        self,
        change
    ):
        namespace = change.get(
            "namespace"
        )

        change_type = change.get(
            "change_type"
        )

        with self.lock:
            self.last_watcher_change_at = (
                datetime.now(UTC).isoformat()
            )

        if namespace not in DEFAULT_CONFIGS:
            self.events.publish(
                event_name="CONFIG_UNKNOWN_FILE_CHANGED",
                payload=deepcopy(change)
            )

            return False

        if change_type in [
            "CREATED",
            "MODIFIED"
        ]:
            self.cache.delete(namespace)

            config = self.load(
                namespace=namespace,
                use_cache=False
            )

            with self.lock:
                self.watcher_reloads += 1

            self.add_timeline_event(
                event_type="CONFIG_LIVE_RELOADED",
                payload={
                    "namespace": namespace,
                    "change_type": change_type
                }
            )

            self.events.publish(
                event_name="CONFIG_LIVE_RELOADED",
                payload={
                    "namespace": namespace,
                    "change_type": change_type,
                    "config": deepcopy(config)
                }
            )

            return True

        if change_type == "DELETED":
            defaults = deepcopy(
                DEFAULT_CONFIGS[namespace]
            )

            self.storage.save(
                namespace=namespace,
                data=defaults,
                create_backup=False
            )

            self.cache.set(
                namespace=namespace,
                value=defaults
            )

            self.watcher.refresh_baseline()

            with self.lock:
                self.files_created += 1
                self.recovered_config_files += 1

            self.add_timeline_event(
                event_type="CONFIG_FILE_RECOVERED",
                payload={
                    "namespace": namespace
                }
            )

            self.events.publish(
                event_name="CONFIG_FILE_RECOVERED",
                payload={
                    "namespace": namespace,
                    "reason": "deleted"
                }
            )

            return True

        return False

    # =====================================================
    # Validation and Migration
    # =====================================================

    def validate(
        self,
        namespace
    ):
        config = self.get(namespace)

        valid, validated = self.validator.validate(
            namespace=namespace,
            config=config
        )

        report = self.validator.get_report()

        with self.lock:
            self.validations_run += 1
            self.last_validation_at = datetime.now(UTC).isoformat()

            if not valid:
                self.validation_errors += len(
                    report["errors"]
                )

        return {
            "namespace": namespace,
            "valid": valid,
            "config": validated,
            "report": report
        }

    def migrate(
        self,
        namespace
    ):
        config = self.get(namespace)

        migrated, report = self.migrator.migrate(
            namespace=namespace,
            config=config,
            target_version=CONFIG_VERSION
        )

        self.cache.set(
            namespace=namespace,
            value=migrated
        )

        with self.lock:
            if report["migrated"]:
                self.migrations_run += 1
                self.last_migration_at = datetime.now(UTC).isoformat()

        if report["migrated"]:
            self.save(namespace)

        return {
            "config": migrated,
            "report": report
        }

    # =====================================================
    # Backup and Restore
    # =====================================================

    def backup(
        self,
        namespace
    ):
        try:
            success = self.storage.backup(namespace)

            if success:
                with self.lock:
                    self.backups_created += 1
                    self.last_backup_at = datetime.now(UTC).isoformat()

                self.add_timeline_event(
                    event_type="CONFIG_BACKUP_CREATED",
                    payload={
                        "namespace": namespace
                    }
                )

            return success

        except Exception as error:
            return self.set_error(
                error,
                critical=False
            )

    def restore_latest_backup(
        self,
        namespace
    ):
        prefix = f"{namespace}_"

        if not os.path.exists(
            self.backup_path
        ):
            return False

        backup_files = [
            filename
            for filename in os.listdir(self.backup_path)
            if filename.startswith(prefix)
            and filename.endswith(".json")
        ]

        if not backup_files:
            return False

        backup_files.sort(
            reverse=True
        )

        latest_backup = os.path.join(
            self.backup_path,
            backup_files[0]
        )

        target_path = self.storage.get_path(
            namespace
        )

        try:
            shutil.copy2(
                latest_backup,
                target_path
            )

            self.reload(namespace)

            with self.lock:
                self.restores_completed += 1
                self.last_restore_at = datetime.now(UTC).isoformat()

            self.add_timeline_event(
                event_type="CONFIG_RESTORED",
                payload={
                    "namespace": namespace,
                    "backup": latest_backup
                }
            )

            if self.watcher.lifecycle["initialized"]:
                self.watcher.refresh_baseline()

            self.events.publish(
                event_name="CONFIG_RESTORED",
                payload={
                    "namespace": namespace,
                    "backup": latest_backup
                }
            )

            return True

        except Exception as error:
            return self.set_error(error)

    # =====================================================
    # Reset
    # =====================================================

    def reset_namespace(
        self,
        namespace,
        save=True
    ):
        if namespace not in DEFAULT_CONFIGS:
            return False

        self.cache.set(
            namespace=namespace,
            value=deepcopy(
                DEFAULT_CONFIGS[namespace]
            )
        )

        self.add_timeline_event(
            event_type="CONFIG_RESET",
            payload={
                "namespace": namespace
            }
        )

        self.events.publish(
            event_name="CONFIG_RESET",
            payload={
                "namespace": namespace,
                "reset": True
            }
        )

        if save:
            return self.save(namespace)

        return True

    def reset_all(self):
        success = True

        for namespace in DEFAULT_CONFIGS:
            if not self.reset_namespace(namespace):
                success = False

        return success

    # =====================================================
    # Cache Management
    # =====================================================

    def clear_cache(self):
        result = self.cache.clear()

        if result:
            self.add_timeline_event(
                "CONFIG_CACHE_CLEARED"
            )

        return result

    def cleanup_cache(self):
        removed = self.cache.cleanup_expired()

        if removed > 0:
            self.add_timeline_event(
                event_type="CONFIG_CACHE_CLEANED",
                payload={
                    "removed_entries": removed
                }
            )

        return removed

    def invalidate_cache(
        self,
        namespace
    ):
        deleted = self.cache.delete(namespace)

        if deleted:
            self.add_timeline_event(
                event_type="CONFIG_CACHE_INVALIDATED",
                payload={
                    "namespace": namespace
                }
            )

        return deleted

    def update_cache_ttl(
        self,
        namespace,
        ttl
    ):
        return self.cache.update_ttl(
            namespace=namespace,
            ttl=ttl
        )

    def get_cache_status(self):
        return self.cache.get_status()

    def get_events_status(self):
        return self.events.get_status()

    # =====================================================
    # Import and Export
    # =====================================================

    def export_namespace(
        self,
        namespace,
        export_path
    ):
        config = self.get(namespace)

        try:
            export_directory = os.path.dirname(
                export_path
            )

            if export_directory:
                os.makedirs(
                    export_directory,
                    exist_ok=True
                )

            with open(
                export_path,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    config,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            with self.lock:
                self.exports_created += 1

            return True

        except Exception as error:
            return self.set_error(
                error,
                critical=False
            )

    def export_all(
        self,
        export_path
    ):
        export_data = {
            namespace: self.cache.get(
                namespace,
                default={}
            )
            for namespace in self.cache.list_namespaces()
        }

        try:
            export_directory = os.path.dirname(
                export_path
            )

            if export_directory:
                os.makedirs(
                    export_directory,
                    exist_ok=True
                )

            with open(
                export_path,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    export_data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            with self.lock:
                self.exports_created += 1

            return True

        except Exception as error:
            return self.set_error(
                error,
                critical=False
            )

    def import_namespace(
        self,
        namespace,
        import_path,
        save=True
    ):
        if namespace not in DEFAULT_CONFIGS:
            return False

        try:
            with open(
                import_path,
                "r",
                encoding="utf-8"
            ) as file:
                imported = json.load(file)

            if not isinstance(imported, dict):
                with self.lock:
                    self.last_error = (
                        "Imported configuration must be a dictionary."
                    )

                return False

            valid, validated = self.validator.validate(
                namespace=namespace,
                config=imported
            )

            if not valid:
                with self.lock:
                    self.last_error = str(
                        self.validator.get_report()["errors"]
                    )

                return False

            self.cache.set(
                namespace=namespace,
                value=validated
            )

            with self.lock:
                self.imports_completed += 1

            if save:
                return self.save(namespace)

            return True

        except Exception as error:
            return self.set_error(
                error,
                critical=False
            )

    # =====================================================
    # Information
    # =====================================================

    def list_namespaces(self):
        return sorted(
            self.cache.list_namespaces()
        )

    def get_version(
        self,
        namespace
    ):
        return self.get(
            namespace=namespace,
            key="version",
            default=None
        )

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "mission": self.mission,
            "requires": [],
            "optional": [
                "core.event_bus",
                "core.logger"
            ],
            "capabilities": deepcopy(
                self.capabilities
            )
        }

    def get_statistics(self):
        with self.lock:
            manager_statistics = {
                "files_created": self.files_created,
                "files_loaded": self.files_loaded,
                "files_saved": self.files_saved,
                "files_reloaded": self.files_reloaded,
                "validations_run": self.validations_run,
                "validation_errors": self.validation_errors,
                "defaults_added": self.defaults_added,
                "migrations_run": self.migrations_run,
                "backups_created": self.backups_created,
                "restores_completed": self.restores_completed,
                "values_read": self.values_read,
                "values_written": self.values_written,
                "values_deleted": self.values_deleted,
                "exports_created": self.exports_created,
                "imports_completed": self.imports_completed,
                "transactions_created": self.transactions_created,
                "watcher_reloads": self.watcher_reloads,
                "recovered_config_files": self.recovered_config_files,
                "cached_namespaces": self.cache.list_namespaces(),
                "timeline_count": len(self.timeline),
                "config_path": self.config_path,
                "backup_path": self.backup_path,
                "created_at": self.created_at,
                "last_loaded_at": self.last_loaded_at,
                "last_saved_at": self.last_saved_at,
                "last_validation_at": self.last_validation_at,
                "last_migration_at": self.last_migration_at,
                "last_backup_at": self.last_backup_at,
                "last_restore_at": self.last_restore_at,
                "last_watcher_change_at": self.last_watcher_change_at
            }

        manager_statistics["cache"] = self.cache.get_statistics()

        manager_statistics["events"] = (
            self.events.get_status()["statistics"]
        )

        manager_statistics["watcher"] = (
            self.watcher.get_statistics()
        )

        return manager_statistics

    def get_status(self):
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": deepcopy(
                self.lifecycle
            ),
            "statistics": self.get_statistics(),
            "cache": self.cache.get_status(),
            "events": self.events.get_status(),
            "watcher": self.watcher.get_status(),
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
            event_type="CONFIG_MANAGER_ERROR",
            payload={
                "error": str(error),
                "critical": critical
            }
        )

        self.events.publish(
            event_name="CONFIG_MANAGER_ERROR",
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

    # =====================================================
    # Optional Integrations
    # =====================================================

    def _emit_event(
        self,
        event_type,
        payload=None,
        severity="INFO"
    ):
        if self.event_bus is None:
            return False

        if payload is None:
            payload = {}

        self.event_bus.publish(
            event_type=event_type,
            payload=payload,
            source=self.component_id,
            severity=severity
        )

        return True

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
    config = ConfigManager(
        cache_ttl=None,
        cache_max_entries=1000,
        watcher_enabled=False
    )

    config.initialize()
    config.start()

    print("=== CONFIG SYSTEM INTEGRATION TEST ===")
    print()

    print("Namespaces:")
    print(
        config.list_namespaces()
    )

    print()
    print("Boot Mode:")
    print(
        config.get(
            namespace="boot",
            key="boot_mode"
        )
    )

    original_boot_config = config.get("boot")

    print()
    print("Set Test:")
    print(
        config.set(
            namespace="boot",
            key="boot_mode",
            value="testing"
        )
    )

    print()
    print("Transaction Test:")

    transaction = config.begin_transaction(
        "Boot Transaction Test"
    )

    transaction.set(
        namespace="boot",
        key="safe_mode",
        value=True
    )

    transaction.set(
        namespace="boot",
        key="parallel_boot",
        value=True
    )

    print(
        transaction.preview()
    )

    print(
        "Commit:",
        transaction.commit()
    )

    print()
    print("Boot Config:")
    print(
        config.get("boot")
    )

    print()
    print("Cache Status:")
    print(
        config.get_cache_status()
    )

    print()
    print("Events Status:")
    print(
        config.get_events_status()
    )

    print()
    print("Watcher Status:")
    print(
        config.get_watcher_status()
    )

    print()
    print("Manager Status:")
    print(
        config.get_status()
    )

    config.cache.set(
        namespace="boot",
        value=original_boot_config
    )

    config.save(
        namespace="boot",
        create_backup=False
    )

    config.stop()