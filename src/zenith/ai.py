from __future__ import annotations

import json
import re
import shlex
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .assets import read_asset_text
from .binaries import resolve_binary, with_local_bin_path
from .models import AIResult, Paths, ResolvedConfig, TaskContext
from .shells import shell_history_path

SAFE_PREFIXES = (
    # navigation / listing
    "pwd",
    "ls",
    "eza",
    "lsd",
    "tree",
    "find",
    # output
    "echo",
    "printf",
    "print",
    # file reading
    "cat",
    "bat",
    "head",
    "tail",
    "less",
    "more",
    "file",
    "stat",
    "wc",
    # search
    "grep",
    "rg",
    "ag",
    "cut",
    "sort",
    "uniq",
    "diff",
    "cmp",
    # system info (read-only)
    "df",
    "du",
    "free",
    "ps",
    "uptime",
    "uname",
    "whoami",
    "id",
    "hostname",
    "date",
    "cal",
    "env",
    "printenv",
    "which",
    "type",
    "command",
    "man",
    "help",
    "history",
    "lsof",
    "ss",
    "ip addr",
    "ip link",
    "ip route",
    "ip neigh",
    "ip -s",
    "ifconfig",
    "ping",
    "traceroute",
    "nslookup",
    "dig",
    "host",
    # hash / checksum
    "md5sum",
    "sha1sum",
    "sha256sum",
    "sha512sum",
    # data tools
    "jq",
    "yq",
    "column",
    "xargs",
    # archives (extract only)
    "tar -x",
    "tar -t",
    "unzip",
    "unrar",
    "7z l",
    "7z x",
    # git (read-only)
    "git status",
    "git log",
    "git show",
    "git diff",
    "git branch",
    "git tag",
    "git remote",
    "git stash list",
    "git describe",
    "git rev-parse",
    # process / job
    "jobs",
    "fg",
    "bg",
    "wait",
    # misc utilities
    "locale",
    "ldd",
    "nm",
    "strings",
    "xxd",
    "od",
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
    "sed",
    "awk",
    "tr",
    "tee",
    "touch",
    "curl",
    "wget",
)
BLOCKED_MARKERS = (
    "rm -rf",
    "rm -r ",
    "rm --recursive",
    "mkfs",
    "fdisk",
    "iptables",
    "ufw",
    "| sh",
    "| bash",
    "| zsh",
    "| python",
    "| perl",
    "dd if=",
    "shred",
    "> /dev/",
    "chmod 777",
    "chmod -R 777",
)
COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
    },
    "required": ["command"],
    "additionalProperties": False,
}


def prompt_text(paths: Paths, name: str) -> str:
    local = paths.prompt_dir / f"{name}.prompt"
    if local.exists():
        return local.read_text(encoding="utf-8")
    return read_asset_text("prompts", f"{name}.prompt")


def _has_write_flags(command: str, write_flags: tuple[str, ...]) -> bool:
    """Check if a command string contains any of the specified write flags."""
    parts = command.strip().split()
    return any(flag in parts for flag in write_flags)


def classify_command(command: str) -> tuple[str, bool, str]:
    lowered = command.strip().lower()
    if any(marker in lowered for marker in BLOCKED_MARKERS):
        return "blocked", True, "This command is high risk and blocked from direct execution in Zenith V1."
    if lowered.startswith(SAFE_PREFIXES):
        return "safe", False, "Read-oriented or low-impact command."
    # Smart classification for curl/wget: read-only usage is safe
    if lowered.startswith(("curl", "wget")):
        curl_write_flags = ("-o", "--output", "-O", "--remote-name", "-T", "--upload-file", "--data", "-d", "--post")
        wget_write_flags = ("-O", "--output-document", "-P", "--directory-prefix")
        flags = curl_write_flags if lowered.startswith("curl") else wget_write_flags
        if not _has_write_flags(command, flags):
            return "safe", False, "Read-only network request."
    if lowered.startswith(REVIEW_PREFIXES):
        return "review", True, "This command can change packages, services, permissions, or files — review before running."
    return "review", True, "Unrecognized command — review before running."


def _normalize_command(output: str) -> str:
    return output.strip().replace("```bash", "").replace("```sh", "").replace("```", "").strip()


def _command_from_text(response_text: str) -> str:
    cleaned = _normalize_command(response_text)
    if not cleaned:
        return ""

    json_match = re.search(r'"command"\s*:\s*"([^"]+)"', cleaned)
    if json_match:
        return _normalize_command(json_match.group(1))

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        for prefix in ("command:", "shell command:", "run:", "answer:"):
            if lowered.startswith(prefix):
                line = line.split(":", 1)[1].strip()
                break
        if line:
            return _normalize_command(line)
    return cleaned


_KIND_TO_TASK = {"nav": "ask", "fix": "fix", "agent": "agent"}


def _ai_model_for(config: ResolvedConfig, kind: str) -> str:
    task = _KIND_TO_TASK.get(kind, kind)
    models_table = config.ai.get("models", {})
    if isinstance(models_table, dict) and models_table.get(task, "").strip():
        return str(models_table[task]).strip()
    lookup = "ask_model" if kind == "nav" else f"{kind}_model"
    specific = str(config.ai.get(lookup, "")).strip()
    if not specific and kind == "nav":
        specific = str(config.ai.get("nav_model", "")).strip()
    if specific:
        return specific
    return str(config.ai.get("model", "qwen2.5-coder:7b"))


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
        return _command_from_text(response_text)
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return _command_from_text(response_text)
    command = payload.get("command", "") if isinstance(payload, dict) else ""
    return _normalize_command(str(command))


