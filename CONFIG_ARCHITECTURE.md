# Configuration architecture

The configuration subsystem is a single KAS component under
`core/config_manager`.

Its public surface is intentionally small:

```python
from core.config_manager import ConfigManager, BootConfig, KernelConfig
```

Standard KAS files (`manifest.py`, `validator.py`, `events.py`,
`transaction.py`, and related adapters) describe the component itself.
Implementation details such as storage, schema handling, caching, migration,
source resolution, typed models, file watching, and configuration-specific
transactions live in `core/config_manager/internals`.

Loose `core/config_*.py` compatibility modules and legacy source snapshots are
not part of the active project tree. This prevents two competing import paths
from becoming permanent APIs.
