from __future__ import annotations

import shutil
import subprocess

from .models import ResolvedConfig



def workspace_status(config: ResolvedConfig) -> str:
    if not shutil.which("zellij"):
        return "unavailable"
    session = str(config.workspace.get("default_session", "zenith"))
    result = subprocess.run(
        ["zellij", "list-sessions", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "unavailable"
    sessions = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return "running" if session in sessions else "ready"



def open_workspace(config: ResolvedConfig) -> int:
    if not shutil.which("zellij"):
        raise SystemExit("zellij is not installed")
    session = str(config.workspace.get("default_session", "zenith"))
    return subprocess.run(["zellij", "attach", session, "-c", "--layout", "zenith"], check=False).returncode
