from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .assets import read_asset_text
from .binaries import resolve_binary, with_local_bin_path
from .models import AIResult, Paths, ResolvedConfig
from .shells import shell_history_path

SAFE_PREFIXES = (
    "pwd",
    "ls",
    "eza",
    "grep",
    "rg",
    "find",
    "cat",
    "bat",
    "git status",
    "git log",
    "git show",
    "git diff",
    "tar -x",
    "unzip",
)
REVIEW_PREFIXES = (
    "sudo",
    "dnf",
    "pacman",
    "apt",
    "apt-get",
    "zypper",
    "apk",
    "brew",
    "systemctl",
    "service",
    "chmod",
    "chown",
    "mv",
    "cp",
    "sed -i",
    "tee",
    "touch",
)
BLOCKED_MARKERS = ("rm -rf", "mkfs", "fdisk", "iptables", "ufw", "| sh", "| bash", "curl ", "wget ")
COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
    },
    "required": ["command"],
    "additionalProperties": False,
}


def _prompt_text(paths: Paths, name: str) -> str:
    local = paths.prompt_dir / f"{name}.prompt"
    if local.exists():
        return local.read_text(encoding="utf-8")
    return read_asset_text("prompts", f"{name}.prompt")


def _classify(command: str) -> tuple[str, bool, str]:
    lowered = command.strip().lower()
    if any(marker in lowered for marker in BLOCKED_MARKERS):
        return "blocked", True, "This command is high risk and blocked from direct execution in Zenith V1."
    if lowered.startswith(SAFE_PREFIXES):
        return "safe", False, "Read-oriented or low-impact command."
    if lowered.startswith(REVIEW_PREFIXES):
        return "review", True, "This command can change packages, services, permissions, or files and should be reviewed."
    return "review", True, "This command should be reviewed before execution."


def _normalize_command(output: str) -> str:
    return output.strip().replace("```bash", "").replace("```", "").strip()


def _ai_model_for(config: ResolvedConfig, kind: str) -> str:
    lookup = "ask_model" if kind == "nav" else f"{kind}_model"
    specific = str(config.ai.get(lookup, "")).strip()
    if not specific and kind == "nav":
        specific = str(config.ai.get("nav_model", "")).strip()
    if specific:
        return specific
    return str(config.ai.get("model", "qwen3.5:4b"))


def _ollama_host(config: ResolvedConfig) -> str:
    return str(config.ai.get("host", "http://127.0.0.1:11434")).rstrip("/")


def _ollama_timeout(config: ResolvedConfig) -> int:
    try:
        timeout = int(config.ai.get("timeout_seconds", 90))
    except (TypeError, ValueError):
        timeout = 90
    return max(timeout, 1)


def _ollama_options(config: ResolvedConfig) -> dict[str, int | float]:
    options: dict[str, int | float] = {}
    for key in ("temperature", "num_ctx", "num_predict", "top_k", "top_p", "repeat_penalty", "num_gpu"):
        if key not in config.ai:
            continue
        value = config.ai.get(key)
        if value in (None, ""):
            continue
        options[key] = value
    return options


def _structured_output_enabled(config: ResolvedConfig) -> bool:
    return bool(config.ai.get("structured_output", True))


def _extract_command(response_text: str, structured_output: bool) -> str:
    if not structured_output:
        return _normalize_command(response_text)
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return _normalize_command(response_text)
    command = payload.get("command", "") if isinstance(payload, dict) else ""
    return _normalize_command(str(command))


def _ollama_generate(config: ResolvedConfig, kind: str, prompt: str) -> str:
    ollama = resolve_binary("ollama")
    if not ollama:
        raise SystemExit("ollama is not installed")

    structured_output = _structured_output_enabled(config)
    body: dict[str, object] = {
        "model": _ai_model_for(config, kind),
        "prompt": prompt,
        "stream": False,
        "keep_alive": config.ai.get("keep_alive", "15m"),
        "options": _ollama_options(config),
    }
    if structured_output:
        body["format"] = COMMAND_SCHEMA

    request = urllib.request.Request(
        f"{_ollama_host(config)}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_ollama_timeout(config)) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise SystemExit(f"ollama generate failed: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"unable to reach ollama at {_ollama_host(config)}") from exc

    response_text = str(payload.get("response", "")).strip()
    command = _extract_command(response_text, structured_output)
    if not command:
        raise SystemExit("ollama did not return a command")
    return command


def ollama_runtime_details() -> dict[str, str]:
    ollama = resolve_binary("ollama")
    if not ollama:
        return {"status": "unavailable", "model": "", "processor": "", "context": ""}
    result = subprocess.run([ollama, "ps"], capture_output=True, text=True, check=False, env=with_local_bin_path())
    if result.returncode != 0:
        return {"status": "unknown", "model": "", "processor": "", "context": ""}
    lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return {"status": "idle", "model": "", "processor": "", "context": ""}
    for line in lines[1:]:
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) >= 5:
            return {
                "status": "running",
                "model": parts[0],
                "processor": parts[3],
                "context": parts[4],
            }
    return {"status": "running", "model": lines[1].strip(), "processor": "unknown", "context": ""}


