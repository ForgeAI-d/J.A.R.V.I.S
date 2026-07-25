"""Lifecycle transaction helper."""
class ComponentTransaction:
    def __init__(self, component):
        self.component = component
        self.started = False
    def __enter__(self):
        self.component.initialize()
        self.component.start()
        self.started = True
        return self.component
    def __exit__(self, exc_type, exc, tb):
        if self.started:
            self.component.stop()
        return False
