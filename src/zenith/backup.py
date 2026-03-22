from __future__ import annotations

import shutil
from pathlib import Path

from .models import ManifestTransaction, Paths


def _safe_backup_name(file_path: Path) -> str:
    """Create a collision-free backup name from the full path.

    Transforms e.g. /home/user/.config/kitty/kitty.conf -> _home_user_.config_kitty_kitty.conf
    so two files with the same basename from different directories never collide.
    """
    parts = file_path.parts
    # Skip the first empty part for absolute paths (the root '/')
    cleaned = "__".join(p for p in parts if p != "/")
    return cleaned


def backup_file(paths: Paths, manifest: ManifestTransaction, file_path: Path) -> None:
    if not file_path.exists() or not file_path.is_file():
        return
    txn_dir = paths.backup_dir / manifest.timestamp.replace(":", "-")
    txn_dir.mkdir(parents=True, exist_ok=True)
    backup_path = txn_dir / _safe_backup_name(file_path)
    shutil.copy2(file_path, backup_path)
    manifest.backups[str(file_path)] = str(backup_path)
