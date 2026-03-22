from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from .binaries import resolve_binary, with_local_bin_path
from .models import Paths, ResolvedConfig


def _load_session_state(paths: Paths) -> dict[str, str]:
    state_file = paths.state_dir / "sessions.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        from .logging_utils import warn
        warn(f"Session state file is corrupt — starting with empty session state")
        return {}


def _save_session_state(paths: Paths, sessions: dict[str, str]) -> None:
    state_file = paths.state_dir / "sessions.json"
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(state_file)


def _live_sessions() -> set[str]:
    zellij = resolve_binary("zellij")
    if not zellij:
        return set()
    result = subprocess.run(
        [zellij, "list-sessions", "--short"],
        capture_output=True,
        text=True,
        check=False,
        env=with_local_bin_path(),
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def workspace_status(config: ResolvedConfig) -> str:
    zellij = resolve_binary("zellij")
    if not zellij:
        return "unavailable"
    session = str(config.workspace.get("default_session", "zenith"))
    live = _live_sessions()
    return "running" if session in live else "ready"


def open_workspace(config: ResolvedConfig) -> int:
    zellij = resolve_binary("zellij")
    if not zellij:
        raise SystemExit("zellij is not installed")
    session = str(config.workspace.get("default_session", "zenith"))
    return subprocess.run(
        [zellij, "attach", session, "-c"],
        check=False,
        env=with_local_bin_path(),
    ).returncode


def list_sessions(config: ResolvedConfig, paths: Paths) -> list[dict[str, str]]:
    live = _live_sessions()
    state = _load_session_state(paths)
    seen: set[str] = set()
    rows: list[dict[str, str]] = []

    # Registered sessions first
    for name, created_at in state.items():
        seen.add(name)
        rows.append({
            "name": name,
            "status": "running" if name in live else "stopped",
            "created_at": created_at,
        })

    # Live sessions not in registry
    for name in sorted(live - seen):
        rows.append({
            "name": name,
            "status": "running",
            "created_at": "",
        })

    return rows


def new_session(config: ResolvedConfig, paths: Paths, name: str, dry_run: bool = False) -> int:
    zellij = resolve_binary("zellij")
    if not zellij:
        raise SystemExit("zellij is not installed")
    from .logging_utils import info, ok
    info(f"Creating workspace session: {name}")
    if dry_run:
        ok(f"[dry-run] would create session '{name}'")
        return 0
    ret = subprocess.run(
        [zellij, "attach", name, "-c"],
        check=False,
        env=with_local_bin_path(),
    ).returncode
    if ret == 0:
        state = _load_session_state(paths)
        state[name] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _save_session_state(paths, state)
    return ret


def kill_session(config: ResolvedConfig, paths: Paths, name: str | None, dry_run: bool = False) -> int:
    zellij = resolve_binary("zellij")
    if not zellij:
        raise SystemExit("zellij is not installed")
    target = name or str(config.workspace.get("default_session", "zenith"))
    from .logging_utils import info, ok
    info(f"Killing workspace session: {target}")
    if dry_run:
        ok(f"[dry-run] would kill session '{target}'")
        return 0
    ret = subprocess.run(
        [zellij, "delete-session", target],
        check=False,
        env=with_local_bin_path(),
    ).returncode
    state = _load_session_state(paths)
    state.pop(target, None)
    _save_session_state(paths, state)
    return ret


def attach_session(config: ResolvedConfig, name: str) -> int:
    zellij = resolve_binary("zellij")
    if not zellij:
        raise SystemExit("zellij is not installed")
    return subprocess.run(
        [zellij, "attach", name],
        check=False,
        env=with_local_bin_path(),
    ).returncode
