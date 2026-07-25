# J.A.R.V.I.S. Kernel Architecture Standard 1.0

Canonical hierarchy:

- `BaseComponent`
- `BaseKernelComponent`
- `BaseManager` / `BaseEngine`

Every bootable component exposes manifest, lifecycle, validation, health, statistics, reports, events, observer support and transactions.

Runtime path:

`KernelRuntime -> BootLoader -> DiscoveryEngine -> ComponentRegistry -> DependencyResolver -> LifecycleManager -> Health -> RecoveryManager`

Compatibility imports remain available for the previous manager packages. `JarvisCore` is now an application facade over `KernelRuntime` and no longer manually constructs the whole service graph.
