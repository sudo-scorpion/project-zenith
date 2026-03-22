from __future__ import annotations

import json
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .ai import classify_command, ollama_generate, ollama_generate_structured, prompt_text
from .assets import read_asset_text
from .context import format_context_for_prompt, load_context
from .logging_utils import fail, info, note, ok, warn
from .models import AgentRun, AgentStep, Paths, ResolvedConfig

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        }
    },
    "required": ["steps"],
    "additionalProperties": False,
}

ABORT_SCHEMA = {
    "type": "object",
    "properties": {
        "abort": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["abort"],
    "additionalProperties": False,
}


def _agent_prompt(paths: Paths, name: str) -> str:
    local = paths.prompt_dir / f"{name}.prompt"
    if local.exists():
        return local.read_text(encoding="utf-8")
    try:
        return read_asset_text("prompts", f"{name}.prompt")
    except Exception as exc:
        raise SystemExit(f"Missing agent prompt file: {name}.prompt") from exc


def _format_history(steps: list[AgentStep]) -> str:
    if not steps:
        return "(none)"
    lines = []
    for step in steps:
        lines.append(f"Step {step.index + 1}: {step.command} (exit {step.exit_code})")
        if step.stdout.strip():
            lines.append(f"  stdout: {step.stdout.strip()[:400]}")
        if step.stderr.strip():
            lines.append(f"  stderr: {step.stderr.strip()[:200]}")
    return "\n".join(lines)


def _generate_plan(
    paths: Paths,
    config: ResolvedConfig,
    goal: str,
    ctx_block: str,
    cwd: Path,
    max_steps: int,
) -> list[str]:
    template = _agent_prompt(paths, "agent.plan")
    prompt = (
        template
        .replace("{{CONTEXT}}", ctx_block)
        .replace("{{PWD}}", str(cwd))
        .replace("{{GOAL}}", goal)
        .replace("{{MAX_STEPS}}", str(max_steps))
    )
    result = ollama_generate_structured(config, "agent", prompt, PLAN_SCHEMA)
    steps = result.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise SystemExit("Agent planner returned an empty plan")
    return [str(s).strip() for s in steps if str(s).strip()]


def _generate_step_command(
    paths: Paths,
    config: ResolvedConfig,
    goal: str,
    step_desc: str,
    history: list[AgentStep],
    ctx_block: str,
    cwd: Path,
) -> str:
    template = _agent_prompt(paths, "agent.step")
    prompt = (
        template
        .replace("{{CONTEXT}}", ctx_block)
        .replace("{{PWD}}", str(cwd))
        .replace("{{GOAL}}", goal)
        .replace("{{STEP}}", step_desc)
        .replace("{{HISTORY}}", _format_history(history))
    )
    return ollama_generate(config, "agent", prompt)


def _should_abort(
    paths: Paths,
    config: ResolvedConfig,
    goal: str,
    command: str,
    exit_code: int,
    stderr: str,
) -> tuple[bool, str]:
    template = _agent_prompt(paths, "agent.abort")
    prompt = (
        template
        .replace("{{GOAL}}", goal)
        .replace("{{COMMAND}}", command)
        .replace("{{EXIT_CODE}}", str(exit_code))
        .replace("{{STDERR}}", stderr.strip()[:400])
    )
    try:
        result = ollama_generate_structured(config, "agent", prompt, ABORT_SCHEMA)
        return bool(result.get("abort", False)), str(result.get("reason", ""))
    except SystemExit:
        return False, ""


def _execute_step(command: str, cwd: Path, timeout: int) -> tuple[str, str, int]:
    try:
        tokens = shlex.split(command)
        proc = subprocess.run(
            tokens,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
            check=False,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except ValueError:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
            check=False,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"step timed out after {timeout}s", 124
    except Exception as exc:
        return "", str(exc), 1


def _confirm_step(index: int, command: str, risk: str, explanation: str) -> bool:
    note(f"Step {index + 1} [{risk}]: {command}")
    note(f"  {explanation}")
    try:
        answer = input("Execute this step? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer == "y"


def _slug(goal: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", goal.lower())
    return cleaned.strip("-")[:40]


def _log_run(paths: Paths, run: AgentRun) -> None:
    ts = run.started.replace(":", "-").replace("+", "").replace(".", "")[:15]
    filename = f"{ts}_{_slug(run.goal)}.json"
    log_file = paths.agent_log_dir / filename

    def _step_dict(s: AgentStep) -> dict:
        return {
            "index": s.index,
            "command": s.command,
            "risk": s.risk,
            "stdout": s.stdout,
            "stderr": s.stderr,
            "exit_code": s.exit_code,
            "timestamp": s.timestamp,
        }

    data = {
        "goal": run.goal,
        "started": run.started,
        "status": run.status,
        "abort_reason": run.abort_reason,
        "steps": [_step_dict(s) for s in run.steps],
    }
    log_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run_agent(
    paths: Paths,
    config: ResolvedConfig,
    goal: str,
    *,
    dry_run: bool = False,
    max_steps: int = 8,
    yes: bool = False,
) -> AgentRun:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run = AgentRun(goal=goal, started=started)

    ctx = load_context(paths)
    ctx_block = format_context_for_prompt(ctx)
    cwd = Path.cwd()
    step_timeout = int(config.agent.get("step_timeout", 30))
    pause_on_review = bool(config.agent.get("pause_on_review", True))
    log_runs = bool(config.agent.get("log_runs", True))

    note(f"Agent goal: {goal}")
    note("Planning steps...")

    try:
        plan = _generate_plan(paths, config, goal, ctx_block, cwd, max_steps)
    except SystemExit as exc:
        run.status = "aborted"
        run.abort_reason = str(exc)
        fail(str(exc))
        return run

    if not plan:
        run.status = "aborted"
        run.abort_reason = "Planner returned empty plan"
        fail(run.abort_reason)
        return run

    info(f"Plan: {len(plan)} step(s)")
    for i, step_desc in enumerate(plan):
        info(f"  {i + 1}. {step_desc}")

    if dry_run:
        run.status = "dry-run"
        return run

    for i, step_desc in enumerate(plan[:max_steps]):
        note(f"\nStep {i + 1}/{min(len(plan), max_steps)}: {step_desc}")

        try:
            command = _generate_step_command(paths, config, goal, step_desc, run.steps, ctx_block, cwd)
        except SystemExit as exc:
            run.status = "aborted"
            run.abort_reason = f"Step {i + 1} command generation failed: {exc}"
            fail(run.abort_reason)
            break

        risk, requires_confirmation, explanation = classify_command(command)

        if risk == "blocked":
            run.status = "aborted"
            run.abort_reason = f"Step {i + 1} command blocked: {command}"
            fail(f"Blocked command — stopping agent: {command}")
            break

        if risk == "review" and pause_on_review and not yes:
            if not _confirm_step(i, command, risk, explanation):
                run.status = "aborted"
                run.abort_reason = f"User declined step {i + 1}: {command}"
                note("Agent stopped at user request.")
                break
        else:
            info(f"  [{risk}] {command}")

        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        stdout, stderr, exit_code = _execute_step(command, cwd, step_timeout)

        step = AgentStep(
            index=i,
            command=command,
            risk=risk,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timestamp=timestamp,
        )
        run.steps.append(step)

        if exit_code == 0:
            ok(f"  exit 0")
            if stdout.strip():
                info(f"  {stdout.strip()[:300]}")
        else:
            warn(f"  exit {exit_code}")
            if stderr.strip():
                warn(f"  {stderr.strip()[:200]}")
            should_abort, reason = _should_abort(paths, config, goal, command, exit_code, stderr)
            if should_abort:
                run.status = "aborted"
                run.abort_reason = reason or f"Step {i + 1} failed and goal is unachievable"
                fail(f"Agent aborting: {run.abort_reason}")
                break

    else:
        run.status = "completed"

    if run.status == "running":
        run.status = "completed"

    if log_runs:
        try:
            _log_run(paths, run)
        except Exception:
            pass

    return run
