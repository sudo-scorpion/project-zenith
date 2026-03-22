from __future__ import annotations


def info(message: str) -> None:
    print(f"[zen] {message}")


def warn(message: str) -> None:
    print(f"[warn] {message}")


def ok(message: str) -> None:
    print(f"[ok] {message}")


def fail(message: str) -> None:
    print(f"[error] {message}")
