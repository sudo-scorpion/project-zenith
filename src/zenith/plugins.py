from __future__ import annotations

import dataclasses
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logging_utils import warn
from .models import Paths, ResolvedConfig

EXAMPLE_PLUGIN_CONTENT = '''\
# Example Zenith plugin — rename to <name>.py to activate
# Place active plugins in ~/.config/zenith/plugins/
#
# Required attributes:
#   COMMAND     - name used in: zen plugins run <COMMAND>
#   DESCRIPTION - shown in: zen plugins list
#
# Optional:
#   VERSION     - displayed in plugin list

COMMAND = "example"
DESCRIPTION = "Show Zenith config summary"
VERSION = "1.0"


def run(args, config, paths):
    """
    args:   list of strings passed after the plugin name
    config: dict of the active ResolvedConfig (read-only)
    paths:  dict of Paths fields as strings (read-only)
    Returns: exit code (int)
    """
    print(f"Shell:   {config[\'shell\']}")
    print(f"Profile: {config[\'profile\']}")
    print(f"Mode:    {config[\'mode\']}")
    print(f"Config:  {paths[\'config_file\']}")
    return 0
'''


@dataclass
class PluginInfo:
    name: str
    command: str
    description: str
    version: str
    path: Path


def _load_plugin(path: Path) -> PluginInfo | None:
    module_name = f"zenith_plugin_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            warn(f"Plugin {path.name}: could not load spec")
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        command = str(getattr(module, "COMMAND", "")).strip()
        if not command:
            warn(f"Plugin {path.name}: missing COMMAND attribute — skipped")
            return None
        return PluginInfo(
            name=path.stem,
            command=command,
            description=str(getattr(module, "DESCRIPTION", "")).strip(),
            version=str(getattr(module, "VERSION", "")).strip(),
            path=path,
        )
    except SyntaxError as exc:
        warn(f"Plugin {path.name}: syntax error — {exc}")
    except ImportError as exc:
        warn(f"Plugin {path.name}: import error — {exc}")
    except Exception as exc:
        warn(f"Plugin {path.name}: failed to load — {exc}")
    return None


def discover_plugins(paths: Paths) -> list[PluginInfo]:
    if not paths.plugins_dir.exists():
        return []
    plugins: list[PluginInfo] = []
    for py_file in sorted(paths.plugins_dir.glob("*.py")):
        plugin = _load_plugin(py_file)
        if plugin:
            plugins.append(plugin)
    return sorted(plugins, key=lambda p: p.command)


def run_plugin(plugin: PluginInfo, args: list[str], config: ResolvedConfig, paths: Paths) -> int:
    module_name = f"zenith_plugin_{plugin.path.stem}"
    module = sys.modules.get(module_name)
    if module is None:
        spec = importlib.util.spec_from_file_location(module_name, plugin.path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"Cannot load plugin '{plugin.command}'")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]

    run_fn = getattr(module, "run", None)
    if not callable(run_fn):
        raise SystemExit(f"Plugin '{plugin.command}' has no callable run() function")

    config_dict = dataclasses.asdict(config)
    paths_dict = {field.name: str(getattr(paths, field.name)) for field in dataclasses.fields(paths)}

    try:
        result = run_fn(args, config_dict, paths_dict)
        return int(result) if result is not None else 0
    except SystemExit:
        raise
    except Exception as exc:
        from .logging_utils import fail
        fail(f"Plugin '{plugin.command}' raised an error: {exc}")
        return 1


def render_plugin_list(plugins: list[PluginInfo]) -> str:
    if not plugins:
        return (
            "No active plugins found in ~/.config/zenith/plugins/\n"
            "Rename example.py.disabled to example.py to activate the example plugin."
        )
    lines = [f"{'COMMAND':<20} {'VERSION':<8} {'DESCRIPTION'}"]
    lines.append("-" * 60)
    for p in plugins:
        ver = p.version or "-"
        lines.append(f"{p.command:<20} {ver:<8} {p.description}")
    return "\n".join(lines)
