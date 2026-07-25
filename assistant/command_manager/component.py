from core.base_manager import BaseManager
from datetime import datetime, timezone


class CommandManager(BaseManager):
    COMPONENT_ID = "assistant.command_manager"
    NAME = "CommandManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True


    def __init__(
        self,
        identity_manager,
        permission_manager,
        memory_manager,
        event_manager
    ):
        BaseManager.__init__(self)

        self.identity = identity_manager
        self.permissions = permission_manager
        self.memory = memory_manager
        self.events = event_manager

    def process_command(
        self,
        user_id,
        command,
        source="UNKNOWN",
        device_id=None
    ):

        user = self.identity.get_user(
            user_id
        )

        if not user:

            self.events.log_error(
                "CommandManager",
                f"Unbekannter Benutzer: {user_id}"
            )

            return {
                "success": False,
                "message": "Unknown user"
            }

        self.identity.update_last_seen(
            user_id
        )

        self.events.log_info(
            "CommandManager",
            f"{user['name']} führte Befehl aus: {command}"
        )

        self.memory.create_memory(
            user_id=user_id,
            category="COMMAND",
            content=command,
            importance=3
        )

        return {
            "success": True,
            "user": user["name"],
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"Command processed: {command}"
        }

    def get_user_context(
        self,
        user_id
    ):

        user = self.identity.get_user(
            user_id
        )

        if not user:
            return None

        memories = self.memory.get_important_memories(
            user_id
        )

        permissions = self.permissions.get_permissions(
            user_id
        )

        devices = self.identity.get_user_devices(
            user_id
        )

        return {
            "user": user,
            "memories": memories,
            "permissions": permissions,
            "devices": devices
        }

    def check_permission(
        self,
        user_id,
        permission_name,
        source="COMMAND",
        device_id=None
    ):

        return self.permissions.check_permission(
            user_id=user_id,
            permission_name=permission_name,
            source=source,
            device_id=device_id
        )
