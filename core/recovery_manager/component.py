from core.base_manager import BaseManager
class RecoveryManager(BaseManager):
    COMPONENT_ID=MANAGER_ID="core.recovery_manager"; NAME="Recovery Manager"; VERSION="1.0.0"; PRIORITY=4; AUTO_START=True
    def __init__(self, context=None, max_restarts=1): super().__init__(context=context); self.max_restarts=max_restarts; self.attempts={}; self.isolated=set()
    def recover(self, component):
        cid=component.component_id; count=self.attempts.get(cid,0)
        if count>=self.max_restarts: self.isolated.add(cid); return {"recovered":False,"isolated":True,"component_id":cid}
        self.attempts[cid]=count+1
        try:
            component.stop(); ok=component.initialize() is not False and component.start() is not False
        except Exception: ok=False
        if not ok and self.attempts[cid]>=self.max_restarts: self.isolated.add(cid)
        return {"recovered":ok,"isolated":cid in self.isolated,"component_id":cid}
