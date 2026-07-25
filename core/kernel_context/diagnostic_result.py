import importlib.util
import json
import os
import platform
import shutil
import subprocess
import socket
import sys
import time
from copy import deepcopy
from datetime import datetime, UTC
from threading import Condition, RLock
from uuid import uuid4


class DiagnosticResult:

    VALID_SEVERITIES = {"INFO", "WARNING", "ERROR", "CRITICAL"}

    def __init__(
        self,
        name,
        passed,
        severity="INFO",
        message="",
        details=None,
        repaired=False
    ):
        severity = str(severity).strip().upper()
        if severity not in self.VALID_SEVERITIES:
            severity = "ERROR"

        self.name = str(name)
        self.passed = bool(passed)
        self.severity = severity
        self.message = str(message)
        self.details = deepcopy(details or {})
        self.repaired = bool(repaired)
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "details": deepcopy(self.details),
            "repaired": self.repaired,
            "timestamp": self.timestamp
        }


