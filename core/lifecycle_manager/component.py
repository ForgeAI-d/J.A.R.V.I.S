from core.base_manager import BaseManager
class LifecycleManager(BaseManager):
    COMPONENT_ID=MANAGER_ID="core.lifecycle_manager"; NAME="Lifecycle Manager"; VERSION="1.0.0"; PRIORITY=3; AUTO_START=True
    def initialize_component(self, component): return component.initialize() is not False
    def start_component(self, component): return component.start() is not False
    def stop_component(self, component): return component.stop() is not False
    def start_ordered(self, components, order):
        started=[]
        for cid in order:
            component=components.get(cid)
            if component is None or not getattr(component,"auto_start",True): continue
            if not self.initialize_component(component) or not self.start_component(component): return {"success":False,"started":started,"failed":cid}
            started.append(cid)
        return {"success":True,"started":started,"failed":None}
    def stop_ordered(self, components, order):
        stopped=[]; failed=[]
        for cid in order:
            component=components.get(cid)
            if component is None: continue
            (stopped if self.stop_component(component) else failed).append(cid)
        return {"success":not failed,"stopped":stopped,"failed":failed}
