from core.common import BaseKernelComponent
import json
import os
from datetime import datetime, UTC


class JarvisLogger(BaseKernelComponent):

    COMPONENT_ID = "core.logger"
    NAME = "J.A.R.V.I.S. Logger"
    PRIORITY = 5
    AUTO_START = True

    VERSION = "0.1.0"

    def __init__(
        self,
        log_path="logs"
    ):
        BaseKernelComponent.__init__(self)
        self.name = "J.A.R.V.I.S. Logger"
        self.component_id = "core.logger"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = "Zentrales Logging-System für J.A.R.V.I.S."

        self.log_path = log_path

        self.status = "OFFLINE"
        self.health = 0

        self.logs_written = 0
        self.last_log_at = None
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
            "log_info",
            "log_warning",
            "log_error",
            "log_debug",
            "log_security",
            "json_logs",
            "daily_log_files"
        ]

    def initialize(self):
        os.makedirs(
            self.log_path,
            exist_ok=True
        )

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

        self.info(
            message="Logger gestartet",
            source=self.component_id
        )

        return True

    def stop(self):
        self.info(
            message="Logger gestoppt",
            source=self.component_id
        )

        self.status = "OFFLINE"
        self.health = 0
        self.last_stopped = datetime.now(UTC).isoformat()

        self.lifecycle["started"] = False
        self.lifecycle["healthy"] = False

        return True

    def log(
        self,
        level,
        message,
        source="UNKNOWN",
        payload=None
    ):
        if payload is None:
            payload = {}

        timestamp = datetime.now(UTC).isoformat()

        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "source": source,
            "message": message,
            "payload": payload
        }

        filename = datetime.now(UTC).strftime(
            "%Y-%m-%d.jsonl"
        )

        file_path = os.path.join(
            self.log_path,
            filename
        )

        try:
            with open(
                file_path,
                "a",
                encoding="utf-8"
            ) as file:
                file.write(
                    json.dumps(
                        log_entry,
                        ensure_ascii=False
                    ) + "\n"
                )

            self.logs_written += 1
            self.last_log_at = timestamp

            return True

        except Exception as error:
            self.last_error = str(error)
            self.health = 0
            self.status = "ERROR"
            self.lifecycle["healthy"] = False

            return False

    def info(
        self,
        message,
        source="UNKNOWN",
        payload=None
    ):
        return self.log(
            level="INFO",
            message=message,
            source=source,
            payload=payload
        )

    def warning(
        self,
        message,
        source="UNKNOWN",
        payload=None
    ):
        return self.log(
            level="WARNING",
            message=message,
            source=source,
            payload=payload
        )

    def error(
        self,
        message,
        source="UNKNOWN",
        payload=None
    ):
        return self.log(
            level="ERROR",
            message=message,
            source=source,
            payload=payload
        )

    def debug(
        self,
        message,
        source="UNKNOWN",
        payload=None
    ):
        return self.log(
            level="DEBUG",
            message=message,
            source=source,
            payload=payload
        )

    def security(
        self,
        message,
        source="UNKNOWN",
        payload=None
    ):
        return self.log(
            level="SECURITY",
            message=message,
            source=source,
            payload=payload
        )

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
            "logs_written": self.logs_written,
            "last_log_at": self.last_log_at,
            "log_path": self.log_path
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
    logger = JarvisLogger()

    logger.initialize()
    logger.start()

    logger.info(
        message="Test Info Log",
        source="LoggerTest"
    )

    logger.warning(
        message="Test Warning Log",
        source="LoggerTest"
    )

    logger.error(
        message="Test Error Log",
        source="LoggerTest"
    )

    print("=== LOGGER STATUS ===")
    print(logger.get_status())