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


class ResourceManager:

    VERSION = "1.0.0"

    FEATURE_MODULES = {
        "numpy": "numpy",
        "pytorch": "torch",
        "onnxruntime": "onnxruntime",
        "whisper": "whisper",
        "opencv": "cv2",
        "pillow": "PIL",
        "psutil": "psutil",
        "piper": "piper",
        "coqui_tts": "TTS"
    }

    FEATURE_COMMANDS = {
        "ffmpeg": "ffmpeg",
        "git": "git",
        "docker": "docker",
        "nvidia_smi": "nvidia-smi"
    }

    def __init__(self, context=None, cache_ttl=5.0):
        self.component_id = "core.resource_manager"
        self.name = "Kernel Resource Manager"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.context = context
        self.cache_ttl = max(float(cache_ttl), 0.0)
        self.lock = RLock()
        self.cache = {}
        self.refresh_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = 0
        self.last_error = None
        self.created_at = datetime.now(UTC).isoformat()
        self.last_refresh_at = None

    def refresh(self):
        snapshot = {
            "cpu": self.refresh_cpu(),
            "memory": self.refresh_memory(),
            "disk": self.refresh_disk(),
            "network": self.refresh_network(),
            "os": self.refresh_os(),
            "python": self.refresh_python(),
            "gpu": self.refresh_gpu(),
            "features": self.refresh_features()
        }
        with self.lock:
            self.refresh_count += 1
            self.last_refresh_at = datetime.now(UTC).isoformat()
        self._notify("KERNEL_RESOURCES_REFRESHED", {"sections": list(snapshot)})
        return deepcopy(snapshot)

    def refresh_cpu(self):
        data = self._collect_cpu()
        self._cache_set("cpu", data)
        return deepcopy(data)

    def refresh_memory(self):
        data = self._collect_memory()
        self._cache_set("memory", data)
        return deepcopy(data)

    def refresh_disk(self, path=None):
        data = self._collect_disk(path)
        self._cache_set("disk", data)
        return deepcopy(data)

    def refresh_network(self):
        data = self._collect_network()
        self._cache_set("network", data)
        return deepcopy(data)

    def refresh_os(self):
        data = self._collect_os()
        self._cache_set("os", data)
        return deepcopy(data)

    def refresh_python(self):
        data = self._collect_python()
        self._cache_set("python", data)
        return deepcopy(data)

    def refresh_gpu(self):
        data = self._collect_gpu()
        self._cache_set("gpu", data)
        return deepcopy(data)

    def refresh_features(self):
        data = self._collect_features()
        self._cache_set("features", data)
        return deepcopy(data)

    def cpu(self, refresh=False):
        return self._get_section("cpu", self._collect_cpu, refresh)

    def memory(self, refresh=False):
        return self._get_section("memory", self._collect_memory, refresh)

    def disk(self, path=None, refresh=False):
        if path is not None:
            return self._collect_disk(path)
        return self._get_section("disk", self._collect_disk, refresh)

    def network(self, refresh=False):
        return self._get_section("network", self._collect_network, refresh)

    def os_info(self, refresh=False):
        return self._get_section("os", self._collect_os, refresh)

    def python_info(self, refresh=False):
        return self._get_section("python", self._collect_python, refresh)

    def gpu(self, refresh=False):
        return self._get_section("gpu", self._collect_gpu, refresh)

    def features(self, refresh=False):
        return self._get_section("features", self._collect_features, refresh)

    def has_gpu(self):
        return bool(self.gpu().get("available"))

    def gpu_count(self):
        return int(self.gpu().get("count", 0))

    def gpu_names(self):
        return list(self.gpu().get("names", []))

    def has_feature(self, name):
        normalized = str(name).strip().lower()
        return bool(self.features().get(normalized, {}).get("available"))

    def has_cuda(self):
        return bool(self.features().get("cuda", {}).get("available"))

    def memory_available(self):
        return self.memory().get("available_bytes")

    def disk_free(self, path="/"):
        return self.disk(path=path).get("free_bytes")

    def snapshot(self, refresh=False):
        if refresh:
            self.refresh()
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "cpu": self.cpu(),
            "memory": self.memory(),
            "disk": self.disk(),
            "network": self.network(),
            "os": self.os_info(),
            "python": self.python_info(),
            "gpu": self.gpu(),
            "features": self.features(),
            "health": self.health()
        }

    def health(self):
        memory = self.memory()
        disks = self.disk().get("mounts", {})
        memory_percent = memory.get("percent")
        disk_percentages = [
            item.get("percent") for item in disks.values()
            if isinstance(item.get("percent"), (int, float))
        ]
        max_disk = max(disk_percentages, default=None)

        def level(percent):
            if percent is None:
                return "UNKNOWN"
            if percent >= 95:
                return "CRITICAL"
            if percent >= 85:
                return "WARNING"
            return "OK"

        sections = {
            "cpu": "OK" if self.cpu().get("logical_cores") else "UNKNOWN",
            "memory": level(memory_percent),
            "disk": level(max_disk),
            "gpu": "OK" if self.has_gpu() else "NOT_AVAILABLE"
        }
        overall = "OK"
        if "CRITICAL" in sections.values():
            overall = "CRITICAL"
        elif "WARNING" in sections.values():
            overall = "WARNING"
        elif "UNKNOWN" in sections.values():
            overall = "DEGRADED"
        return {"overall": overall, "sections": sections, "healthy": overall in {"OK", "WARNING"}}

    def report(self, refresh=False):
        return {
            "component_id": self.component_id,
            "version": self.version,
            "snapshot": self.snapshot(refresh=refresh),
            "statistics": self.get_statistics(),
            "last_error": deepcopy(self.last_error)
        }

    def clear_cache(self):
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
        return count

    def get_statistics(self):
        with self.lock:
            return {
                "cache_entry_count": len(self.cache),
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "refresh_count": self.refresh_count,
                "errors": self.errors,
                "cache_ttl_seconds": self.cache_ttl,
                "created_at": self.created_at,
                "last_refresh_at": self.last_refresh_at
            }

    def _get_section(self, name, collector, refresh=False):
        if not refresh:
            cached = self._cache_get(name)
            if cached is not None:
                return cached
        try:
            data = collector()
            self._cache_set(name, data)
            return deepcopy(data)
        except Exception as error:
            self._record_error(error)
            return {"available": False, "error": str(error)}

    def _cache_get(self, name):
        with self.lock:
            item = self.cache.get(name)
            if item is None:
                self.cache_misses += 1
                return None
            if self.cache_ttl and time.monotonic() - item["stored_at"] > self.cache_ttl:
                self.cache.pop(name, None)
                self.cache_misses += 1
                return None
            self.cache_hits += 1
            return deepcopy(item["value"])

    def _cache_set(self, name, value):
        with self.lock:
            self.cache[name] = {"value": deepcopy(value), "stored_at": time.monotonic()}

    def _collect_cpu(self):
        logical = os.cpu_count()
        physical = None
        load = None
        try:
            import psutil
            physical = psutil.cpu_count(logical=False)
            load = psutil.cpu_percent(interval=None)
        except Exception:
            if hasattr(os, "getloadavg"):
                try:
                    load = list(os.getloadavg())
                except OSError:
                    load = None
        return {
            "available": logical is not None,
            "logical_cores": logical,
            "physical_cores": physical,
            "architecture": platform.machine(),
            "processor": platform.processor() or None,
            "load": load
        }

    def _collect_memory(self):
        total = available = used = percent = None
        try:
            import psutil
            memory = psutil.virtual_memory()
            total, available, used, percent = memory.total, memory.available, memory.used, memory.percent
        except Exception:
            if sys.platform.startswith("linux"):
                values = {}
                try:
                    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                        for line in handle:
                            key, value = line.split(":", 1)
                            values[key] = int(value.strip().split()[0]) * 1024
                    total = values.get("MemTotal")
                    available = values.get("MemAvailable")
                    if total is not None and available is not None:
                        used = total - available
                        percent = round((used / total) * 100, 2) if total else 0.0
                except (OSError, ValueError):
                    pass
        return {
            "available": total is not None,
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used,
            "percent": percent
        }

    def _collect_disk(self, path=None):
        targets = [path] if path is not None else self._disk_targets()
        mounts = {}
        for target in targets:
            try:
                usage = shutil.disk_usage(target)
                percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0.0
                mounts[str(target)] = {
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": percent
                }
            except OSError as error:
                mounts[str(target)] = {"error": str(error)}
        if path is not None:
            return mounts[str(path)]
        return {"available": bool(mounts), "mounts": mounts}

    def _disk_targets(self):
        targets = [os.path.abspath(os.sep)]
        try:
            import psutil
            for partition in psutil.disk_partitions(all=False):
                if partition.mountpoint not in targets:
                    targets.append(partition.mountpoint)
        except Exception:
            pass
        return targets

    def _collect_network(self):
        addresses = []
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None)})
        except OSError:
            pass
        return {
            "available": True,
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "addresses": addresses
        }

    def _collect_os(self):
        return {
            "available": True,
            "name": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "hostname": socket.gethostname()
        }

    def _collect_python(self):
        return {
            "available": True,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "bits": 64 if sys.maxsize > 2**32 else 32,
            "build": list(platform.python_build()),
            "compiler": platform.python_compiler()
        }

    def _collect_gpu(self):
        names = []
        details = []
        command = shutil.which("nvidia-smi")
        if command:
            try:
                result = subprocess.run(
                    [command, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = [part.strip() for part in line.split(",")]
                        if parts and parts[0]:
                            names.append(parts[0])
                            details.append({
                                "name": parts[0],
                                "memory_total_mb": self._to_number(parts[1]) if len(parts) > 1 else None,
                                "driver_version": parts[2] if len(parts) > 2 else None,
                                "vendor": "NVIDIA"
                            })
            except (OSError, subprocess.SubprocessError):
                pass
        if not names and sys.platform.startswith("linux"):
            lspci = shutil.which("lspci")
            if lspci:
                try:
                    result = subprocess.run([lspci], capture_output=True, text=True, timeout=3, check=False)
                    for line in result.stdout.splitlines():
                        lower = line.lower()
                        if "vga compatible controller" in lower or "3d controller" in lower:
                            name = line.split(": ", 1)[-1].strip()
                            names.append(name)
                            details.append({"name": name, "vendor": None})
                except (OSError, subprocess.SubprocessError):
                    pass
        return {"available": bool(names), "count": len(names), "names": names, "devices": details}

    def _collect_features(self):
        features = {}
        for name, module in self.FEATURE_MODULES.items():
            spec = importlib.util.find_spec(module)
            features[name] = {"available": spec is not None, "source": "python_module", "target": module}
        for name, command in self.FEATURE_COMMANDS.items():
            path = shutil.which(command)
            features[name] = {"available": path is not None, "source": "command", "path": path}
        cuda_available = features.get("nvidia_smi", {}).get("available", False)
        if features.get("pytorch", {}).get("available"):
            try:
                import torch
                cuda_available = bool(torch.cuda.is_available())
            except Exception:
                pass
        features["cuda"] = {"available": cuda_available, "source": "runtime_detection"}
        return features

    def _record_error(self, error):
        with self.lock:
            self.errors += 1
            self.last_error = {"message": str(error), "timestamp": datetime.now(UTC).isoformat()}

    def _notify(self, event_type, payload):
        context = self.context
        if context is not None and hasattr(context, "add_timeline_event"):
            try:
                context.add_timeline_event(event_type, payload)
            except Exception:
                pass

    @staticmethod
    def _to_number(value):
        try:
            number = float(value)
            return int(number) if number.is_integer() else number
        except (TypeError, ValueError):
            return None



