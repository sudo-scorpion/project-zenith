from __future__ import annotations

import os
from pathlib import Path

from .models import Paths

SUPPORTED_SHELLS = ("bash", "zsh")
HOOK_MARKER = "# Project Zenith"


def normalize_shell(value: str | None) -> str:
    candidate = Path(value).name.lower() if value else ""
    return candidate if candidate in SUPPORTED_SHELLS else "bash"


def detect_default_shell() -> str:
    return normalize_shell(os.environ.get("SHELL"))


def shell_fragment_name(shell: str) -> str:
    return {
        "bash": "zenith.bashrc",
        "zsh": "zenith.zshrc",
    }[normalize_shell(shell)]


def shell_fragment_path(paths: Paths, shell: str) -> Path:
    return paths.config_dir / shell_fragment_name(shell)


def shell_fragment_source(shell: str) -> tuple[str, ...]:
    return {
        "bash": ("configs", "bash", "zenith.bashrc.fragment"),
        "zsh": ("configs", "zsh", "zenith.zshrc.fragment"),
    }[normalize_shell(shell)]


def shell_rc_path(paths: Paths, shell: str) -> Path:
    if normalize_shell(shell) == "zsh":
        return paths.home / ".zshrc"
    return paths.home / ".bashrc"


def shell_history_path(paths: Paths, shell: str) -> Path:
    if normalize_shell(shell) == "zsh":
        return paths.home / ".zsh_history"
    return paths.home / ".bash_history"


def shell_hook(shell: str) -> str:
    fragment_name = shell_fragment_name(shell)
    return (
        f"{HOOK_MARKER}\n"
        f"if [ -f \"$HOME/.config/zenith/{fragment_name}\" ]; then\n"
        f"  . \"$HOME/.config/zenith/{fragment_name}\"\n"
        "fi\n"
    )
