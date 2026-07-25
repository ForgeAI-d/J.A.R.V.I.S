from core.module_manager import ModuleManager


class CoreManager:
    manager_id = "core.manager"
    name = "Core Manager"
    version = "1.0.0"
    status = "OFFLINE"
    health = 0
    requires = []
    optional = []
    auto_start = True
    priority = 0
    startup_group = "core"
    tags = ["core", "system"]

    def initialize(self):
        self.status = "INITIALIZED"
        self.health = 100
        return True

    def start(self):
        self.status = "ONLINE"
        self.health = 100
        return True

    def stop(self):
        self.status = "OFFLINE"
        self.health = 0
        return True


class VisionEngine:
    engine_id = "vision.engine"
    name = "Vision Engine"
    version = "1.0.0"
    status = "OFFLINE"
    health = 0
    requires = ["core.manager"]
    optional = []
    auto_start = True
    priority = 100
    startup_group = "vision"
    tags = ["vision", "gpu"]

    def initialize(self):
        self.status = "INITIALIZED"
        self.health = 100
        return True

    def start(self):
        self.status = "ONLINE"
        self.health = 100
        return True

    def stop(self):
        self.status = "OFFLINE"
        self.health = 0
        return True


class VisionPlugin:
    plugin_id = "vision.plugin"
    name = "Vision Plugin"
    version = "1.0.0"
    status = "OFFLINE"
    health = 0
    requires = ["vision.engine"]
    optional = []
    auto_start = True
    priority = 200
    startup_group = "vision"
    tags = ["vision", "experimental"]

    def initialize(self):
        self.status = "INITIALIZED"
        self.health = 100
        return True

    def start(self):
        self.status = "ONLINE"
        self.health = 100
        return True

    def stop(self):
        self.status = "OFFLINE"
        self.health = 0
        return True


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"{name:.<42} {status}")
    if not condition:
        raise AssertionError(name)


def main():
    manager = ModuleManager()
    check("Initialize manager", manager.initialize())
    check("Start manager", manager.start())
    check("Register core", manager.register_manager(CoreManager()))
    check("Register vision engine", manager.register_engine(VisionEngine()))
    check("Register vision plugin", manager.register_plugin(VisionPlugin()))

    plan = manager.get_boot_plan()
    check(
        "Boot plan dependency order",
        [item["module_id"] for item in plan]
        == ["core.manager", "vision.engine", "vision.plugin"]
    )

    check("Initialize all", all(manager.initialize_all().values()))
    check("Start core group", all(manager.start_group("core").values()))
    check("Start vision tag", all(manager.start_tag("vision").values()))

    check(
        "Enable maintenance mode",
        manager.set_maintenance_mode("vision.plugin", True)
    )
    check(
        "Maintenance blocks start",
        manager.start_module("vision.plugin") is False
    )
    check(
        "Disable maintenance mode",
        manager.set_maintenance_mode("vision.plugin", False)
    )

    check(
        "Runtime configuration",
        manager.update_module_runtime(
            "vision.engine",
            priority=80,
            startup_group="perception",
            startup_delay=0,
            auto_restart=True
        )
    )
    runtime = manager.get_module_runtime("vision.engine")
    check(
        "Runtime values persisted",
        runtime["priority"] == 80
        and runtime["startup_group"] == "perception"
    )

    check(
        "Add tags",
        manager.add_module_tags(
            "vision.engine",
            "camera",
            "perception"
        )
    )
    check(
        "Tag lookup",
        manager.list_modules_by_tag("camera")
        == ["vision.engine"]
    )
    check(
        "Remove tag",
        manager.remove_module_tags(
            "vision.engine",
            "camera"
        )
    )
    check(
        "Tag removed",
        manager.list_modules_by_tag("camera") == []
    )

    restart_results = manager.restart_tag(
        "vision",
        reinitialize=True
    )
    check("Restart tag", all(restart_results.values()))

    stop_results = manager.stop_tag("vision")
    check("Stop tag", all(stop_results.values()))

    status = manager.get_status()
    check("Version 1.0.0", status["manifest"]["version"] == "1.0.0")
    check("Status contains tags", "tags" in status["modules"][0])
    check("Stop manager", manager.stop())

    print("\nMODULE MANAGER: SUCCESS")


if __name__ == "__main__":
    main()
