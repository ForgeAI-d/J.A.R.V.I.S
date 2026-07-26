# Phase 0 — Application Integration Repair

## Objective

Remove the non-critical boot failures currently affecting IdentityManager, MemoryManager, DeviceManager, EventManager and PermissionManager, and make the optional face-recognition capability report its state correctly.

## Required investigation

1. Identify the canonical component ID exported by DatabaseManager.
2. Compare that ID with every dependent manager's `REQUIRES` declaration.
3. Verify discovery includes the database package.
4. Verify DependencyResolver orders DatabaseManager before dependents.
5. Verify KernelContext exposes registry/service lookup during initialization.
6. Find all direct `DatabaseManager()` construction and replace it with context injection where appropriate.
7. Inspect Vision imports so missing optional libraries are not imported at module-discovery time.

## Target behavior

```text
DatabaseManager      ONLINE
IdentityManager      ONLINE
MemoryManager        ONLINE
DeviceManager        ONLINE
EventManager         ONLINE
PermissionManager    ONLINE
VisionManager        DISABLED or DEGRADED when face_recognition is unavailable
Kernel               RUNNING / 100%
```

## Tests

- canonical database dependency resolves for all five managers;
- initialization order is deterministic;
- all five managers receive the same registered database service;
- full application boot succeeds;
- graceful shutdown succeeds;
- restart succeeds;
- Vision disabled with dependency absent produces no error;
- Vision enabled with dependency absent reports degraded capability only;
- no optional module import can abort discovery.

## Definition of done

No manager reports "benötigt noch einen DatabaseManager" during a normal full boot. The boot report accurately separates required dependency failures from disabled or unavailable optional capabilities.
