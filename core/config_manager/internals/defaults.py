CONFIG_VERSION = 1


BOOT_DEFAULTS = {
    "version": CONFIG_VERSION,
    "boot_mode": "development",
    "safe_mode": False,
    "parallel_boot": False,
    "strict_dependencies": False,
    "fallback_boot_order": True
}


KERNEL_DEFAULTS = {
    "version": CONFIG_VERSION,
    "kernel_name": "Velthor Kernel",
    "kernel_version": "1.0.0-alpha",
    "system_name": "J.A.R.V.I.S.",
    "environment": "development"
}


LOGGER_DEFAULTS = {
    "version": CONFIG_VERSION,
    "log_path": "logs",
    "level": "INFO",
    "console_logging": True,
    "file_logging": True,
    "json_logging": True
}


SECURITY_DEFAULTS = {
    "version": CONFIG_VERSION,
    "safe_mode": False,
    "panic_mode": False,
    "auto_lock": True,
    "require_admin_approval": True
}


AI_DEFAULTS = {
    "version": CONFIG_VERSION,
    "local_models": True,
    "allow_cloud_models": False,
    "model_update_suggestions": True,
    "auto_deploy_updates": False
}


NETWORK_DEFAULTS = {
    "version": CONFIG_VERSION,
    "allow_remote_access": False,
    "api_enabled": False,
    "api_host": "127.0.0.1",
    "api_port": 8000
}


DATABASE_DEFAULTS = {
    "version": CONFIG_VERSION,
    "database_path": "data/jarvis.db",
    "auto_migrate": True,
    "backup_before_migration": True
}


BACKUP_DEFAULTS = {
    "version": CONFIG_VERSION,
    "backup_path": "backups",
    "auto_backup": True,
    "backup_on_boot": False
}


PLUGIN_DEFAULTS = {
    "version": CONFIG_VERSION,
    "plugin_path": "plugins",
    "auto_discover": True,
    "allow_unsigned_plugins": False
}


USER_DEFAULTS = {
    "version": CONFIG_VERSION,
    "default_user": "admin",
    "multi_user": True,
    "guest_access": False
}


DEFAULT_CONFIGS = {
    "boot": BOOT_DEFAULTS,
    "kernel": KERNEL_DEFAULTS,
    "logger": LOGGER_DEFAULTS,
    "security": SECURITY_DEFAULTS,
    "ai": AI_DEFAULTS,
    "network": NETWORK_DEFAULTS,
    "database": DATABASE_DEFAULTS,
    "backup": BACKUP_DEFAULTS,
    "plugins": PLUGIN_DEFAULTS,
    "users": USER_DEFAULTS
}