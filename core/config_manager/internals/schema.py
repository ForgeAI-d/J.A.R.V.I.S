from .defaults import DEFAULT_CONFIGS


CONFIG_SCHEMA = {
    "boot": {
        "version": int,
        "boot_mode": str,
        "safe_mode": bool,
        "parallel_boot": bool,
        "strict_dependencies": bool,
        "fallback_boot_order": bool
    },
    "kernel": {
        "version": int,
        "kernel_name": str,
        "kernel_version": str,
        "system_name": str,
        "environment": str
    },
    "logger": {
        "version": int,
        "log_path": str,
        "level": str,
        "console_logging": bool,
        "file_logging": bool,
        "json_logging": bool
    },
    "security": {
        "version": int,
        "safe_mode": bool,
        "panic_mode": bool,
        "auto_lock": bool,
        "require_admin_approval": bool
    },
    "ai": {
        "version": int,
        "local_models": bool,
        "allow_cloud_models": bool,
        "model_update_suggestions": bool,
        "auto_deploy_updates": bool
    },
    "network": {
        "version": int,
        "allow_remote_access": bool,
        "api_enabled": bool,
        "api_host": str,
        "api_port": int
    },
    "database": {
        "version": int,
        "database_path": str,
        "auto_migrate": bool,
        "backup_before_migration": bool
    },
    "backup": {
        "version": int,
        "backup_path": str,
        "auto_backup": bool,
        "backup_on_boot": bool
    },
    "plugins": {
        "version": int,
        "plugin_path": str,
        "auto_discover": bool,
        "allow_unsigned_plugins": bool
    },
    "users": {
        "version": int,
        "default_user": str,
        "multi_user": bool,
        "guest_access": bool
    }
}


def get_schema(namespace):
    return CONFIG_SCHEMA.get(namespace, {})


def get_default(namespace):
    return DEFAULT_CONFIGS.get(namespace, {})


def list_namespaces():
    return list(CONFIG_SCHEMA.keys())


if __name__ == "__main__":
    print("=== CONFIG SCHEMA TEST ===")
    print(list_namespaces())
    print(get_schema("boot"))