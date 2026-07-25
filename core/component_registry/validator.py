def validate_registry(registry):
    required=("register_component","get","list_components")
    missing=[n for n in required if not callable(getattr(registry,n,None))]
    return {"valid":not missing,"errors":missing}
