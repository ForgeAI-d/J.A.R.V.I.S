# KAS BootLoader v2

The BootLoader is now a KAS package and runtime coordinator. It performs explicit discovery, manifest validation, dependency graph construction, deterministic startup, health reporting and reverse-order shutdown. The public import remains `from core.boot_loader import BootLoader`.

The DependencyResolver now participates in the shared `BaseKernelComponent` hierarchy and exposes the same package-level KAS support files as the other kernel components.
