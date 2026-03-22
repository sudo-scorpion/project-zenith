from __future__ import annotations

import json

from . import __version__
from .manifest import latest_manifest_timestamp
from .models import EnvironmentInfo, Paths, ResolvedConfig
from .shells import HOOK_MARKER, shell_fragment_path, shell_rc_path
from .workspace import workspace_status


def shell_integration_status(paths: Paths, shell: str) -> str:
    fragment = shell_fragment_path(paths, shell)
    rc_file = shell_rc_path(paths, shell)
    if fragment.exists() and rc_file.exists():
        try:
            text = rc_file.read_text(encoding="utf-8")
        except OSError:
            return "fragment-present"
        if HOOK_MARKER in text:
            return "configured"
    if fragment.exists():
        return "fragment-present"
    return "absent"


def surface_status(paths: Paths, config: ResolvedConfig) -> str:
    ghostty_config = paths.home / ".config/ghostty/config"
    shaders_dir = paths.home / ".config/ghostty/shaders"
    if ghostty_config.exists() and shaders_dir.exists():
        return "installed"
    if config.features.get("surface"):
        return "configured-missing-assets"
    return "absent"


def render_status(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, as_json: bool) -> str:
    payload = {
        "version": __version__,
        "profile": config.profile,
        "mode": env.resolved_mode,
        "distro": f"{env.distro} {env.version}".strip(),
        "package_manager": env.package_manager,
        "container": env.container,
        "container_runtime": env.container_runtime,
        "distrobox": env.distrobox,
        "gui": env.gui,
        "systemd": env.systemd,
        "components": {
            "core": bool(config.features.get("core")),
            "surface": bool(config.features.get("surface")),
        },
        "shell": config.shell,
        "shell_integration": shell_integration_status(paths, config.shell),
        "workspace_session": config.workspace.get("default_session", "zenith"),
        "workspace_status": workspace_status(config),
        "ai_provider": config.ai.get("provider", "ollama"),
        "ai_model": config.ai.get("model", "llama3.2:3b"),
        "surface_status": surface_status(paths, config),
        "config_path": str(paths.config_file),
        "latest_manifest": str(paths.latest_manifest) if paths.latest_manifest.exists() else "",
        "latest_manifest_timestamp": latest_manifest_timestamp(paths),
    }
    if as_json:
        return json.dumps(payload, indent=2)
    return "\n".join(
        [
            f"Zenith {payload['version']}",
            f"  profile: {payload['profile']}",
            f"  mode: {payload['mode']}",
            f"  distro: {payload['distro']}",
            f"  package manager: {payload['package_manager']}",
            f"  container: {payload['container']} ({payload['container_runtime']})",
            f"  distrobox: {payload['distrobox']}",
            f"  gui: {payload['gui']}",
            f"  systemd: {payload['systemd']}",
            f"  core installed: {payload['components']['core']}",
            f"  surface installed: {payload['components']['surface']}",
            f"  surface status: {payload['surface_status']}",
            f"  shell: {payload['shell']}",
            f"  shell integration: {payload['shell_integration']}",
            f"  workspace session: {payload['workspace_session']}",
            f"  workspace status: {payload['workspace_status']}",
            f"  ai provider: {payload['ai_provider']}",
            f"  ai model: {payload['ai_model']}",
            f"  config: {payload['config_path']}",
            f"  manifest: {payload['latest_manifest'] or 'none'}",
            f"  manifest timestamp: {payload['latest_manifest_timestamp'] or 'none'}",
        ]
    )
