from __future__ import annotations

import shutil
from pathlib import Path

from .models import ManifestTransaction, Paths


def backup_file(paths: Paths, manifest: ManifestTransaction, file_path: Path) -> None:
    if not file_path.exists() or not file_path.is_file():
        return
    txn_dir = paths.backup_dir / manifest.timestamp.replace(":", "-")
    txn_dir.mkdir(parents=True, exist_ok=True)
    backup_path = txn_dir / file_path.name
    shutil.copy2(file_path, backup_path)
    manifest.backups[str(file_path)] = str(backup_path)
