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


class ContextScope:

    VERSION = "1.0.0"

    def __init__(
        self,
        name,
        default_ttl=None,
        allow_objects=True
    ):
        self.name = str(name).strip().lower()
        self.default_ttl = default_ttl
        self.allow_objects = bool(allow_objects)

        self.entries = {}
        self.namespaces = {}
        self.lock = RLock()

        self.created_count = 0
        self.updated_count = 0
        self.deleted_count = 0
        self.expired_count = 0
        self.lookup_count = 0
        self.lookup_misses = 0
        self.cleanup_count = 0
        self.clear_count = 0

        self.created_at = datetime.now(UTC).isoformat()
        self.last_change_at = None
        self.last_cleanup_at = None
        self.last_error = None

    def set(
        self,
        key,
        value,
        ttl=None,
        namespace="default",
        replace=True,
        metadata=None
    ):
        key = self._normalize_name(key)
        namespace = self._normalize_name(namespace)

        if key is None or namespace is None:
            return False

        ttl_value = self._normalize_ttl(
            self.default_ttl if ttl is None else ttl
        )

        now_monotonic = time.monotonic()
        timestamp = datetime.now(UTC).isoformat()
        expires_at = (
            now_monotonic + ttl_value
            if ttl_value is not None
            else None
        )

        entry_id = self._entry_id(namespace, key)

        with self.lock:
            exists = entry_id in self.entries

            if exists and not replace:
                self.last_error = (
                    f"Entry '{namespace}.{key}' already exists."
                )
                return False

            self.entries[entry_id] = {
                "key": key,
                "namespace": namespace,
                "value": value,
                "created_at": (
                    self.entries[entry_id]["created_at"]
                    if exists
                    else timestamp
                ),
                "updated_at": timestamp,
                "expires_at_monotonic": expires_at,
                "ttl": ttl_value,
                "metadata": deepcopy(metadata or {})
            }

            self.namespaces.setdefault(
                namespace,
                set()
            ).add(entry_id)

            if exists:
                self.updated_count += 1
            else:
                self.created_count += 1

            self.last_change_at = timestamp
            self.last_error = None

        return True

    def get(
        self,
        key,
        default=None,
        namespace="default"
    ):
        key = self._normalize_name(key)
        namespace = self._normalize_name(namespace)

        if key is None or namespace is None:
            return default

        entry_id = self._entry_id(namespace, key)

        with self.lock:
            self.lookup_count += 1
            entry = self.entries.get(entry_id)

            if entry is None:
                self.lookup_misses += 1
                return default

            if self._is_expired(entry):
                self._delete_entry_locked(entry_id, expired=True)
                self.lookup_misses += 1
                return default

            return entry["value"]

    def get_entry(
        self,
        key,
        namespace="default"
    ):
        key = self._normalize_name(key)
        namespace = self._normalize_name(namespace)

        if key is None or namespace is None:
            return None

        entry_id = self._entry_id(namespace, key)

        with self.lock:
            entry = self.entries.get(entry_id)

            if entry is None:
                return None

            if self._is_expired(entry):
                self._delete_entry_locked(entry_id, expired=True)
                return None

            result = deepcopy(entry)
            result.pop("expires_at_monotonic", None)
            result["remaining_ttl"] = self._remaining_ttl(entry)
            return result

    def has(
        self,
        key,
        namespace="default"
    ):
        marker = object()
        return self.get(
            key=key,
            default=marker,
            namespace=namespace
        ) is not marker

    def delete(
        self,
        key,
        namespace="default"
    ):
        key = self._normalize_name(key)
        namespace = self._normalize_name(namespace)

        if key is None or namespace is None:
            return False

        entry_id = self._entry_id(namespace, key)

        with self.lock:
            if entry_id not in self.entries:
                return False

            self._delete_entry_locked(entry_id)
            return True

    def clear_namespace(self, namespace):
        namespace = self._normalize_name(namespace)

        if namespace is None:
            return 0

        with self.lock:
            entry_ids = list(
                self.namespaces.get(namespace, set())
            )

            for entry_id in entry_ids:
                self._delete_entry_locked(entry_id)

            self.namespaces.pop(namespace, None)
            return len(entry_ids)

    def clear(self):
        with self.lock:
            removed = len(self.entries)
            self.entries.clear()
            self.namespaces.clear()
            self.clear_count += 1
            self.last_change_at = datetime.now(UTC).isoformat()
            return removed

    def cleanup_expired(self):
        with self.lock:
            expired_ids = [
                entry_id
                for entry_id, entry in self.entries.items()
                if self._is_expired(entry)
            ]

            for entry_id in expired_ids:
                self._delete_entry_locked(
                    entry_id,
                    expired=True
                )

            self.cleanup_count += 1
            self.last_cleanup_at = datetime.now(UTC).isoformat()
            return len(expired_ids)

    def list_namespaces(self):
        self.cleanup_expired()

        with self.lock:
            return sorted(
                namespace
                for namespace, entry_ids in self.namespaces.items()
                if entry_ids
            )

    def list_keys(self, namespace="default"):
        namespace = self._normalize_name(namespace)

        if namespace is None:
            return []

        self.cleanup_expired()

        with self.lock:
            return sorted(
                self.entries[entry_id]["key"]
                for entry_id in self.namespaces.get(
                    namespace,
                    set()
                )
                if entry_id in self.entries
            )

    def snapshot(
        self,
        namespace=None,
        include_metadata=False
    ):
        self.cleanup_expired()

        with self.lock:
            result = {}

            for entry in self.entries.values():
                if (
                    namespace is not None
                    and entry["namespace"] != namespace
                ):
                    continue

                namespace_data = result.setdefault(
                    entry["namespace"],
                    {}
                )

                if include_metadata:
                    entry_data = deepcopy(entry)
                    entry_data.pop(
                        "expires_at_monotonic",
                        None
                    )
                    entry_data["remaining_ttl"] = (
                        self._remaining_ttl(entry)
                    )
                    namespace_data[entry["key"]] = entry_data
                else:
                    namespace_data[entry["key"]] = entry["value"]

            return result

    def get_statistics(self):
        self.cleanup_expired()

        with self.lock:
            return {
                "scope": self.name,
                "entry_count": len(self.entries),
                "namespace_count": len(
                    [
                        namespace
                        for namespace, entry_ids
                        in self.namespaces.items()
                        if entry_ids
                    ]
                ),
                "created_count": self.created_count,
                "updated_count": self.updated_count,
                "deleted_count": self.deleted_count,
                "expired_count": self.expired_count,
                "lookup_count": self.lookup_count,
                "lookup_misses": self.lookup_misses,
                "cleanup_count": self.cleanup_count,
                "clear_count": self.clear_count,
                "default_ttl": self.default_ttl,
                "created_at": self.created_at,
                "last_change_at": self.last_change_at,
                "last_cleanup_at": self.last_cleanup_at,
                "last_error": self.last_error
            }

    def _delete_entry_locked(
        self,
        entry_id,
        expired=False
    ):
        entry = self.entries.pop(entry_id, None)

        if entry is None:
            return False

        namespace = entry["namespace"]
        namespace_entries = self.namespaces.get(namespace)

        if namespace_entries is not None:
            namespace_entries.discard(entry_id)

            if not namespace_entries:
                self.namespaces.pop(namespace, None)

        if expired:
            self.expired_count += 1
        else:
            self.deleted_count += 1

        self.last_change_at = datetime.now(UTC).isoformat()
        return True

    def _is_expired(self, entry):
        expires_at = entry.get("expires_at_monotonic")

        return (
            expires_at is not None
            and time.monotonic() >= expires_at
        )

    def _remaining_ttl(self, entry):
        expires_at = entry.get("expires_at_monotonic")

        if expires_at is None:
            return None

        return max(
            0.0,
            round(expires_at - time.monotonic(), 6)
        )

    def _normalize_ttl(self, ttl):
        if ttl is None:
            return None

        try:
            ttl = float(ttl)
        except (TypeError, ValueError):
            self.last_error = "TTL must be numeric or None."
            return None

        if ttl <= 0:
            self.last_error = "TTL must be greater than zero."
            return None

        return ttl

    def _normalize_name(self, name):
        if not isinstance(name, str):
            self.last_error = "Name must be a string."
            return None

        normalized = name.strip().lower()

        if not normalized:
            self.last_error = "Name must not be empty."
            return None

        return normalized

    def _entry_id(self, namespace, key):
        return f"{namespace}:{key}"


