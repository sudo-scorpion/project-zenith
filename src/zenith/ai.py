from __future__ import annotations

import json
import subprocess
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


def _ollama_generate(model: str, prompt: str) -> str:
    ollama = resolve_binary("ollama")
    if not ollama:
        raise SystemExit("ollama is not installed")
    result = subprocess.run([ollama, "run", model, prompt], capture_output=True, text=True, check=False, env=with_local_bin_path())
    output = result.stdout.strip().replace("```bash", "").replace("```", "").strip()
    if not output:
        raise SystemExit("ollama did not return a command")
    return output


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
    command = _ollama_generate(str(config.ai.get("model", "llama3.2:3b")), prompt)
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


def nav(paths: Paths, config: ResolvedConfig, request: str) -> AIResult:
    if not request.strip():
        raise SystemExit('Usage: zen nav "<request>"')
    return _result_for(paths, config, "nav", request)


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
    answer = input("Execute generated safe command? [y/N] " ).strip().lower()
    if answer != "y":
        return 0
    return subprocess.run(result.command, shell=True, check=False, env=with_local_bin_path()).returncode
