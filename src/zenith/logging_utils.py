from __future__ import annotations

import sys


def info(message: str) -> None:
    print(f"[zen] {message}")


def warn(message: str) -> None:
    print(f"[warn] {message}", file=sys.stderr)


def note(message: str) -> None:
    print(f"[note] {message}")


def ok(message: str) -> None:
    print(f"[ok] {message}")


def fail(message: str) -> None:
    print(f"[error] {message}", file=sys.stderr)
