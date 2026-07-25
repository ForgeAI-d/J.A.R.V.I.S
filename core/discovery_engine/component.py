from __future__ import annotations
import importlib, inspect, pkgutil
from typing import Iterable
from core.base_engine import BaseEngine
from core.base_manager import BaseManager
from core.common import BaseKernelComponent

class DiscoveryEngine(BaseEngine):
    COMPONENT_ID = ENGINE_ID = "core.discovery_engine"
    NAME="Discovery Engine"; VERSION="1.0.0"; MANAGER="core.boot_loader"; AUTO_START=False; PRIORITY=1
    CAPABILITIES=("package_scan","component_class_discovery","safe_import")
    EXCLUDED_PARTS=(".tests", ".test", "__pycache__", ".legacy")

    def discover(self, packages: Iterable[str]):
        found=[]; errors=[]
        for package_name in packages:
            try: package=importlib.import_module(package_name)
            except ModuleNotFoundError: continue
            except BaseException as exc:
                errors.append({"module":package_name,"error":str(exc)}); continue
            modules=[package]
            if hasattr(package,"__path__"):
                for info in pkgutil.walk_packages(package.__path__, package.__name__+"."):
                    if any(part in info.name for part in self.EXCLUDED_PARTS): continue
                    try: modules.append(importlib.import_module(info.name))
                    except (SystemExit,KeyboardInterrupt) as exc: errors.append({"module":info.name,"error":f"blocked process exit: {exc}"})
                    except Exception as exc: errors.append({"module":info.name,"error":str(exc)})
            for module in modules:
                for _,cls in inspect.getmembers(module,inspect.isclass):
                    if cls.__module__ != module.__name__: continue
                    try:
                        if issubclass(cls,(BaseManager,BaseEngine,BaseKernelComponent)) and cls not in (BaseManager,BaseEngine,BaseKernelComponent,DiscoveryEngine): found.append((cls,module.__name__))
                    except TypeError: pass
        unique={getattr(cls,"COMPONENT_ID",f"{cls.__module__}.{cls.__name__}"):(cls,src) for cls,src in found}
        return {"components":list(unique.values()),"errors":errors}
