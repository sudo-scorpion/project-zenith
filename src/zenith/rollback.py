from __future__ import annotations

import shutil
from pathlib import Path

from .logging_utils import ok, warn
from .manifest import load_manifest_history, rewrite_latest_manifest
from .models import Paths



def _restore_manifest(manifest: dict, dry_run: bool) -> None:
    for target, backup in manifest.get("backups", {}).items():
        target_path = Path(target)
        backup_path = Path(backup)
        if not backup_path.exists():
            continue
        if dry_run:
            ok(f"[dry-run] Would restore {target}")
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target_path)
        ok(f"Restored {target}")
    for created in reversed(manifest.get("files_created", [])):
        created_path = Path(created)
        if not created_path.exists():
            continue
        if dry_run:
            ok(f"[dry-run] Would remove {created}")
            continue
        if created_path.is_dir():
            shutil.rmtree(created_path, ignore_errors=True)
            ok(f"Removed {created}")
        elif created_path.is_file() or created_path.is_symlink():
            created_path.unlink(missing_ok=True)
            ok(f"Removed {created}")


def rollback(paths: Paths, *, dry_run: bool = False, all_transactions: bool = False) -> None:
    history = load_manifest_history(paths)
    if not history:
        warn("No manifest found; nothing to roll back")
        return

    selected = history if all_transactions else [history[-1]]
    removed_paths: set[Path] = set()
    for manifest_path, manifest in reversed(selected):
        _restore_manifest(manifest, dry_run=dry_run)
        removed_paths.add(manifest_path)
        if not dry_run:
            manifest_path.unlink(missing_ok=True)

    if dry_run:
        ok("Dry-run rollback complete")
        return

    remaining = [path for path, _ in history if path not in removed_paths]
    rewrite_latest_manifest(paths, remaining[-1] if remaining else None)
    ok("Rollback complete")


def uninstall(paths: Paths, *, dry_run: bool = False) -> None:
    rollback(paths, dry_run=dry_run, all_transactions=True)
    if dry_run:
        ok(f"[dry-run] Would remove {paths.config_dir}")
        ok(f"[dry-run] Would remove {paths.share_dir}")
        return
    for managed_dir in (paths.config_dir, paths.share_dir):
        if managed_dir.exists():
            shutil.rmtree(managed_dir, ignore_errors=True)
            ok(f"Removed {managed_dir}")
