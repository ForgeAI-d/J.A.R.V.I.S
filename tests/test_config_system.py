import json
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from core.config_manager.internals import CONFIG_VERSION, DEFAULT_CONFIGS
from core.config_manager import ConfigManager


class ConfigSystemIntegrationTest:

    def __init__(self):
        self.results = []

        self.temp_root = tempfile.mkdtemp(
            prefix="jarvis_config_test_"
        )

        self.config_path = os.path.join(
            self.temp_root,
            "config"
        )

        self.backup_path = os.path.join(
            self.temp_root,
            "backups",
            "config"
        )

        self.export_path = os.path.join(
            self.temp_root,
            "exports",
            "boot.json"
        )

        self.config = ConfigManager(
            config_path=self.config_path,
            backup_path=self.backup_path,
            cache_ttl=None,
            cache_max_entries=1000,
            watcher_enabled=True,
            watcher_poll_interval=0.1
        )

    # =====================================================
    # Test Helpers
    # =====================================================

    def check(
        self,
        name,
        condition,
        details=""
    ):
        passed = bool(condition)

        self.results.append(
            {
                "name": name,
                "passed": passed,
                "details": details
            }
        )

        status = "PASS" if passed else "FAIL"

        print(
            f"{name:.<38} {status}"
        )

        if details and not passed:
            print(
                f"    {details}"
            )

        return passed

    def wait_for(
        self,
        condition,
        timeout=3.0,
        interval=0.1
    ):
        deadline = time.time() + timeout

        while time.time() < deadline:
            if condition():
                return True

            time.sleep(interval)

        return False

    # =====================================================
    # Main Test
    # =====================================================

    def run(self):
        print()
        print("=" * 56)
        print("J.A.R.V.I.S. CONFIG SYSTEM INTEGRATION TEST")
        print("=" * 56)

        try:
            # -------------------------------------------------
            # Lifecycle
            # -------------------------------------------------

            self.check(
                "Initialize",
                self.config.initialize()
            )

            self.check(
                "Start",
                self.config.start()
            )

            self.check(
                "Manager Online",
                self.config.status == "ONLINE"
                and self.config.health == 100
            )

            # -------------------------------------------------
            # Automatic Environment Creation
            # -------------------------------------------------

            expected_files = {
                f"{namespace}.json"
                for namespace in DEFAULT_CONFIGS
            }

            actual_files = {
                filename
                for filename in os.listdir(
                    self.config_path
                )
                if filename.endswith(".json")
            }

            self.check(
                "Auto Create",
                actual_files == expected_files,
                (
                    f"Expected: {sorted(expected_files)}, "
                    f"Actual: {sorted(actual_files)}"
                )
            )

            self.check(
                "Namespaces",
                set(
                    self.config.list_namespaces()
                ) == set(
                    DEFAULT_CONFIGS.keys()
                )
            )

            # -------------------------------------------------
            # Loading and Cache
            # -------------------------------------------------

            boot_config = self.config.get(
                "boot"
            )

            self.check(
                "Storage Load",
                isinstance(boot_config, dict)
                and "boot_mode" in boot_config
            )

            hits_before = (
                self.config.cache
                .get_statistics()["hits"]
            )

            self.config.get(
                "boot",
                "boot_mode"
            )

            self.config.get(
                "boot",
                "boot_mode"
            )

            hits_after = (
                self.config.cache
                .get_statistics()["hits"]
            )

            self.check(
                "Cache",
                hits_after > hits_before
            )

            # -------------------------------------------------
            # Get, Set, Update and Delete
            # -------------------------------------------------

            self.check(
                "Set",
                self.config.set(
                    namespace="boot",
                    key="boot_mode",
                    value="testing"
                )
                and self.config.get(
                    "boot",
                    "boot_mode"
                ) == "testing"
            )

            self.check(
                "Update",
                self.config.update(
                    namespace="boot",
                    values={
                        "safe_mode": True,
                        "parallel_boot": True
                    }
                )
                and self.config.get(
                    "boot",
                    "safe_mode"
                ) is True
                and self.config.get(
                    "boot",
                    "parallel_boot"
                ) is True
            )

            self.config.set(
                namespace="boot",
                key="temporary_test_key",
                value="delete-me",
                save=False
            )

            self.check(
                "Delete",
                self.config.delete(
                    namespace="boot",
                    key="temporary_test_key",
                    save=False
                )
                and "temporary_test_key"
                not in self.config.get("boot")
            )

            # -------------------------------------------------
            # Validation
            # -------------------------------------------------

            validation = self.config.validate(
                "boot"
            )

            self.check(
                "Validation",
                validation["valid"]
                and not validation["report"]["errors"]
            )

            invalid_boot = self.config.get(
                "boot"
            )

            invalid_boot["safe_mode"] = (
                "not-a-boolean"
            )

            valid, _ = (
                self.config.validator.validate(
                    namespace="boot",
                    config=invalid_boot
                )
            )

            self.check(
                "Invalid Type Detection",
                not valid
            )

            # -------------------------------------------------
            # Defaults
            # -------------------------------------------------

            incomplete_boot = {
                "version": CONFIG_VERSION,
                "boot_mode": "development"
            }

            valid, completed_boot = (
                self.config.validator.validate(
                    namespace="boot",
                    config=incomplete_boot
                )
            )

            self.check(
                "Default Completion",
                valid
                and "safe_mode" in completed_boot
                and "parallel_boot" in completed_boot
            )

            # -------------------------------------------------
            # Migration
            # -------------------------------------------------

            old_config = {
                "version": 0,
                "boot_mode": "development"
            }

            migrated, migration_report = (
                self.config.migrator.migrate(
                    namespace="boot",
                    config=old_config,
                    target_version=CONFIG_VERSION
                )
            )

            self.check(
                "Migration",
                migration_report["migrated"]
                and migrated["version"]
                == CONFIG_VERSION
                and "safe_mode" in migrated
            )

            # -------------------------------------------------
            # Events
            # -------------------------------------------------

            events_before = (
                self.config.events
                .get_status()["statistics"][
                    "events_sent"
                ]
            )

            self.config.set(
                namespace="boot",
                key="boot_mode",
                value="development"
            )

            events_after = (
                self.config.events
                .get_status()["statistics"][
                    "events_sent"
                ]
            )

            self.check(
                "Events",
                events_after > events_before
            )

            # -------------------------------------------------
            # Transactions: Commit
            # -------------------------------------------------

            transaction = (
                self.config.begin_transaction(
                    "Integration Commit"
                )
            )

            transaction.set(
                namespace="boot",
                key="boot_mode",
                value="production"
            )

            transaction.set(
                namespace="boot",
                key="safe_mode",
                value=False
            )

            preview = transaction.preview()

            self.check(
                "Transaction Preview",
                "boot" in preview
                and preview["boot"]["after"][
                    "boot_mode"
                ] == "production"
            )

            self.check(
                "Transaction Commit",
                transaction.commit()
                and transaction.status
                == transaction.STATUS_COMMITTED
                and self.config.get(
                    "boot",
                    "boot_mode"
                ) == "production"
            )

            # -------------------------------------------------
            # Transactions: Rollback
            # -------------------------------------------------

            value_before_rollback = (
                self.config.get(
                    "boot",
                    "boot_mode"
                )
            )

            rollback_transaction = (
                self.config.begin_transaction(
                    "Integration Rollback"
                )
            )

            rollback_transaction.set(
                namespace="boot",
                key="boot_mode",
                value="development"
            )

            self.check(
                "Transaction Rollback",
                rollback_transaction.rollback()
                and rollback_transaction.status
                == rollback_transaction.STATUS_ROLLED_BACK
                and self.config.get(
                    "boot",
                    "boot_mode"
                ) == value_before_rollback
            )

            # -------------------------------------------------
            # Backup and Restore
            # -------------------------------------------------

            self.config.set(
                namespace="boot",
                key="boot_mode",
                value="testing"
            )

            self.check(
                "Backup",
                self.config.backup("boot")
            )

            self.config.set(
                namespace="boot",
                key="boot_mode",
                value="production"
            )

            restored = (
                self.config.restore_latest_backup(
                    "boot"
                )
            )

            self.check(
                "Restore",
                restored
                and self.config.get(
                    "boot",
                    "boot_mode"
                ) == "testing"
            )

            # -------------------------------------------------
            # Export and Import
            # -------------------------------------------------

            exported = (
                self.config.export_namespace(
                    namespace="boot",
                    export_path=self.export_path
                )
            )

            self.check(
                "Export",
                exported
                and os.path.exists(
                    self.export_path
                )
            )

            imported_boot = deepcopy(
                DEFAULT_CONFIGS["boot"]
            )

            imported_boot["boot_mode"] = (
                "development"
            )

            with open(
                self.export_path,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    imported_boot,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            imported = (
                self.config.import_namespace(
                    namespace="boot",
                    import_path=self.export_path
                )
            )

            self.check(
                "Import",
                imported
                and self.config.get(
                    "boot",
                    "boot_mode"
                ) == "development"
            )

            # -------------------------------------------------
            # Live Reload
            # -------------------------------------------------

            boot_path = (
                self.config.storage.get_path(
                    "boot"
                )
            )

            external_boot = self.config.get(
                "boot"
            )

            external_boot["boot_mode"] = (
                "production"
            )

            time.sleep(0.2)

            with open(
                boot_path,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    external_boot,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            os.utime(
                boot_path,
                None
            )

            watcher_reloaded = self.wait_for(
                lambda: self.config.get(
                    "boot",
                    "boot_mode"
                ) == "production"
            )

            self.check(
                "Watcher Live Reload",
                watcher_reloaded
            )

            # -------------------------------------------------
            # Deleted File Recovery
            # -------------------------------------------------

            os.remove(
                boot_path
            )

            recovered = self.wait_for(
                lambda: os.path.exists(
                    boot_path
                )
            )

            self.check(
                "Deleted File Recovery",
                recovered
                and self.config.get(
                    "boot"
                ) == DEFAULT_CONFIGS["boot"]
            )

            # -------------------------------------------------
            # Cache Management
            # -------------------------------------------------

            self.check(
                "Cache Invalidate",
                self.config.invalidate_cache(
                    "boot"
                )
            )

            reloaded_boot = self.config.get(
                "boot"
            )

            self.check(
                "Cache Reload",
                isinstance(reloaded_boot, dict)
                and "boot_mode" in reloaded_boot
            )

            self.check(
                "Cache Cleanup",
                isinstance(
                    self.config.cleanup_cache(),
                    int
                )
            )

            # -------------------------------------------------
            # Thread Safety
            # -------------------------------------------------

            def read_worker(_):
                return self.config.get(
                    "network",
                    "api_port"
                )

            with ThreadPoolExecutor(
                max_workers=8
            ) as executor:
                thread_results = list(
                    executor.map(
                        read_worker,
                        range(100)
                    )
                )

            self.check(
                "Thread Safety",
                len(thread_results) == 100
                and all(
                    isinstance(value, int)
                    for value in thread_results
                )
            )

            # -------------------------------------------------
            # Status and Health
            # -------------------------------------------------

            status = self.config.get_status()

            self.check(
                "System Status",
                status["status"] == "ONLINE"
                and status["health"] == 100
                and "cache" in status
                and "events" in status
                and "watcher" in status
            )

            # -------------------------------------------------
            # Shutdown
            # -------------------------------------------------

            self.check(
                "Stop",
                self.config.stop()
            )

            self.check(
                "Watcher Stopped",
                not self.config.watcher.lifecycle[
                    "started"
                ]
            )

        except Exception as error:
            self.check(
                "Unexpected Exception",
                False,
                str(error)
            )

        finally:
            try:
                if self.config.watcher.lifecycle[
                    "started"
                ]:
                    self.config.stop()

            finally:
                shutil.rmtree(
                    self.temp_root,
                    ignore_errors=True
                )

        return self.print_summary()

    # =====================================================
    # Summary
    # =====================================================

    def print_summary(self):
        passed = sum(
            1
            for result in self.results
            if result["passed"]
        )

        total = len(
            self.results
        )

        print()
        print("=" * 56)

        if passed == total:
            print(
                f"CONFIG SYSTEM: SUCCESS "
                f"({passed}/{total})"
            )
        else:
            print(
                f"CONFIG SYSTEM: FAILED "
                f"({passed}/{total})"
            )

            print()

            for result in self.results:
                if result["passed"]:
                    continue

                print(
                    f"FAIL: {result['name']}"
                )

                if result["details"]:
                    print(
                        f"      {result['details']}"
                    )

        print("=" * 56)
        print()

        return passed == total


if __name__ == "__main__":
    successful = (
        ConfigSystemIntegrationTest().run()
    )

    raise SystemExit(
        0 if successful else 1
    )