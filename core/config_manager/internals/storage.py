import json
import os
import shutil
from datetime import datetime, UTC


class ConfigStorage:

    def __init__(
        self,
        config_path="config",
        backup_path="backups/config"
    ):
        self.config_path = config_path
        self.backup_path = backup_path

        os.makedirs(
            self.config_path,
            exist_ok=True
        )

        os.makedirs(
            self.backup_path,
            exist_ok=True
        )

    def get_path(
        self,
        namespace
    ):
        return os.path.join(
            self.config_path,
            f"{namespace}.json"
        )

    def exists(
        self,
        namespace
    ):
        return os.path.exists(
            self.get_path(namespace)
        )

    def load(
        self,
        namespace,
        default=None
    ):
        if default is None:
            default = {}

        path = self.get_path(namespace)

        if not os.path.exists(path):
            self.save(
                namespace=namespace,
                data=default,
                create_backup=False
            )

            return default

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    def save(
        self,
        namespace,
        data,
        create_backup=True
    ):
        path = self.get_path(namespace)

        if create_backup and os.path.exists(path):
            self.backup(namespace)

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    def backup(
        self,
        namespace
    ):
        source = self.get_path(namespace)

        if not os.path.exists(source):
            return False

        timestamp = datetime.now(UTC).strftime(
            "%Y%m%d_%H%M%S"
        )

        target = os.path.join(
            self.backup_path,
            f"{namespace}_{timestamp}.json"
        )

        shutil.copy2(
            source,
            target
        )

        return True

    def load_all(
        self
    ):
        configs = {}

        if not os.path.exists(
            self.config_path
        ):
            return configs

        for filename in os.listdir(
            self.config_path
        ):
            if not filename.endswith(".json"):
                continue

            namespace = filename[:-5]

            configs[namespace] = self.load(
                namespace
            )

        return configs

    def save_all(
        self,
        configs
    ):
        for namespace, data in configs.items():
            self.save(
                namespace=namespace,
                data=data
            )

        return True

    def delete(
        self,
        namespace
    ):
        path = self.get_path(namespace)

        if not os.path.exists(path):
            return False

        os.remove(path)
        return True


if __name__ == "__main__":
    storage = ConfigStorage()

    storage.save(
        namespace="storage_test",
        data={
            "test": True
        },
        create_backup=False
    )

    loaded = storage.load(
        namespace="storage_test"
    )

    print("=== CONFIG STORAGE TEST ===")
    print(loaded)