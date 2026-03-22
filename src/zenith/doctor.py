from __future__ import annotations

import json
import os
import subprocess

from .ai import ollama_runtime_details
from .binaries import binary_available, resolve_binary, with_local_bin_path
from .manifest import latest_manifest_timestamp
from .models import EnvironmentInfo, Paths, ResolvedConfig
from .status import shell_integration_status, surface_status
from .updates import surface_upgrade_report
from .workspace import workspace_status

CORE_TOOLS = {
    "zellij": ("zellij",),
    "yazi": ("yazi",),
    "eza": ("eza", "exa"),
    "bat": ("bat", "batcat"),
    "starship": ("starship",),
    "zoxide": ("zoxide",),
    "fzf": ("fzf",),
    "rg": ("rg", "ripgrep"),
    "btop": ("btop",),
}


def _missing_core_tools() -> list[str]:
    missing: list[str] = []
    for label, binaries in CORE_TOOLS.items():
        if binary_available(*binaries):
            continue
        missing.append(label)
    return missing


def doctor_report(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo) -> list[dict[str, str]]:
    model = str(config.ai.get("model", "qwen3.5:4b"))
    missing_tools = _missing_core_tools()
    workspace = workspace_status(config)
    surface = surface_status(paths, config)
    surface_upgrade = surface_upgrade_report(paths, config, env, allow_network=False)
    shell_integration = shell_integration_status(paths, config.shell)
    backups_writable = paths.backup_dir.exists() and os.access(paths.backup_dir, os.W_OK)
    manifest_timestamp = latest_manifest_timestamp(paths)
    shell_available = binary_available(config.shell)

    report = [
        {"level": "PASS", "item": "distro", "detail": f"{env.distro} {env.version}"},
        {"level": "PASS" if env.package_manager != "unknown" else "WARN", "item": "package_manager", "detail": env.package_manager},
        {"level": "PASS", "item": "mode", "detail": env.resolved_mode},
        {"level": "WARN" if env.container else "PASS", "item": "container", "detail": "Container environment detected" if env.container else "Host environment"},
        {"level": "PASS", "item": "container_runtime", "detail": env.container_runtime},
        {"level": "PASS" if env.distrobox else "WARN", "item": "distrobox", "detail": "Distrobox markers detected" if env.distrobox else "No distrobox markers detected"},
        {"level": "PASS" if env.gui else "WARN", "item": "gui", "detail": "GUI session detected" if env.gui else "No GUI session detected"},
        {"level": "PASS" if env.systemd else "WARN", "item": "systemd", "detail": "systemctl available" if env.systemd else "systemctl unavailable"},
        {"level": "PASS" if shell_available else "FAIL", "item": "shell", "detail": f"{config.shell} available" if shell_available else f"{config.shell} missing"},
        {"level": "PASS" if shell_integration == "configured" else "WARN", "item": "shell_integration", "detail": shell_integration},
        {"level": "PASS" if not missing_tools else "WARN", "item": "core_tools", "detail": "all present" if not missing_tools else f"missing: {', '.join(missing_tools)}"},
        {"level": "PASS" if workspace in {"ready", "running"} else "WARN", "item": "workspace", "detail": workspace},
        {"level": "PASS" if resolve_binary("ollama") else "WARN", "item": "ollama", "detail": "ollama available" if resolve_binary("ollama") else "ollama not installed"},
        {"level": "PASS", "item": "config_parse", "detail": "config parsed successfully"},
        {"level": "PASS" if paths.config_file.exists() else "WARN", "item": "config", "detail": str(paths.config_file) if paths.config_file.exists() else "No config written yet"},
        {"level": "PASS" if backups_writable else "FAIL", "item": "backups", "detail": str(paths.backup_dir)},
        {"level": "PASS" if manifest_timestamp else "WARN", "item": "manifest", "detail": manifest_timestamp or "No manifest present"},
    ]
    if config.features.get("surface"):
        report.append({"level": "PASS" if surface == "installed" else "WARN", "item": "surface", "detail": surface})
    else:
        report.append({"level": "PASS", "item": "surface", "detail": f"not requested ({surface})"})
    upgrade_status = str(surface_upgrade.get("status", "unknown"))
    upgrade_detail = str(surface_upgrade.get("message", "No surface upgrade data available"))
    upgrade_level = "PASS"
    if upgrade_status == "upgrade-available" or upgrade_status == "install-available":
        upgrade_level = "WARN"
    report.append({"level": upgrade_level, "item": "surface_upgrade", "detail": upgrade_detail})
    ollama = resolve_binary("ollama")
    if ollama:
        result = subprocess.run([ollama, "list"], capture_output=True, text=True, check=False, env=with_local_bin_path())
        has_model = model in result.stdout
        report.append({"level": "PASS" if has_model else "WARN", "item": "model", "detail": f"{model} available" if has_model else f"{model} not available"})
        runtime = ollama_runtime_details()
        if runtime["status"] == "running":
            level = "PASS" if "GPU" in runtime["processor"].upper() else "WARN"
            detail = f"{runtime['processor']} ({runtime['model']}, ctx {runtime['context'] or 'unknown'})"
        elif runtime["status"] == "idle":
            level = "PASS"
            detail = "idle"
        elif runtime["status"] == "unavailable":
            level = "WARN"
            detail = "ollama unavailable"
        else:
            level = "WARN"
            detail = runtime["status"]
        report.append({"level": level, "item": "ai_runtime", "detail": detail})
    else:
        report.append({"level": "WARN", "item": "model", "detail": f"{model} not available"})
        report.append({"level": "WARN", "item": "ai_runtime", "detail": "ollama unavailable"})
    return report


def render_doctor(report: list[dict[str, str]], as_json: bool) -> str:
    if as_json:
        return json.dumps({row["item"]: {"level": row["level"], "detail": row["detail"]} for row in report}, indent=2)
    return "\n".join(f"{row['level']:<4} {row['item']:<17} {row['detail']}" for row in report)
