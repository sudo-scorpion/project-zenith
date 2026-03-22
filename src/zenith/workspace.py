from __future__ import annotations

import subprocess

from .binaries import resolve_binary, with_local_bin_path
from .models import ResolvedConfig



def workspace_status(config: ResolvedConfig) -> str:
    zellij = resolve_binary("zellij")
    if not zellij:
        return "unavailable"
    session = str(config.workspace.get("default_session", "zenith"))
    result = subprocess.run(
        [zellij, "list-sessions", "--short"],
        capture_output=True,
        text=True,
        check=False,
        env=with_local_bin_path(),
    )
    if result.returncode != 0:
        return "unavailable"
    sessions = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return "running" if session in sessions else "ready"



def open_workspace(config: ResolvedConfig) -> int:
    zellij = resolve_binary("zellij")
    if not zellij:
        raise SystemExit("zellij is not installed")
    session = str(config.workspace.get("default_session", "zenith"))
    # The shipped zellij config sets `default_layout "zenith"`, so creating the
    # session is enough on current zellij releases.
    return subprocess.run([zellij, "attach", session, "-c"], check=False, env=with_local_bin_path()).returncode
