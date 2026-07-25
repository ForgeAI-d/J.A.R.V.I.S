# KernelContext and Config Refactor

## KernelContext

- Mutable service ownership moved to `KernelServiceRegistry`.
- Flags, shared values, and metadata are owned by `KernelDataStore`.
- Existing public methods and dictionary attributes remain compatible.
- Service waiting uses the registry-owned condition variable.

## Config system

Canonical config infrastructure now lives inside `core/config_manager/`:

- `cache.py`
- `defaults.py`
- `schema.py`
- `storage.py`
- `migrator.py`
- `watcher.py`
- `sources.py`
- `models.py`

The old `core/config_*.py` paths are compatibility re-exports.

New APIs:

- `get_resolved(namespace, key=None, default=None)`
- `get_typed(namespace, resolved=True)`
- `set_runtime_override(namespace, key, value)`
- `clear_runtime_overrides(namespace=None, key=None)`

Override precedence:

1. persisted JSON configuration
2. environment variables (`JARVIS_<NAMESPACE>_<KEY>`)
3. runtime overrides

Environment and runtime overrides are intentionally non-persistent.
