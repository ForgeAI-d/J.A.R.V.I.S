from __future__ import annotations
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from core.base_manager import BaseManager

class ComponentRegistry(BaseManager):
    COMPONENT_ID = MANAGER_ID = "core.component_registry"
    NAME = "Component Registry"
    VERSION = "1.0.0"
    PRIORITY = 5
    AUTO_START = True
    CAPABILITIES = ("component_registration","component_query","runtime_snapshot")

    def __init__(self, context=None):
        super().__init__(context=context)
        self._components: dict[str, dict[str, Any]] = {}
        self._registry_lock = RLock()

    def register_component(self, component, *, replace=False, source=None):
        cid=getattr(component,"component_id",None) or getattr(component,"manager_id",None) or getattr(component,"engine_id",None)
        if not cid: raise ValueError("component has no canonical identifier")
        with self._registry_lock:
            if cid in self._components and not replace: return False
            manifest=component.get_manifest() if callable(getattr(component,"get_manifest",None)) else {}
            self._components[cid]={"instance":component,"manifest":deepcopy(manifest),"source":source,
                "registered_at":datetime.now(UTC).isoformat()}
        self.add_timeline_event("COMPONENT_REGISTERED", {"component_id":cid})
        return True

    def unregister_component(self, component_id):
        with self._registry_lock:
            existed=self._components.pop(component_id,None) is not None
        if existed: self.add_timeline_event("COMPONENT_UNREGISTERED", {"component_id":component_id})
        return existed

    def get(self, component_id, default=None):
        with self._registry_lock: item=self._components.get(component_id)
        return default if item is None else item["instance"]

    def contains(self, component_id):
        with self._registry_lock: return component_id in self._components

    def list_components(self, kind=None):
        with self._registry_lock: values=list(self._components.items())
        if kind is None: return [cid for cid,_ in values]
        target=str(getattr(kind,"value",kind)).lower()
        return [cid for cid,data in values if str(data["manifest"].get("kind","")).lower()==target]

    def get_all(self):
        with self._registry_lock: return {cid:data["instance"] for cid,data in self._components.items()}

    def get_manifest(self, component_id=None):
        if component_id is None: return super().get_manifest()
        with self._registry_lock: item=self._components.get(component_id)
        return None if item is None else deepcopy(item["manifest"])

    def register_manager(self, manager): return self.register_component(manager, replace=True)
    def register_engine(self, engine, manager_id=None): return self.register_component(engine, replace=True)
    def register_service(self, service_id, service_data):
        component=service_data.get("instance") if isinstance(service_data,dict) else service_data
        if component is None: return False
        return self.register_component(component, replace=True, source=service_id)
    def get_manager(self, manager_id): return self.get(manager_id)
    def get_engine(self, engine_id): return self.get(engine_id)
    def list_managers(self): return self.list_components("manager")
    def list_engines(self): return self.list_components("engine")
    def list_services(self): return self.list_components("service")
    def update_runtime(self): return True
    def get_all_status(self):
        return {cid:(obj.get_status() if callable(getattr(obj,"get_status",None)) else {}) for cid,obj in self.get_all().items()}
    def get_health_summary(self):
        statuses=self.get_all_status(); total=len(statuses)
        healthy=sum(1 for s in statuses.values() if (s.get("health",{}).get("healthy") if isinstance(s.get("health"),dict) else bool(s.get("health"))))
        return {"healthy": healthy==total, "healthy_components":healthy, "component_count":total}
