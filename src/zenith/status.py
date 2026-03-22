from __future__ import annotations

import json

from . import __version__
from .ai import ollama_runtime_details
from .config import normalize_terminal
from .manifest import latest_manifest_timestamp
from .models import EnvironmentInfo, Paths, ResolvedConfig
from .updates import surface_upgrade_report
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
    terminal = normalize_terminal(config.surface.get("terminal"))
    if terminal == "ghostty":
        ghostty_config = paths.home / ".config/ghostty/config"
        shaders_dir = paths.home / ".config/ghostty/shaders"
        if ghostty_config.exists() and shaders_dir.exists():
            return "installed"
        if config.features.get("surface"):
            return "configured-missing-assets"
        return "absent"
    if terminal == "kitty":
        kitty_config = paths.home / ".config/kitty/kitty.conf"
        if kitty_config.exists():
            return "installed"
        if config.features.get("surface"):
            return "configured-missing-assets"
        return "absent"
    if config.features.get("surface"):
        return f"recorded-for-{terminal}"
    return "absent"


def render_status(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, as_json: bool) -> str:
    ai_runtime = ollama_runtime_details()
    surface_terminal = normalize_terminal(config.surface.get("terminal"))
    surface_upgrade = surface_upgrade_report(paths, config, env, allow_network=False)
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
        "ai_model": config.ai.get("model", "qwen3.5:4b"),
        "ai_ask_model": config.ai.get("ask_model") or config.ai.get("nav_model") or config.ai.get("model", "qwen3.5:4b"),
        "ai_fix_model": config.ai.get("fix_model") or config.ai.get("model", "qwen3.5:4b"),
        "ai_keep_alive": config.ai.get("keep_alive", "15m"),
        "ai_runtime_status": ai_runtime["status"],
        "ai_runtime_model": ai_runtime["model"],
        "ai_processor": ai_runtime["processor"],
        "ai_context": ai_runtime["context"],
        "surface_terminal": surface_terminal,
        "surface_status": surface_status(paths, config),
        "surface_installed_version": surface_upgrade.get("installed_version", ""),
        "surface_recommended_version": surface_upgrade.get("recommended_version", ""),
        "surface_upgrade_status": surface_upgrade.get("status", "unknown"),
        "updates_check_on_startup": bool(config.updates.get("check_on_startup")),
        "updates_recommend_on_startup": bool(config.updates.get("recommend_on_startup", True)),
        "updates_auto_upgrade_on_startup": bool(config.updates.get("auto_upgrade_on_startup")),
        "updates_startup_interval_hours": int(config.updates.get("startup_interval_hours", 24)),
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
            f"  surface terminal: {payload['surface_terminal']}",
            f"  surface status: {payload['surface_status']}",
            f"  surface installed version: {payload['surface_installed_version'] or 'none'}",
            f"  surface recommended version: {payload['surface_recommended_version'] or 'unknown'}",
            f"  surface upgrade status: {payload['surface_upgrade_status']}",
            f"  updates check on startup: {payload['updates_check_on_startup']}",
            f"  updates recommend on startup: {payload['updates_recommend_on_startup']}",
            f"  updates auto-upgrade on startup: {payload['updates_auto_upgrade_on_startup']}",
            f"  updates startup interval hours: {payload['updates_startup_interval_hours']}",
            f"  shell: {payload['shell']}",
            f"  shell integration: {payload['shell_integration']}",
            f"  workspace session: {payload['workspace_session']}",
            f"  workspace status: {payload['workspace_status']}",
            f"  ai provider: {payload['ai_provider']}",
            f"  ai model: {payload['ai_model']}",
            f"  ai ask model: {payload['ai_ask_model']}",
            f"  ai fix model: {payload['ai_fix_model']}",
            f"  ai keep-alive: {payload['ai_keep_alive']}",
            f"  ai runtime: {payload['ai_runtime_status']}",
            f"  ai processor: {payload['ai_processor'] or 'unknown'}",
            f"  ai loaded model: {payload['ai_runtime_model'] or 'none'}",
            f"  ai context: {payload['ai_context'] or 'unknown'}",
            f"  config: {payload['config_path']}",
            f"  manifest: {payload['latest_manifest'] or 'none'}",
            f"  manifest timestamp: {payload['latest_manifest_timestamp'] or 'none'}",
        ]
    )
