from __future__ import annotations

import os
from pathlib import Path

from .models import Paths


def build_paths(root: Path | None = None) -> Paths:
    root = root or Path(__file__).resolve().parents[2]
    home = Path.home()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    bin_home = home / ".local/bin"
    config_dir = config_home / "zenith"
    share_dir = data_home / "zenith"
    cache_dir = config_dir / "cache"
    state_dir = config_dir / "state"
    log_dir = config_dir / "logs"
    audit_dir = share_dir / "audit"
    backup_dir = share_dir / "backups"
    manifest_dir = share_dir / "manifests"
    session_dir = share_dir / "sessions"
    prompt_dir = config_dir / "prompts"
    config_file = config_dir / "zenith.toml"
    latest_manifest = manifest_dir / "latest.json"
    last_command_file = state_dir / "last_command"
    last_stderr_file = state_dir / "last_stderr"
    last_status_file = state_dir / "last_status"
    last_pwd_file = state_dir / "last_pwd"
    session_stderr_file = state_dir / "session.stderr"
    upgrade_state_file = state_dir / "upgrade_state.json"
    return Paths(
        root=root,
        home=home,
        config_home=config_home,
        data_home=data_home,
        bin_home=bin_home,
        config_dir=config_dir,
        share_dir=share_dir,
        cache_dir=cache_dir,
        state_dir=state_dir,
        log_dir=log_dir,
        audit_dir=audit_dir,
        backup_dir=backup_dir,
        manifest_dir=manifest_dir,
        session_dir=session_dir,
        prompt_dir=prompt_dir,
        config_file=config_file,
        latest_manifest=latest_manifest,
        last_command_file=last_command_file,
        last_stderr_file=last_stderr_file,
        last_status_file=last_status_file,
        last_pwd_file=last_pwd_file,
        session_stderr_file=session_stderr_file,
        upgrade_state_file=upgrade_state_file,
    )


def ensure_state_dirs(paths: Paths) -> None:
    for path in (
        paths.config_dir,
        paths.share_dir,
        paths.cache_dir,
        paths.state_dir,
        paths.log_dir,
        paths.audit_dir,
        paths.backup_dir,
        paths.manifest_dir,
        paths.session_dir,
        paths.prompt_dir,
        paths.bin_home,
    ):
        path.mkdir(parents=True, exist_ok=True)
