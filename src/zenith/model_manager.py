from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from .ai import _ollama_host, _ollama_timeout
from .config import write_config
from .logging_utils import warn
from .models import Paths, ResolvedConfig

TASK_TYPES = ("ask", "fix", "agent")


def model_for_task(config: ResolvedConfig, task: str) -> str:
    models_table = config.ai.get("models", {})
    if isinstance(models_table, dict) and models_table.get(task, "").strip():
        return str(models_table[task]).strip()
    legacy = {"ask": "ask_model", "fix": "fix_model", "agent": "agent_model"}
    key = legacy.get(task)
    if key:
        specific = str(config.ai.get(key, "")).strip()
        if specific:
            return specific
    return str(config.ai.get("model", "qwen2.5-coder:7b"))




def _ollama_get(config: ResolvedConfig, path: str) -> dict:
    url = f"{_ollama_host(config)}{path}"
    req = urllib.request.Request(url, method="GET", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_ollama_timeout(config)) as resp:
            return json.load(resp)
    except urllib.error.URLError:
        return {}
    except urllib.error.HTTPError:
        return {}


def list_local_models(config: ResolvedConfig) -> list[dict]:
    data = _ollama_get(config, "/api/tags")
    models = data.get("models", [])
    result = []
    for m in models:
        size_bytes = m.get("size", 0)
        size_gb = f"{size_bytes / 1_073_741_824:.1f}G" if size_bytes else "?"
        result.append({
            "name": str(m.get("name", "")),
            "size": size_gb,
            "modified": str(m.get("modified_at", ""))[:10],
        })
    return result


def list_loaded_models(config: ResolvedConfig) -> list[dict]:
    data = _ollama_get(config, "/api/ps")
    models = data.get("models", [])
    result = []
    for m in models:
        size_bytes = m.get("size", 0)
        size_gb = f"{size_bytes / 1_073_741_824:.1f}G" if size_bytes else "?"
        details = m.get("details", {})
        processor = str(details.get("processor", details.get("families", ["?"])[0] if isinstance(details.get("families"), list) else "?"))
        result.append({
            "name": str(m.get("name", m.get("model", ""))),
            "size": size_gb,
            "processor": processor,
        })
    return result


def pull_model(config: ResolvedConfig, name: str) -> int:
    from .logging_utils import info, ok, fail as _fail
    host = _ollama_host(config)
    body = json.dumps({"name": name, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/pull",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                status = str(event.get("status", ""))
                if "error" in event:
                    _fail(str(event["error"]))
                    return 1
                if status and status not in ("success",):
                    completed = event.get("completed", 0)
                    total = event.get("total", 0)
                    if total and completed:
                        pct = int(100 * completed / total)
                        info(f"  {status}: {pct}%")
                    else:
                        info(f"  {status}")
        ok(f"Model '{name}' pulled successfully")
        return 0
    except urllib.error.URLError as exc:
        from .logging_utils import fail as _fail
        _fail(f"Cannot reach Ollama at {host}: {exc}")
        return 1


def set_model_for_task(paths: Paths, config: ResolvedConfig, task: str, model: str) -> None:
    if task not in TASK_TYPES:
        raise SystemExit(f"Unknown task type '{task}'. Valid: {', '.join(TASK_TYPES)}")
    models = config.ai.setdefault("models", {})
    models[task] = model.strip()
    write_config(paths, config)


def render_model_list(
    local: list[dict],
    loaded: list[dict],
    assignments: dict[str, str],
) -> str:
    loaded_names = {m["name"] for m in loaded}
    lines = []

    if not local:
        lines.append("No local models found. Is Ollama running?")
        lines.append("  zen models pull qwen2.5-coder:7b")
        return "\n".join(lines)

    lines.append(f"{'MODEL':<35} {'SIZE':>6}  {'MODIFIED':<12}  ASSIGNED TO     STATUS")
    lines.append("-" * 80)
    for m in local:
        name = m["name"]
        size = m.get("size", "?")
        modified = m.get("modified", "?")
        assigned_to = [task for task, mdl in assignments.items() if mdl == name]
        assigned_str = ", ".join(assigned_to) if assigned_to else ""
        status = "loaded" if name in loaded_names else ""
        lines.append(f"{name:<35} {size:>6}  {modified:<12}  {assigned_str:<16}{status}")

    lines.append("")
    lines.append("Task assignments:")
    for task in TASK_TYPES:
        lines.append(f"  {task:<8} -> {assignments.get(task, '(default)')}")

    if loaded:
        lines.append("")
        lines.append("Loaded in VRAM:")
        for m in loaded:
            lines.append(f"  {m['name']} ({m.get('size', '?')}, {m.get('processor', '?')})")

    return "\n".join(lines)
