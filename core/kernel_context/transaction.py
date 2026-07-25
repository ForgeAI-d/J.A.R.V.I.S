class ContextTransaction:
    def __init__(self): self.changes=[]
    def record(self, operation, key): self.changes.append((operation,key))
