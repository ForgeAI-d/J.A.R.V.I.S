from core.common import BaseKernelComponent
from core.kernel_runtime import KernelRuntime
class JarvisCore(BaseKernelComponent):
    COMPONENT_ID="core.jarvis_core"; NAME="J.A.R.V.I.S. Core"; VERSION="0.2.0-alpha"; AUTO_START=False
    def __init__(self, runtime=None, **runtime_kwargs):
        super().__init__(); self.runtime=runtime or KernelRuntime(**runtime_kwargs); self.running=False
    def start(self):
        result=self.runtime.boot(print_report=False); self.running=result["success"]; self.status="RUNNING" if self.running else "ERROR"; return self.running
    def shutdown(self):
        result=self.runtime.shutdown(); self.running=False; self.status="STOPPED" if result["success"] else "ERROR"; return result["success"]
    def restart(self):
        result=self.runtime.restart(print_report=False); self.running=result["success"]; return self.running
    def get_status(self): return {"name":self.NAME,"version":self.VERSION,"running":self.running,"runtime":self.runtime.get_runtime_report()}
    def get_health_report(self): return self.runtime.boot_loader.health_check()
    def report(self): return self.get_status()
