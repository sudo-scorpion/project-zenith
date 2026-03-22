from __future__ import annotations

import json
import os
import shutil
import subprocess

from .manifest import latest_manifest_timestamp
from .models import EnvironmentInfo, Paths, ResolvedConfig
from .status import shell_integration_status, surface_status
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
        if any(shutil.which(binary) for binary in binaries):
            continue
        missing.append(label)
    return missing


def doctor_report(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo) -> list[dict[str, str]]:
    model = str(config.ai.get("model", "llama3.2:3b"))
    missing_tools = _missing_core_tools()
    workspace = workspace_status(config)
    surface = surface_status(paths, config)
    shell_integration = shell_integration_status(paths, config.shell)
    backups_writable = paths.backup_dir.exists() and os.access(paths.backup_dir, os.W_OK)
    manifest_timestamp = latest_manifest_timestamp(paths)
    shell_available = shutil.which(config.shell) is not None

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
        {"level": "PASS" if shutil.which("ollama") else "WARN", "item": "ollama", "detail": "ollama available" if shutil.which("ollama") else "ollama not installed"},
        {"level": "PASS", "item": "config_parse", "detail": "config parsed successfully"},
        {"level": "PASS" if paths.config_file.exists() else "WARN", "item": "config", "detail": str(paths.config_file) if paths.config_file.exists() else "No config written yet"},
        {"level": "PASS" if backups_writable else "FAIL", "item": "backups", "detail": str(paths.backup_dir)},
        {"level": "PASS" if manifest_timestamp else "WARN", "item": "manifest", "detail": manifest_timestamp or "No manifest present"},
    ]
    if config.features.get("surface"):
        report.append({"level": "PASS" if surface == "installed" else "WARN", "item": "surface", "detail": surface})
    else:
        report.append({"level": "PASS", "item": "surface", "detail": f"not requested ({surface})"})
    if shutil.which("ollama"):
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
        has_model = model in result.stdout
        report.append({"level": "PASS" if has_model else "WARN", "item": "model", "detail": f"{model} available" if has_model else f"{model} not available"})
    else:
        report.append({"level": "WARN", "item": "model", "detail": f"{model} not available"})
    return report


def render_doctor(report: list[dict[str, str]], as_json: bool) -> str:
    if as_json:
        return json.dumps({row["item"]: {"level": row["level"], "detail": row["detail"]} for row in report}, indent=2)
    return "\n".join(f"{row['level']:<4} {row['item']:<17} {row['detail']}" for row in report)
