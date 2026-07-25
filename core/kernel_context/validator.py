def validate_context(context_class):
    required=("initialize","register_service","get_service","get_manifest","get_health","report")
    missing=[name for name in required if not callable(getattr(context_class,name,None))]
    return {"valid": not missing, "errors": missing}
