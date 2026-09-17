"""Discover, validate, and register method-owned CodeWM plugins."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import pkgutil
from types import ModuleType

from processors import (
    MethodIntegrationPlugin,
    register_method_plugin,
)


def _integration_module_names(package: ModuleType) -> tuple[str, ...]:
    names = set()
    for child in pkgutil.iter_modules(package.__path__, f"{package.__name__}."):
        integration_name = f"{child.name}.codewm_integration"
        try:
            integration_spec = importlib.util.find_spec(integration_name)
        except (AttributeError, ModuleNotFoundError):
            integration_spec = None
        if integration_spec is not None:
            names.add(integration_name)

    # pkgutil omits namespace-package children that have no __init__.py.
    for package_root in package.__path__:
        for integration_path in Path(package_root).glob("*/codewm_integration.py"):
            names.add(
                f"{package.__name__}.{integration_path.parent.name}.codewm_integration"
            )
    return tuple(sorted(names))


def _load_plugin(module_name: str) -> MethodIntegrationPlugin:
    module = importlib.import_module(module_name)
    plugin = getattr(module, "CODEWM_PLUGIN", None)
    if not isinstance(plugin, MethodIntegrationPlugin):
        raise TypeError(
            f"{module_name} must export CODEWM_PLUGIN as MethodIntegrationPlugin"
        )

    legacy_contract = getattr(module, "CODEWM_INTEGRATION", None)
    if legacy_contract is not plugin.contract:
        raise ValueError(
            f"{module_name} CODEWM_INTEGRATION must be CODEWM_PLUGIN.contract"
        )

    method_package = module_name.rsplit(".", 1)[0]
    if not plugin.builder.__module__.startswith(f"{method_package}."):
        raise ValueError(
            f"method plugin '{plugin.contract.name}' builder must live under "
            f"{method_package}"
        )
    return plugin


def discover_and_register_methods(
    package_name: str = "libWM",
) -> dict[str, MethodIntegrationPlugin]:
    """Register every package-local integration plugin without a method list."""
    package = importlib.import_module(package_name)
    discovered: dict[str, MethodIntegrationPlugin] = {}
    for module_name in _integration_module_names(package):
        plugin = _load_plugin(module_name)
        name = plugin.contract.name
        if name in discovered:
            raise ValueError(f"duplicate discovered method plugin: {name}")
        register_method_plugin(plugin)
        discovered[name] = plugin
    return discovered


DISCOVERED_METHOD_PLUGINS = discover_and_register_methods()
