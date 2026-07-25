from database.database_manager import DatabaseManager

from identity.identity_manager import IdentityManager
from devices.device_manager import DeviceManager
from permissions.permission_manager import PermissionManager
from memory.memory_manager import MemoryManager
from events.event_manager import EventManager

from assistant.command_manager import CommandManager


print()
print("=== J.A.R.V.I.S INTEGRATION TEST ===")
print()

db = DatabaseManager()

identity = IdentityManager(db)
devices = DeviceManager(db)
permissions = PermissionManager(db)
memory = MemoryManager(db)
events = EventManager(db)

commands = CommandManager(
    identity,
    permissions,
    memory,
    events
)

print("1. Benutzer erstellen")

user_id = identity.create_user(
    "Domenik",
    role="OWNER"
)

print("User ID:", user_id)

print()
print("2. Gerät registrieren")

device_id = devices.register_device(
    owner_id=user_id,
    name="Forge Laptop",
    device_type="SERVER",
    platform="LINUX"
)

print("Device ID:", device_id)

print()
print("3. Berechtigung vergeben")

permissions.grant_permission(
    user_id,
    "system.shutdown"
)

allowed = permissions.check_permission(
    user_id,
    "system.shutdown"
)

print("Permission:", allowed)

print()
print("4. Erinnerung speichern")

memory.create_memory(
    user_id=user_id,
    category="PROFILE",
    content="Besitzer von J.A.R.V.I.S",
    importance=10
)

print("Memory gespeichert")

print()
print("5. Command ausführen")

result = commands.process_command(
    user_id=user_id,
    command="status"
)

print(result)

print()
print("=== TEST FERTIG ===")