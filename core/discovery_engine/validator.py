def validate_discovery(engine): return {"valid":callable(getattr(engine,"discover",None)),"errors":[]}