def _ollama_request(config: ResolvedConfig, kind: str, prompt: str, structured_output: bool) -> dict[str, object]:
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
    if not isinstance(payload, dict):
        return {}
    return payload


def ollama_generate(config: ResolvedConfig, kind: str, prompt: str) -> str:
    ollama = resolve_binary("ollama")
    if not ollama:
        raise SystemExit("ollama is not installed")

    structured_output = _structured_output_enabled(config)
    payload = _ollama_request(config, kind, prompt, structured_output)
    response_text = str(payload.get("response") or payload.get("message", {}).get("content", "")).strip()
    command = _extract_command(response_text, structured_output)
    if command:
        return command
    if structured_output:
        payload = _ollama_request(config, kind, prompt, False)
        response_text = str(payload.get("response") or payload.get("message", {}).get("content", "")).strip()
        command = _extract_command(response_text, False)
        if command:
            return command
    snippet = _normalize_command(response_text)[:160]
    raise SystemExit(f"ollama did not return a command: {snippet or 'empty response'}")


def ollama_generate_structured(config: ResolvedConfig, kind: str, prompt: str, schema: dict) -> dict:
    """Call Ollama and return the parsed JSON response matching schema. Raises SystemExit on failure."""
    ollama = resolve_binary("ollama")
    if not ollama:
        raise SystemExit("ollama is not installed")
    body: dict[str, object] = {
        "model": _ai_model_for(config, kind),
        "prompt": prompt,
        "stream": False,
        "keep_alive": config.ai.get("keep_alive", "15m"),
        "options": _ollama_options(config),
        "format": schema,
    }
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
    response_text = str(payload.get("response") or "").strip()
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ollama returned invalid JSON: {response_text[:120]}") from exc


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


def _result_for(
    paths: Paths,
    config: ResolvedConfig,
    kind: str,
    request: str,
    *,
    cwd: Path | None = None,
    ctx: TaskContext | None = None,
) -> AIResult:
    from .context import format_context_for_prompt
    working_dir = cwd or Path.cwd()
    ctx_block = format_context_for_prompt(ctx) if ctx else ""
    prompt = (
        prompt_text(paths, kind)
        .replace("{{PWD}}", str(working_dir))
        .replace("{{REQUEST}}", request)
        .replace("{{CONTEXT}}", ctx_block)
    )
    command = ollama_generate(config, kind, prompt)
    risk, requires_confirmation, explanation = classify_command(command)
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
    from .context import load_context
    ctx = load_context(paths)
    return _result_for(paths, config, "nav", request, ctx=ctx)


def nav(paths: Paths, config: ResolvedConfig, request: str) -> AIResult:
    return ask(paths, config, request)


def fix(paths: Paths, config: ResolvedConfig) -> AIResult:
    from .context import load_context, push_error
    ctx = load_context(paths)
    context = read_fix_context(paths)
    if context["command"]:
        if context["exit_status"] == 0 and not context["stderr"]:
            raise SystemExit("No failed command context captured yet")
        if context["stderr"]:
            push_error(paths, str(context["stderr"]))
            ctx = load_context(paths)
        request_lines = [
            f"Previous command: {context['command']}",
            f"Working directory: {context['pwd'] or Path.cwd()}",
            f"Exit status: {context['exit_status'] if context['exit_status'] is not None else 'unknown'}",
            f"stderr: {context['stderr'] or 'No stderr was captured.'}",
            "Suggest a corrected replacement command.",
        ]
        return _result_for(paths, config, "fix", "\n".join(request_lines), cwd=Path(context["pwd"] or Path.cwd()), ctx=ctx)

    last_command = _latest_history_command(paths, config.shell)
    if not last_command:
        raise SystemExit("No shell history or shell failure context available to inspect")
    from .logging_utils import note
    note("No failure context captured — using last shell history entry as context.")
    request = f"Previous command: {last_command}\nNo captured stderr was available. Suggest a corrected replacement command."
    return _result_for(paths, config, "fix", request, ctx=ctx)


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
    """Prompt the user to execute the generated command.

    - safe commands: execute immediately without prompting
    - review commands: prompt, default N (must type y to run)
    - blocked commands: refuse
    """
    if result.risk == "blocked":
        return 0

    if result.risk != "safe":
        prompt = f"\033[33m⚠ Review — execute?\033[0m [y/N] "
        try:
            answer = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if answer != "y":
            return 0

    _SHELL_METACHAR = re.compile(r"(?<![\\])[|><&;`$()]")
    try:
        tokens = shlex.split(result.command)
    except ValueError:
        tokens = None
    if tokens is None or _SHELL_METACHAR.search(result.command):
        return subprocess.run(result.command, shell=True, check=False, env=with_local_bin_path()).returncode
    return subprocess.run(tokens, shell=False, check=False, env=with_local_bin_path()).returncode
