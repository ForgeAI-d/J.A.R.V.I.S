from copy import deepcopy


def collect_statistics(loader):
    return deepcopy(loader._boot_statistics)
