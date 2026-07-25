"""Lightweight component observer."""
class ComponentObserver:
    def __init__(self):
        self.events = []
    def update(self, event):
        self.events.append(event)
