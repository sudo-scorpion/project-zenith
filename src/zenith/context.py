from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Paths, TaskContext

PROJECT_ROOT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    ".zenith",
    "Makefile",
    "CMakeLists.txt",
)
_MAX_ERRORS = 5


def _find_project_root(start: Path) -> str:
    current = start.resolve()
    for _ in range(20):
        for marker in PROJECT_ROOT_MARKERS:
            if (current / marker).exists():
                return str(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    return ""


def load_context(paths: Paths) -> TaskContext:
    if not paths.context_file.exists():
        return TaskContext()
    try:
        data = json.loads(paths.context_file.read_text(encoding="utf-8"))
        return TaskContext(
            current_task=str(data.get("current_task", "")),
            project_root=str(data.get("project_root", "")),
            recent_errors=list(data.get("recent_errors", [])),
            session_start=str(data.get("session_start", "")),
        )
    except Exception:
        from .logging_utils import warn
        warn(f"Context file {paths.context_file} is corrupt — starting with empty context")
        return TaskContext()


def save_context(paths: Paths, ctx: TaskContext) -> None:
    data = {
        "current_task": ctx.current_task,
        "project_root": ctx.project_root,
        "recent_errors": ctx.recent_errors,
        "session_start": ctx.session_start,
    }
    tmp = paths.context_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(paths.context_file)


def set_context(paths: Paths, task: str) -> TaskContext:
    ctx = load_context(paths)
    ctx.current_task = task.strip()
    if not ctx.project_root:
        ctx.project_root = _find_project_root(Path.cwd())
    if not ctx.session_start:
        ctx.session_start = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_context(paths, ctx)
    return ctx


def clear_context(paths: Paths) -> None:
    save_context(paths, TaskContext())


def push_error(paths: Paths, error_snippet: str) -> TaskContext:
    if not error_snippet.strip():
        return load_context(paths)
    ctx = load_context(paths)
    snippet = error_snippet.strip()[:300]
    if snippet not in ctx.recent_errors:
        ctx.recent_errors.append(snippet)
    ctx.recent_errors = ctx.recent_errors[-_MAX_ERRORS:]
    save_context(paths, ctx)
    return ctx


def format_context_for_prompt(ctx: TaskContext) -> str:
    if not ctx.current_task:
        return ""
    parts = [f"Current task: {ctx.current_task}"]
    if ctx.project_root:
        parts.append(f"Project root: {ctx.project_root}")
    if ctx.recent_errors:
        parts.append("Recent errors (last 5):")
        for err in ctx.recent_errors:
            parts.append(f"  - {err}")
    return "\n".join(parts)


def show_context(paths: Paths) -> str:
    ctx = load_context(paths)
    if not ctx.current_task:
        return "No task context set. Use: zen context set \"<task description>\""
    lines = [f"Task:    {ctx.current_task}"]
    if ctx.project_root:
        lines.append(f"Project: {ctx.project_root}")
    if ctx.session_start:
        lines.append(f"Since:   {ctx.session_start}")
    if ctx.recent_errors:
        lines.append(f"Errors:  {len(ctx.recent_errors)} captured")
    return "\n".join(lines)
