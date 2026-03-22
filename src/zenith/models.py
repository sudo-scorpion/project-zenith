from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Paths:
    root: Path
    home: Path
    config_home: Path
    data_home: Path
    bin_home: Path
    config_dir: Path
    share_dir: Path
    cache_dir: Path
    state_dir: Path
    log_dir: Path
    audit_dir: Path
    backup_dir: Path
    manifest_dir: Path
    session_dir: Path
    prompt_dir: Path
    config_file: Path
    latest_manifest: Path
    last_command_file: Path
    last_stderr_file: Path
    last_status_file: Path
    last_pwd_file: Path
    session_stderr_file: Path


@dataclass
class ResolvedConfig:
    profile: str = "safe"
    mode: str = "auto"
    shell: str = "bash"
    features: dict[str, Any] = field(default_factory=dict)
    ai: dict[str, Any] = field(default_factory=dict)
    surface: dict[str, Any] = field(default_factory=dict)
    workspace: dict[str, Any] = field(default_factory=dict)
    paths: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentInfo:
    distro: str = "unknown"
    version: str = "unknown"
    package_manager: str = "unknown"
    container: bool = False
    container_runtime: str = "none"
    distrobox: bool = False
    gui: bool = False
    systemd: bool = False
    gpu_tools: bool = False
    resolved_mode: str = "auto"


@dataclass
class ManifestTransaction:
    version: str
    profile: str
    mode: str
    timestamp: str
    packages: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    backups: dict[str, str] = field(default_factory=dict)
    services: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)


@dataclass
class AIResult:
    intent: str
    command: str
    risk: str
    explanation: str
    requires_confirmation: bool
