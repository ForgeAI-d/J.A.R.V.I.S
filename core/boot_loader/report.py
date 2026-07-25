from copy import deepcopy


def build_report(loader):
    return deepcopy(loader._build_boot_report())
