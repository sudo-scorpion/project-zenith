from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from . import __version__
from .models import ManifestTransaction, Paths



def begin_transaction(profile: str, mode: str, components: list[str]) -> ManifestTransaction:
    return ManifestTransaction(
        version=__version__,
        profile=profile,
        mode=mode,
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        components=list(components),
    )



def _manifest_filename() -> str:
    return f"{datetime.now():%Y%m%d%H%M%S}.json"



def write_manifest(paths: Paths, manifest: ManifestTransaction) -> Path:
    target = paths.manifest_dir / _manifest_filename()
    payload = json.dumps(asdict(manifest), indent=2)
    target.write_text(payload + "\n", encoding="utf-8")
    paths.latest_manifest.write_text(payload + "\n", encoding="utf-8")
    return target



def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))



def manifest_files(paths: Paths) -> list[Path]:
    return sorted(path for path in paths.manifest_dir.glob("*.json") if path.name != "latest.json")



def load_manifest_history(paths: Paths) -> list[tuple[Path, dict]]:
    return [(path, load_manifest(path)) for path in manifest_files(paths)]



def load_latest_manifest(paths: Paths) -> dict:
    history = load_manifest_history(paths)
    if not history:
        raise FileNotFoundError("No manifest found")
    return history[-1][1]



def latest_manifest_timestamp(paths: Paths) -> str:
    try:
        return str(load_latest_manifest(paths).get("timestamp", ""))
    except FileNotFoundError:
        return ""



def rewrite_latest_manifest(paths: Paths, manifest_path: Path | None) -> None:
    if manifest_path is None:
        paths.latest_manifest.unlink(missing_ok=True)
        return
    paths.latest_manifest.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
