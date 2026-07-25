from copy import deepcopy
from datetime import datetime, UTC
from threading import RLock
import time


class ConfigCache:

    VERSION = "1.0.0"

    def __init__(
        self,
        default_ttl=None,
        max_entries=1000
    ):
        self.name = "Config Cache"
        self.component_id = "core.config_cache"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Thread-sicherer Speicher-Cache für das "
            "J.A.R.V.I.S.-Konfigurationssystem."
        )

        self.default_ttl = default_ttl
        self.max_entries = max_entries

        self.cache = {}
        self.access_order = []

        self.lock = RLock()

        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.deletes = 0
        self.expired_entries = 0
        self.evicted_entries = 0
        self.clear_count = 0

        self.created_at = datetime.now(UTC).isoformat()
        self.last_read_at = None
        self.last_write_at = None
        self.last_cleanup_at = None
        self.last_error = None

        self.capabilities = [
            "cache_get",
            "cache_set",
            "cache_delete",
            "cache_expiration",
            "cache_cleanup",
            "cache_lru_eviction",
            "cache_statistics",
            "thread_safe_access"
        ]

    def set(
        self,
        namespace,
        value,
        ttl=None
    ):
        if not isinstance(namespace, str) or not namespace:
            self.last_error = "Namespace must be a non-empty string."
            return False

        if ttl is None:
            ttl = self.default_ttl

        created_at = time.monotonic()

        expires_at = None

        if ttl is not None:
            try:
                ttl = float(ttl)

                if ttl <= 0:
                    self.last_error = "TTL must be greater than zero."
                    return False

                expires_at = created_at + ttl

            except (TypeError, ValueError):
                self.last_error = "TTL must be numeric or None."
                return False

        with self.lock:
            if namespace not in self.cache:
                self._ensure_capacity()

            self.cache[namespace] = {
                "value": deepcopy(value),
                "created_at": created_at,
                "expires_at": expires_at,
                "last_accessed_at": created_at,
                "access_count": 0
            }

            self._touch(namespace)

            self.writes += 1
            self.last_write_at = datetime.now(UTC).isoformat()
            self.last_error = None

        return True

    def get(
        self,
        namespace,
        default=None
    ):
        with self.lock:
            entry = self.cache.get(namespace)

            if entry is None:
                self.misses += 1
                self.last_read_at = datetime.now(UTC).isoformat()
                return deepcopy(default)

            if self._is_expired(entry):
                self._delete_internal(namespace)
                self.expired_entries += 1
                self.misses += 1
                self.last_read_at = datetime.now(UTC).isoformat()

                return deepcopy(default)

            now = time.monotonic()

            entry["last_accessed_at"] = now
            entry["access_count"] += 1

            self._touch(namespace)

            self.hits += 1
            self.last_read_at = datetime.now(UTC).isoformat()

            return deepcopy(entry["value"])

    def has(
        self,
        namespace
    ):
        with self.lock:
            entry = self.cache.get(namespace)

            if entry is None:
                return False

            if self._is_expired(entry):
                self._delete_internal(namespace)
                self.expired_entries += 1
                return False

            return True

    def delete(
        self,
        namespace
    ):
        with self.lock:
            if namespace not in self.cache:
                return False

            self._delete_internal(namespace)

            self.deletes += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def clear(self):
        with self.lock:
            self.cache.clear()
            self.access_order.clear()

            self.clear_count += 1
            self.last_write_at = datetime.now(UTC).isoformat()

        return True

    def cleanup_expired(self):
        with self.lock:
            expired_namespaces = [
                namespace
                for namespace, entry in self.cache.items()
                if self._is_expired(entry)
            ]

            for namespace in expired_namespaces:
                self._delete_internal(namespace)

            self.expired_entries += len(expired_namespaces)
            self.last_cleanup_at = datetime.now(UTC).isoformat()

        return len(expired_namespaces)

    def update_ttl(
        self,
        namespace,
        ttl
    ):
        try:
            ttl = float(ttl)

            if ttl <= 0:
                self.last_error = "TTL must be greater than zero."
                return False

        except (TypeError, ValueError):
            self.last_error = "TTL must be numeric."
            return False

        with self.lock:
            entry = self.cache.get(namespace)

            if entry is None:
                return False

            if self._is_expired(entry):
                self._delete_internal(namespace)
                self.expired_entries += 1
                return False

            entry["expires_at"] = time.monotonic() + ttl

            self._touch(namespace)

            self.last_write_at = datetime.now(UTC).isoformat()
            self.last_error = None

        return True

    def list_namespaces(self):
        self.cleanup_expired()

        with self.lock:
            return list(self.access_order)

    def get_entry_info(
        self,
        namespace
    ):
        with self.lock:
            entry = self.cache.get(namespace)

            if entry is None:
                return None

            if self._is_expired(entry):
                self._delete_internal(namespace)
                self.expired_entries += 1
                return None

            remaining_ttl = None

            if entry["expires_at"] is not None:
                remaining_ttl = max(
                    0,
                    entry["expires_at"] - time.monotonic()
                )

            return {
                "namespace": namespace,
                "access_count": entry["access_count"],
                "remaining_ttl_seconds": remaining_ttl,
                "has_expiration": entry["expires_at"] is not None
            }

    def get_statistics(self):
        with self.lock:
            total_reads = self.hits + self.misses

            if total_reads == 0:
                hit_rate = 0
            else:
                hit_rate = round(
                    self.hits / total_reads * 100,
                    2
                )

            return {
                "entry_count": len(self.cache),
                "max_entries": self.max_entries,
                "default_ttl": self.default_ttl,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": hit_rate,
                "writes": self.writes,
                "deletes": self.deletes,
                "expired_entries": self.expired_entries,
                "evicted_entries": self.evicted_entries,
                "clear_count": self.clear_count,
                "created_at": self.created_at,
                "last_read_at": self.last_read_at,
                "last_write_at": self.last_write_at,
                "last_cleanup_at": self.last_cleanup_at
            }

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "mission": self.mission,
            "capabilities": deepcopy(self.capabilities)
        }

    def get_status(self):
        return {
            "manifest": self.get_manifest(),
            "statistics": self.get_statistics(),
            "namespaces": self.list_namespaces(),
            "last_error": self.last_error
        }

    def _is_expired(
        self,
        entry
    ):
        expires_at = entry.get("expires_at")

        if expires_at is None:
            return False

        return time.monotonic() >= expires_at

    def _touch(
        self,
        namespace
    ):
        if namespace in self.access_order:
            self.access_order.remove(namespace)

        self.access_order.append(namespace)

    def _ensure_capacity(self):
        if self.max_entries is None:
            return

        while len(self.cache) >= self.max_entries:
            if not self.access_order:
                break

            oldest_namespace = self.access_order[0]
            self._delete_internal(oldest_namespace)
            self.evicted_entries += 1

    def _delete_internal(
        self,
        namespace
    ):
        self.cache.pop(namespace, None)

        if namespace in self.access_order:
            self.access_order.remove(namespace)


if __name__ == "__main__":
    cache = ConfigCache(
        default_ttl=60,
        max_entries=3
    )

    cache.set(
        namespace="boot",
        value={
            "boot_mode": "development"
        }
    )

    cache.set(
        namespace="logger",
        value={
            "level": "INFO"
        }
    )

    print("=== CONFIG CACHE TEST ===")
    print()

    print("Boot Config:")
    print(
        cache.get("boot")
    )

    print()
    print("Boot vorhanden:")
    print(
        cache.has("boot")
    )

    print()
    print("Namespaces:")
    print(
        cache.list_namespaces()
    )

    print()
    print("Entry Info:")
    print(
        cache.get_entry_info("boot")
    )

    print()
    print("Status:")
    print(
        cache.get_status()
    )