def _log(paths: Paths, kind: str, request: str, result: AIResult) -> None:
    audit_file = paths.audit_dir / f"{datetime.now():%Y%m%d}.log"
    line = json.dumps(
        {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "kind": kind,
            "request": request,
            "command": result.command,
            "risk": result.risk,
        }
    )
    with audit_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _result_for(paths: Paths, config: ResolvedConfig, kind: str, request: str, *, cwd: Path | None = None) -> AIResult:
    working_dir = cwd or Path.cwd()
    prompt = _prompt_text(paths, kind).replace("{{PWD}}", str(working_dir)).replace("{{REQUEST}}", request)
    command = _ollama_generate(config, kind, prompt)
    risk, requires_confirmation, explanation = _classify(command)
    result = AIResult(
        intent=request,
        command=command,
        risk=risk,
        explanation=explanation,
        requires_confirmation=requires_confirmation,
    )
    if config.ai.get("log_generated_commands", True):
        _log(paths, kind, request, result)
    return result


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def read_fix_context(paths: Paths) -> dict[str, str | int | None]:
    command = _read_text(paths.last_command_file)
    stderr = _read_text(paths.last_stderr_file)
    pwd = _read_text(paths.last_pwd_file)
    status_raw = _read_text(paths.last_status_file)
    exit_status: int | None = None
    if status_raw:
        try:
            exit_status = int(status_raw)
        except ValueError:
            exit_status = None
    return {
        "command": command,
        "stderr": stderr[-4000:],
        "pwd": pwd,
        "exit_status": exit_status,
    }


def _history_candidates(paths: Paths, shell: str) -> list[Path]:
    candidates = [shell_history_path(paths, shell), paths.home / ".bash_history", paths.home / ".zsh_history"]
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _history_command_from_line(shell: str, line: str) -> str:
    stripped = line.strip()
    if shell == "zsh" and stripped.startswith(": ") and ";" in stripped:
        return stripped.split(";", 1)[1].strip()
    return stripped


def _latest_history_command(paths: Paths, shell: str) -> str:
    for history_file in _history_candidates(paths, shell):
        if not history_file.exists():
            continue
        lines = history_file.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            command = _history_command_from_line("zsh" if history_file.name == ".zsh_history" else "bash", line)
            if command:
                return command
    return ""


def ask(paths: Paths, config: ResolvedConfig, request: str) -> AIResult:
    if not request.strip():
        raise SystemExit('Usage: zen ask "<request>"')
    return _result_for(paths, config, "nav", request)


def nav(paths: Paths, config: ResolvedConfig, request: str) -> AIResult:
    return ask(paths, config, request)


def fix(paths: Paths, config: ResolvedConfig) -> AIResult:
    context = read_fix_context(paths)
    if context["command"]:
        if context["exit_status"] == 0 and not context["stderr"]:
            raise SystemExit("No failed command context captured yet")
        request_lines = [
            f"Previous command: {context['command']}",
            f"Working directory: {context['pwd'] or Path.cwd()}",
            f"Exit status: {context['exit_status'] if context['exit_status'] is not None else 'unknown'}",
            f"stderr: {context['stderr'] or 'No stderr was captured.'}",
            "Suggest a corrected replacement command.",
        ]
        return _result_for(paths, config, "fix", "\n".join(request_lines), cwd=Path(context["pwd"] or Path.cwd()))

    last_command = _latest_history_command(paths, config.shell)
    if not last_command:
        raise SystemExit("No shell history or shell failure context available to inspect")
    request = f"Previous command: {last_command}\nNo captured stderr was available. Suggest a corrected replacement command."
    return _result_for(paths, config, "fix", request)


def render_result(result: AIResult, as_json: bool) -> str:
    if as_json:
        return json.dumps(result.__dict__, indent=2)
    return "\n".join(
        [
            f"Intent: {result.intent}",
            f"Command: {result.command}",
            f"Risk: {result.risk}",
            f"Requires confirmation: {result.requires_confirmation}",
            f"Explanation: {result.explanation}",
        ]
    )


def maybe_execute(result: AIResult, execute: bool) -> int:
    if not execute:
        return 0
    if result.risk != "safe":
        raise SystemExit("Refusing to auto-execute non-safe command")
    answer = input("Execute generated safe command? [y/N] ").strip().lower()
    if answer != "y":
        return 0
    return subprocess.run(result.command, shell=True, check=False, env=with_local_bin_path()).returncode
