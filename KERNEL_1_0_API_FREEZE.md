# J.A.R.V.I.S. Kernel 1.0 API Freeze

The Kernel Architecture Standard (KAS) public surface is frozen at version 1.0.0.

## Stable entry points

- `core.kernel_runtime.KernelRuntime`
- `core.kernel_runtime.Kernel`
- `core.boot_loader.BootLoader`
- `core.kernel_context.KernelContext`
- `core.component_registry.ComponentRegistry`
- `core.dependency_resolver.DependencyResolver`
- `core.base_manager.BaseManager`
- `core.base_engine.BaseEngine`

## Runtime lifecycle

- `boot()`
- `run()`
- `pause()`
- `resume()`
- `restart()`
- `shutdown()`
- `get_status()`
- `report()`

Breaking changes require Kernel 2.0. Additive compatible changes may be released as
1.x. Bug fixes do not change the public contract.
