class LifecycleTransaction:
    def __init__(self): self.actions=[]
    def record(self, action): self.actions.append(action)
