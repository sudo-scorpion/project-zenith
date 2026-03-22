from __future__ import annotations

import os
import shutil
from pathlib import Path


def local_bin_home(home: Path | None = None) -> Path:
    return (home or Path.home()) / '.local/bin'


def resolve_binary(*names: str, home: Path | None = None) -> str | None:
    seen: set[str] = set()
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        resolved = shutil.which(name)
        if resolved:
            return resolved
        candidate = local_bin_home(home) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def binary_available(*names: str, home: Path | None = None) -> bool:
    return resolve_binary(*names, home=home) is not None


def with_local_bin_path(env: dict[str, str] | None = None, home: Path | None = None) -> dict[str, str]:
    data = dict(os.environ if env is None else env)
    local_bin = str(local_bin_home(home))
    current_path = data.get('PATH', '')
    parts = [part for part in current_path.split(':') if part]
    if local_bin not in parts:
        data['PATH'] = f'{local_bin}:{current_path}' if current_path else local_bin
    return data
