def validate_runtime(runtime):
    required=("boot","shutdown","restart","report")
    missing=[n for n in required if not callable(getattr(runtime,n,None))]
    return {"valid":not missing,"errors":missing}
