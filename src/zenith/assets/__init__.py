from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator


def _resource(*parts: str):
    node = files(__name__)
    for part in parts:
        node = node.joinpath(part)
    return node


def read_asset_text(*parts: str) -> str:
    return _resource(*parts).read_text(encoding="utf-8")


@contextmanager
def materialized_asset_path(*parts: str) -> Iterator[Path]:
    with as_file(_resource(*parts)) as resolved:
        yield resolved


def iter_asset_files(*parts: str) -> Iterator[tuple[str, Path]]:
    directory = _resource(*parts)
    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        if not child.is_file():
            continue
        with as_file(child) as resolved:
            yield child.name, resolved
