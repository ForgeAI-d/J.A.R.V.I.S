from copy import deepcopy
from datetime import datetime, UTC

from .defaults import CONFIG_VERSION, DEFAULT_CONFIGS


class ConfigMigrator:

    VERSION = "1.0.0"

    def __init__(self):
        self.migrations = {}
        self.history = []
        self.last_error = None

    def register_migration(
        self,
        namespace,
        from_version,
        to_version,
        migration_function
    ):
        if namespace not in self.migrations:
            self.migrations[namespace] = {}

        self.migrations[namespace][from_version] = {
            "to_version": to_version,
            "function": migration_function
        }

        return True

    def migrate(
        self,
        namespace,
        config,
        target_version=None
    ):
        if target_version is None:
            target_version = CONFIG_VERSION

        migrated = deepcopy(config)

        current_version = migrated.get(
            "version",
            1
        )

        try:
            current_version = int(current_version)
        except (TypeError, ValueError):
            current_version = 1

        applied_migrations = []

        while current_version < target_version:
            migration = self.migrations.get(
                namespace,
                {}
            ).get(current_version)

            if migration is None:
                migrated = self._apply_default_migration(
                    namespace=namespace,
                    config=migrated,
                    target_version=target_version
                )

                applied_migrations.append(
                    {
                        "namespace": namespace,
                        "from_version": current_version,
                        "to_version": target_version,
                        "type": "default"
                    }
                )

                current_version = target_version
                break

            migration_function = migration["function"]
            next_version = migration["to_version"]

            migrated = migration_function(
                deepcopy(migrated)
            )

            migrated["version"] = next_version

            applied_migrations.append(
                {
                    "namespace": namespace,
                    "from_version": current_version,
                    "to_version": next_version,
                    "type": "custom"
                }
            )

            current_version = next_version

        migrated["version"] = target_version

        migration_report = {
            "namespace": namespace,
            "target_version": target_version,
            "applied_migrations": applied_migrations,
            "migrated": len(applied_migrations) > 0,
            "timestamp": datetime.now(UTC).isoformat()
        }

        self.history.append(
            migration_report
        )

        self.last_error = None

        return migrated, migration_report

    def _apply_default_migration(
        self,
        namespace,
        config,
        target_version
    ):
        defaults = DEFAULT_CONFIGS.get(
            namespace,
            {}
        )

        migrated = deepcopy(config)

        for key, value in defaults.items():
            if key not in migrated:
                migrated[key] = deepcopy(value)

        migrated["version"] = target_version

        return migrated

    def get_history(
        self,
        limit=None
    ):
        if limit is None:
            return deepcopy(self.history)

        return deepcopy(
            self.history[-limit:]
        )

    def get_last_report(self):
        if not self.history:
            return None

        return deepcopy(
            self.history[-1]
        )

    def get_status(self):
        return {
            "version": self.VERSION,
            "registered_namespaces": list(
                self.migrations.keys()
            ),
            "migration_count": len(self.history),
            "last_report": self.get_last_report(),
            "last_error": self.last_error
        }


if __name__ == "__main__":
    migrator = ConfigMigrator()

    old_config = {
        "version": 0,
        "boot_mode": "development"
    }

    migrated_config, report = migrator.migrate(
        namespace="boot",
        config=old_config
    )

    print("=== CONFIG MIGRATOR TEST ===")
    print()
    print("Migrated Config:")
    print(migrated_config)
    print()
    print("Report:")
    print(report)
    print()
    print("Status:")
    print(migrator.get_status())