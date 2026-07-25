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


from .diagnostic_result import DiagnosticResult

class DiagnosticsManager:

    VERSION = "1.0.0"

    SCORE_PENALTIES = {
        "INFO": 0,
        "WARNING": 5,
        "ERROR": 15,
        "CRITICAL": 30
    }

    def __init__(self, context, history_limit=100):
        self.context = context
        self.history_limit = max(1, int(history_limit))
        self.checks = {}
        self.history = []
        self.lock = RLock()

        self.runs = 0
        self.checks_executed = 0
        self.repairs_attempted = 0
        self.repairs_completed = 0
        self.last_run_at = None
        self.last_report = None
        self.last_error = None

        self._register_builtin_checks()

    def register_check(
        self,
        name,
        callback,
        priority=100,
        description="",
        replace=False
    ):
        name = self._normalize_name(name)
        if name is None or not callable(callback):
            return False

        with self.lock:
            if name in self.checks and not replace:
                return False

            self.checks[name] = {
                "callback": callback,
                "priority": int(priority),
                "description": str(description)
            }
        return True

    def unregister_check(self, name):
        name = self._normalize_name(name)
        if name is None:
            return False
        with self.lock:
            return self.checks.pop(name, None) is not None

    def list_checks(self):
        with self.lock:
            ordered = sorted(
                self.checks.items(),
                key=lambda item: (item[1]["priority"], item[0])
            )
            return {
                name: {
                    "priority": data["priority"],
                    "description": data["description"]
                }
                for name, data in ordered
            }

    def run_check(self, name, auto_repair=False):
        name = self._normalize_name(name)
        if name is None:
            return DiagnosticResult(
                "invalid_check",
                False,
                "ERROR",
                "Diagnostic check name is invalid."
            ).to_dict()

        with self.lock:
            check = self.checks.get(name)

        if check is None:
            return DiagnosticResult(
                name,
                False,
                "ERROR",
                f"Diagnostic check '{name}' is not registered."
            ).to_dict()

        try:
            result = check["callback"](bool(auto_repair))
            if isinstance(result, DiagnosticResult):
                normalized = result
            elif isinstance(result, dict):
                normalized = DiagnosticResult(
                    name=name,
                    passed=result.get("passed", False),
                    severity=result.get("severity", "ERROR"),
                    message=result.get("message", ""),
                    details=result.get("details", {}),
                    repaired=result.get("repaired", False)
                )
            elif isinstance(result, bool):
                normalized = DiagnosticResult(
                    name,
                    result,
                    "INFO" if result else "ERROR",
                    "Check passed." if result else "Check failed."
                )
            else:
                normalized = DiagnosticResult(
                    name,
                    False,
                    "ERROR",
                    "Diagnostic callback returned an unsupported result."
                )
        except Exception as error:
            self.last_error = str(error)
            normalized = DiagnosticResult(
                name,
                False,
                "CRITICAL",
                f"Diagnostic check raised an exception: {error}",
                {"exception_type": error.__class__.__name__}
            )

        with self.lock:
            self.checks_executed += 1
            if normalized.repaired:
                self.repairs_completed += 1

        return normalized.to_dict()

    def run(self, auto_repair=False, selected_checks=None):
        started_monotonic = time.monotonic()
        started_at = datetime.now(UTC).isoformat()

        if auto_repair:
            with self.lock:
                self.repairs_attempted += 1

        with self.lock:
            ordered_names = [
                name
                for name, _ in sorted(
                    self.checks.items(),
                    key=lambda item: (item[1]["priority"], item[0])
                )
            ]

        if selected_checks is not None:
            requested = {
                self._normalize_name(name)
                for name in selected_checks
                if self._normalize_name(name) is not None
            }
            ordered_names = [name for name in ordered_names if name in requested]

        results = [
            self.run_check(name, auto_repair=auto_repair)
            for name in ordered_names
        ]

        score = 100
        for result in results:
            if not result["passed"]:
                score -= self.SCORE_PENALTIES.get(result["severity"], 15)
        score = max(0, min(100, score))

        errors = [
            result for result in results
            if not result["passed"] and result["severity"] in {"ERROR", "CRITICAL"}
        ]
        warnings = [
            result for result in results
            if not result["passed"] and result["severity"] == "WARNING"
        ]
        repaired = [result for result in results if result["repaired"]]

        healthy = not errors and score >= 80
        status = (
            "HEALTHY" if healthy and not warnings
            else "DEGRADED" if score >= 50
            else "CRITICAL"
        )

        completed_at = datetime.now(UTC).isoformat()
        report = {
            "diagnostics_version": self.VERSION,
            "component_id": self.context.component_id,
            "boot_id": self.context.boot_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": round(time.monotonic() - started_monotonic, 6),
            "auto_repair": bool(auto_repair),
            "healthy": healthy,
            "status": status,
            "score": score,
            "summary": {
                "total": len(results),
                "passed": sum(1 for result in results if result["passed"]),
                "warnings": len(warnings),
                "errors": len(errors),
                "repaired": len(repaired)
            },
            "checks": {result["name"]: result for result in results},
            "warnings": warnings,
            "errors": errors,
            "repairs": repaired
        }

        with self.lock:
            self.runs += 1
            self.last_run_at = completed_at
            self.last_report = deepcopy(report)
            self.history.append(deepcopy(report))
            if len(self.history) > self.history_limit:
                del self.history[:-self.history_limit]

        self.context.add_timeline_event(
            "KERNEL_DIAGNOSTICS_COMPLETED",
            {
                "score": score,
                "status": status,
                "healthy": healthy,
                "warning_count": len(warnings),
                "error_count": len(errors),
                "repair_count": len(repaired),
                "auto_repair": bool(auto_repair)
            }
        )
        self.context._emit_context_event(
            "kernel.context.diagnostics.completed",
            {
                "score": score,
                "status": status,
                "healthy": healthy,
                "warning_count": len(warnings),
                "error_count": len(errors)
            }
        )

        return report

    def get_history(self, limit=None):
        with self.lock:
            if limit is None:
                return deepcopy(self.history)
            return deepcopy(self.history[-max(0, int(limit)):])

    def clear_history(self):
        with self.lock:
            count = len(self.history)
            self.history.clear()
        return count

    def get_statistics(self):
        with self.lock:
            return {
                "registered_check_count": len(self.checks),
                "runs": self.runs,
                "checks_executed": self.checks_executed,
                "repairs_attempted": self.repairs_attempted,
                "repairs_completed": self.repairs_completed,
                "history_count": len(self.history),
                "history_limit": self.history_limit,
                "last_run_at": self.last_run_at,
                "last_score": (
                    self.last_report.get("score")
                    if self.last_report else None
                ),
                "last_error": self.last_error
            }

    def _register_builtin_checks(self):
        builtins = [
            ("state_validity", self._check_state_validity, 10, "Kernel state is valid."),
            ("health_range", self._check_health_range, 20, "Health score is within bounds."),
            ("lifecycle_consistency", self._check_lifecycle_consistency, 30, "Lifecycle and state agree."),
            ("boot_consistency", self._check_boot_consistency, 40, "Boot timestamps are consistent."),
            ("safe_mode_consistency", self._check_safe_mode_consistency, 50, "Safe-mode flags agree."),
            ("core_services", self._check_core_services, 60, "Core-service availability."),
            ("protected_services", self._check_protected_services, 70, "Protected service metadata."),
            ("service_aliases", self._check_service_aliases, 80, "Service aliases resolve correctly."),
            ("service_metadata", self._check_service_metadata, 90, "Registered services have metadata."),
            ("runtime_scopes", self._check_runtime_scopes, 100, "Runtime scopes are structurally valid."),
            ("expired_entries", self._check_expired_entries, 110, "Expired scope entries are cleaned."),
            ("scope_namespaces", self._check_scope_namespaces, 120, "Scope namespace indexes are consistent."),
            ("flags", self._check_flags, 130, "Global flags are valid."),
            ("shared_objects", self._check_shared_objects, 140, "Shared-object registry is valid."),
            ("metadata", self._check_metadata, 150, "Runtime metadata is valid."),
            ("resource_manager", self._check_resource_manager, 160, "Resource manager is available."),
            ("resource_health", self._check_resource_health, 170, "System-resource health."),
            ("resource_cache", self._check_resource_cache, 180, "Resource cache is structurally valid."),
            ("python_runtime", self._check_python_runtime, 190, "Python runtime is compatible."),
            ("disk_capacity", self._check_disk_capacity, 200, "Disk capacity is sufficient."),
            ("memory_capacity", self._check_memory_capacity, 210, "Memory capacity is sufficient."),
            ("timeline", self._check_timeline, 220, "Timeline entries are valid."),
            ("statistics", self._check_statistics, 230, "Counters contain valid values."),
            ("context_identity", self._check_context_identity, 240, "Context identity is complete.")
        ]
        for name, callback, priority, description in builtins:
            self.register_check(name, callback, priority, description)

    def _result(self, name, passed, severity="INFO", message="", details=None, repaired=False):
        return DiagnosticResult(name, passed, severity, message, details, repaired)

    def _check_state_validity(self, _):
        valid = self.context.status in self.context.VALID_STATES
        return self._result("state_validity", valid, "CRITICAL" if not valid else "INFO",
                            "Kernel state is valid." if valid else "Kernel state is invalid.",
                            {"status": self.context.status})

    def _check_health_range(self, auto_repair):
        health = self.context.health
        valid = isinstance(health, (int, float)) and not isinstance(health, bool) and 0 <= health <= 100
        repaired = False
        if not valid and auto_repair:
            try:
                self.context.health = max(0, min(100, int(health)))
            except Exception:
                self.context.health = 0
            valid = True
            repaired = True
        return self._result("health_range", valid, "ERROR" if not valid else "INFO",
                            "Health score is valid." if valid else "Health score is outside 0..100.",
                            {"health": self.context.health}, repaired)

    def _check_lifecycle_consistency(self, _):
        issues = []
        lc = self.context.lifecycle
        if self.context.status == "READY" and not lc.get("ready"):
            issues.append("READY state without lifecycle.ready")
        if lc.get("ready") and not lc.get("started"):
            issues.append("ready lifecycle without started lifecycle")
        if self.context.status == "OFFLINE" and lc.get("started"):
            issues.append("OFFLINE state while lifecycle.started is true")
        if self.context.status == "ERROR" and lc.get("healthy"):
            issues.append("ERROR state while lifecycle.healthy is true")
        return self._result("lifecycle_consistency", not issues, "ERROR" if issues else "INFO",
                            "Lifecycle is consistent." if not issues else "Lifecycle inconsistencies detected.",
                            {"issues": issues, "lifecycle": deepcopy(lc), "status": self.context.status})

    def _check_boot_consistency(self, _):
        issues = []
        if self.context.boot_completed_at and not self.context.boot_started_at:
            issues.append("boot completed without boot start")
        if self.context.ready_at and not self.context.boot_completed_at:
            issues.append("ready timestamp exists before boot completion")
        if self.context.lifecycle.get("started") and not self.context.boot_started_at:
            issues.append("started lifecycle without boot timestamp")
        return self._result("boot_consistency", not issues, "ERROR" if issues else "INFO",
                            "Boot state is consistent." if not issues else "Boot inconsistencies detected.",
                            {"issues": issues})

    def _check_safe_mode_consistency(self, auto_repair):
        issue = self.context.status == "SAFE_MODE" and not self.context.safe_mode
        repaired = False
        if issue and auto_repair:
            self.context.safe_mode = True
            issue = False
            repaired = True
        return self._result("safe_mode_consistency", not issue, "ERROR" if issue else "INFO",
                            "Safe mode is consistent." if not issue else "SAFE_MODE state without safe_mode flag.",
                            {"safe_mode": self.context.safe_mode, "status": self.context.status}, repaired)

    def _check_core_services(self, _):
        report = self.context.validate_core_services()
        missing = report.get("missing", [])
        severity = "ERROR" if self.context.lifecycle.get("ready") and missing else "WARNING"
        return self._result("core_services", not missing, severity if missing else "INFO",
                            "All core services are available." if not missing else "Core services are missing.",
                            report)

    def _check_protected_services(self, auto_repair):
        issues = []
        repaired = False
        for name in self.context.PROTECTED_SERVICE_NAMES:
            service = self.context.services.get(name)
            metadata = self.context.service_metadata.get(name)
            if service is not None and (not metadata or not metadata.get("protected")):
                issues.append(name)
                if auto_repair:
                    metadata = metadata or {}
                    metadata["protected"] = True
                    self.context.service_metadata[name] = metadata
                    repaired = True
        if repaired:
            issues = []
        return self._result("protected_services", not issues, "ERROR" if issues else "INFO",
                            "Protected services are marked correctly." if not issues else "Protected service metadata is invalid.",
                            {"invalid_services": issues}, repaired)

    def _check_service_aliases(self, auto_repair):
        invalid = []
        for alias, target in list(self.context.service_aliases.items()):
            if not alias or not target or target not in self.context.services:
                invalid.append(alias)
        repaired = False
        if invalid and auto_repair:
            for alias in invalid:
                self.context.service_aliases.pop(alias, None)
            repaired = True
            invalid = []
        return self._result("service_aliases", not invalid, "WARNING" if invalid else "INFO",
                            "Service aliases are valid." if not invalid else "Invalid service aliases found.",
                            {"invalid_aliases": invalid}, repaired)

    def _check_service_metadata(self, auto_repair):
        missing = []
        repaired = False
        for name, service in self.context.services.items():
            if service is not None and name not in self.context.service_metadata:
                missing.append(name)
                if auto_repair:
                    self.context.service_metadata[name] = {
                        "registered_at": datetime.now(UTC).isoformat(),
                        "replaced": False,
                        "protected": name in self.context.PROTECTED_SERVICE_NAMES,
                        "class_name": service.__class__.__name__,
                        "component_id": self.context._get_service_id(service),
                        "metadata": {"recovered_by_diagnostics": True}
                    }
                    repaired = True
        if repaired:
            missing = []
        return self._result("service_metadata", not missing, "WARNING" if missing else "INFO",
                            "Service metadata is complete." if not missing else "Registered services lack metadata.",
                            {"missing_metadata": missing}, repaired)

    def _check_runtime_scopes(self, _):
        required = {"runtime", "session", "boot", "temp"}
        missing = sorted(required - set(self.context.scopes))
        invalid = [name for name, scope in self.context.scopes.items() if not isinstance(scope, ContextScope)]
        passed = not missing and not invalid
        return self._result("runtime_scopes", passed, "CRITICAL" if not passed else "INFO",
                            "Runtime scopes are valid." if passed else "Runtime scopes are missing or invalid.",
                            {"missing": missing, "invalid": invalid})

    def _check_expired_entries(self, auto_repair):
        expired = 0
        for scope in self.context.scopes.values():
            with scope.lock:
                expired += sum(1 for entry in scope.entries.values() if scope._is_expired(entry))
        repaired = False
        if expired and auto_repair:
            self.context.cleanup_scopes()
            repaired = True
            expired = 0
        return self._result("expired_entries", expired == 0, "WARNING" if expired else "INFO",
                            "No expired runtime entries remain." if not expired else "Expired runtime entries were found.",
                            {"expired_count": expired}, repaired)

    def _check_scope_namespaces(self, auto_repair):
        issues = []
        repaired = False
        for scope_name, scope in self.context.scopes.items():
            expected = {}
            with scope.lock:
                for entry_id, entry in scope.entries.items():
                    expected.setdefault(entry["namespace"], set()).add(entry_id)
                actual = {name: set(ids) for name, ids in scope.namespaces.items()}
                if expected != actual:
                    issues.append(scope_name)
                    if auto_repair:
                        scope.namespaces = expected
                        repaired = True
        if repaired:
            issues = []
        return self._result("scope_namespaces", not issues, "ERROR" if issues else "INFO",
                            "Scope namespace indexes are valid." if not issues else "Scope namespace indexes are inconsistent.",
                            {"invalid_scopes": issues}, repaired)

    def _check_flags(self, _):
        invalid = [key for key in self.context.flags if not isinstance(key, str) or not key.strip()]
        return self._result("flags", not invalid, "WARNING" if invalid else "INFO",
                            "Flags are valid." if not invalid else "Invalid flag names found.",
                            {"invalid_flags": invalid})

    def _check_shared_objects(self, _):
        invalid = [key for key in self.context.shared if not isinstance(key, str) or not key.strip()]
        return self._result("shared_objects", not invalid, "WARNING" if invalid else "INFO",
                            "Shared-object registry is valid." if not invalid else "Invalid shared-object names found.",
                            {"invalid_names": invalid})

    def _check_metadata(self, _):
        valid = isinstance(self.context.metadata, dict)
        return self._result("metadata", valid, "ERROR" if not valid else "INFO",
                            "Runtime metadata is valid." if valid else "Runtime metadata is not a dictionary.")

    def _check_resource_manager(self, _):
        valid = isinstance(self.context.resources, ResourceManager)
        return self._result("resource_manager", valid, "CRITICAL" if not valid else "INFO",
                            "Resource manager is available." if valid else "Resource manager is unavailable.")

    def _check_resource_health(self, _):
        health = self.context.resources.health()
        status = health.get("overall", health.get("status", "UNKNOWN"))
        passed = bool(health.get("healthy", status in {"OK", "HEALTHY"}))
        severity = "WARNING" if status in {"WARNING", "DEGRADED", "UNKNOWN"} else "ERROR"
        return self._result("resource_health", passed, severity if not passed else "INFO",
                            "Resource health is acceptable." if passed else "Resource health reports issues.",
                            health)

    def _check_resource_cache(self, auto_repair):
        invalid = []
        with self.context.resources.lock:
            for key, entry in self.context.resources.cache.items():
                if not isinstance(entry, dict) or "value" not in entry or "stored_at" not in entry:
                    invalid.append(key)
            if invalid and auto_repair:
                for key in invalid:
                    self.context.resources.cache.pop(key, None)
        return self._result("resource_cache", not invalid or auto_repair, "WARNING" if invalid and not auto_repair else "INFO",
                            "Resource cache is valid." if not invalid or auto_repair else "Invalid resource-cache entries found.",
                            {"invalid_entries": [] if auto_repair else invalid}, bool(invalid and auto_repair))

    def _check_python_runtime(self, _):
        info = self.context.resources.python_info()
        version = info.get("version") or self.context.python_version
        major = int(str(version).split(".")[0]) if version else 0
        passed = major >= 3
        return self._result("python_runtime", passed, "CRITICAL" if not passed else "INFO",
                            "Python runtime is supported." if passed else "Unsupported Python runtime.",
                            info)

    def _check_disk_capacity(self, _):
        disks = self.context.resources.disk()
        entries = disks.get("entries", disks) if isinstance(disks, dict) else {}
        critical = []
        warning = []
        if isinstance(entries, dict):
            for path, data in entries.items():
                percent = data.get("percent") if isinstance(data, dict) else None
                if isinstance(percent, (int, float)):
                    if percent >= 95:
                        critical.append(path)
                    elif percent >= 85:
                        warning.append(path)
        passed = not critical and not warning
        severity = "ERROR" if critical else "WARNING"
        return self._result("disk_capacity", passed, severity if not passed else "INFO",
                            "Disk capacity is sufficient." if passed else "Disk usage is high.",
                            {"critical": critical, "warning": warning})

    def _check_memory_capacity(self, _):
        memory = self.context.resources.memory()
        percent = memory.get("percent") if isinstance(memory, dict) else None
        passed = not isinstance(percent, (int, float)) or percent < 90
        severity = "ERROR" if isinstance(percent, (int, float)) and percent >= 97 else "WARNING"
        return self._result("memory_capacity", passed, severity if not passed else "INFO",
                            "Memory capacity is sufficient." if passed else "Memory usage is high.",
                            memory if isinstance(memory, dict) else {})

    def _check_timeline(self, auto_repair):
        invalid_indexes = []
        with self.context.lock:
            for index, entry in enumerate(self.context.timeline):
                if not isinstance(entry, dict) or not entry.get("event_type") or not entry.get("timestamp"):
                    invalid_indexes.append(index)
            if invalid_indexes and auto_repair:
                self.context.timeline = [
                    entry for index, entry in enumerate(self.context.timeline)
                    if index not in set(invalid_indexes)
                ]
        return self._result("timeline", not invalid_indexes or auto_repair,
                            "ERROR" if invalid_indexes and not auto_repair else "INFO",
                            "Timeline is valid." if not invalid_indexes or auto_repair else "Invalid timeline entries found.",
                            {"invalid_indexes": [] if auto_repair else invalid_indexes},
                            bool(invalid_indexes and auto_repair))

    def _check_statistics(self, _):
        stats = self.context.get_statistics()
        invalid = [key for key, value in stats.items() if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0]
        return self._result("statistics", not invalid, "ERROR" if invalid else "INFO",
                            "Statistics are valid." if not invalid else "Negative counters found.",
                            {"negative_values": invalid})

    def _check_context_identity(self, _):
        fields = ["component_id", "name", "version", "author", "mission", "kernel_version", "boot_id"]
        missing = [field for field in fields if not getattr(self.context, field, None)]
        return self._result("context_identity", not missing, "CRITICAL" if missing else "INFO",
                            "Context identity is complete." if not missing else "Context identity is incomplete.",
                            {"missing_fields": missing})

    @staticmethod
    def _normalize_name(name):
        if not isinstance(name, str):
            return None
        normalized = name.strip().lower()
        return normalized or None


