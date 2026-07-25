def validate_component_class(component_class):
    errors=[]
    for attr in ("COMPONENT_ID", "NAME", "VERSION"):
        if not getattr(component_class, attr, None): errors.append(attr)
    return {"valid": not errors, "errors": errors}
