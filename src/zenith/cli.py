from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess

from . import __version__
from .ai import ask, fix, maybe_execute, nav, render_result
from .config import config_path, load_config, show_config, validate_config, write_config
from .detect import detect_environment
from .doctor import doctor_report, render_doctor
from .install import install_core, install_surface, surface_support_error
from .logging_utils import fail, note, warn
from .updates import render_upgrade_report, startup_upgrade_plan, surface_upgrade_report
from .paths import build_paths, ensure_state_dirs
from .rollback import rollback, uninstall
from .shells import SUPPORTED_SHELLS
from .status import render_status
from .surface import apply_orbit, sync_orbit
from .workspace import attach_session, kill_session, list_sessions, new_session, open_workspace


def _default_container_name() -> str:
    return os.environ.get("ZENITH_CONTAINER_NAME", "zenith-shell")


def _container_exists(name: str) -> bool:
    if not shutil.which("podman"):
        return False
    return subprocess.run(["podman", "container", "exists", name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def _open_default_shell(env_mode: str) -> int:
    if env_mode == "container":
        shell = os.environ.get("SHELL") or shutil.which("bash") or shutil.which("sh")
        if not shell:
            raise SystemExit("No interactive shell found")
        return subprocess.run([shell], check=False).returncode
    name = _default_container_name()
    if not shutil.which("podman") or not _container_exists(name):
        raise SystemExit(f"No Zenith container named {name!r} is available. Run ./bootstrap.sh first or use zen --help.")
    start = subprocess.run(["podman", "start", name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if start.returncode != 0:
        stderr = (start.stderr or "").strip()
        if "already running" not in stderr.lower():
            raise SystemExit(stderr or f"Unable to start container {name!r}")
    return subprocess.run(["podman", "exec", "-it", "-w", "/workspace", name, "bash"], check=False).returncode


def add_common_flags(parser: argparse.ArgumentParser, *, json_flag: bool = False) -> None:
    parser.add_argument("--profile", choices=["personal", "safe"])
    parser.add_argument("--mode", choices=["auto", "host", "container"])
    parser.add_argument("--shell", choices=list(SUPPORTED_SHELLS))
    parser.add_argument("--terminal")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    if json_flag:
        parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zen")
    sub = parser.add_subparsers(dest="command")

    install = sub.add_parser("install")
    install.add_argument("target", choices=["core", "surface", "all"])
    install.add_argument("--packages", action="store_true", help="Install system packages via the host package manager (uses sudo when not root)")
    add_common_flags(install)

    uninstall_cmd = sub.add_parser("uninstall")
    add_common_flags(uninstall_cmd)

    rollback_cmd = sub.add_parser("rollback")
    add_common_flags(rollback_cmd)

    doctor = sub.add_parser("doctor")
    add_common_flags(doctor, json_flag=True)

    status = sub.add_parser("status")
    add_common_flags(status, json_flag=True)

    shell_parser = sub.add_parser("shell", aliases=["enter"])
    add_common_flags(shell_parser)

    workspace = sub.add_parser("workspace")
    ws_sub = workspace.add_subparsers(dest="workspace_command")
    ws_new = ws_sub.add_parser("new")
    ws_new.add_argument("name")
    ws_sub.add_parser("list")
    ws_kill = ws_sub.add_parser("kill")
    ws_kill.add_argument("name", nargs="?")
    ws_attach = ws_sub.add_parser("attach")
    ws_attach.add_argument("name")
    add_common_flags(workspace)

    orbit = sub.add_parser("orbit")
    orbit.add_argument("profile", choices=["celestial", "matrix", "quantum", "void"])
    add_common_flags(orbit)

    sync_cmd = sub.add_parser("sync")
    add_common_flags(sync_cmd)

    ask_parser = sub.add_parser("ask", aliases=["nav", "ai"])
    ask_parser.add_argument("request", nargs="+")
    add_common_flags(ask_parser, json_flag=True)

    fix_parser = sub.add_parser("fix")
    add_common_flags(fix_parser, json_flag=True)

    config_parser = sub.add_parser("config")
    config_parser.add_argument("config_command", choices=["show", "path", "validate", "edit"])
    add_common_flags(config_parser)

    upgrade = sub.add_parser("upgrade")
    upgrade.add_argument("target", choices=["surface"])
    add_common_flags(upgrade, json_flag=True)
    upgrade.add_argument("--check", action="store_true")
    upgrade.add_argument("--startup-check", action="store_true", help=argparse.SUPPRESS)

    # context
    context_p = sub.add_parser("context")
    ctx_sub = context_p.add_subparsers(dest="context_command")
    ctx_set = ctx_sub.add_parser("set")
    ctx_set.add_argument("task", nargs="+")
    ctx_sub.add_parser("show")
    ctx_sub.add_parser("clear")
    add_common_flags(context_p)

    # agent
    agent_p = sub.add_parser("agent")
    agent_p.add_argument("goal", nargs="+")
    agent_p.add_argument("--max-steps", type=int, default=None)
    add_common_flags(agent_p, json_flag=True)

    # models
    models_p = sub.add_parser("models")
    models_sub = models_p.add_subparsers(dest="models_command")
    models_sub.add_parser("list")
    models_sub.add_parser("status")
    models_pull = models_sub.add_parser("pull")
    models_pull.add_argument("name")
    models_set = models_sub.add_parser("set")
    models_set.add_argument("task", choices=["ask", "fix", "agent"])
    models_set.add_argument("model")
    add_common_flags(models_p)

    # plugins
    plugins_p = sub.add_parser("plugins")
    plugins_sub = plugins_p.add_subparsers(dest="plugins_command")
    plugins_sub.add_parser("list")
    plugins_run = plugins_sub.add_parser("run")
    plugins_run.add_argument("name")
    plugins_run.add_argument("plugin_args", nargs=argparse.REMAINDER)
    add_common_flags(plugins_p)

    # theme
    theme_p = sub.add_parser("theme")
    theme_sub = theme_p.add_subparsers(dest="theme_command")
    theme_sub.add_parser("list")
    theme_apply = theme_sub.add_parser("apply")
    theme_apply.add_argument("name")
    theme_preview = theme_sub.add_parser("preview")
    theme_preview.add_argument("name")
    theme_export = theme_sub.add_parser("export")
    theme_export.add_argument("name")
    theme_export.add_argument("--output", default=None)
    add_common_flags(theme_p)

    sub.add_parser("version")
    return parser


def _open_editor(config_file: str) -> int:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or shutil.which("nano") or shutil.which("vi")
    if not editor:
        raise SystemExit("No editor found. Set VISUAL or EDITOR.")
    command = shlex.split(editor) + [config_file]
    return subprocess.run(command, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = build_paths()
    ensure_state_dirs(paths)
    config = load_config(
        paths,
        cli_profile=getattr(args, "profile", None),
        cli_mode=getattr(args, "mode", None),
        cli_shell=getattr(args, "shell", None),
        cli_terminal=getattr(args, "terminal", None),
    )
    env = detect_environment(config.mode)

    if not args.command:
        return _open_default_shell(env.resolved_mode)

    try:
        if args.command == "install":
            allow_pkg = getattr(args, 'packages', False)
            if args.target == "core":
                install_core(paths, config, env, args.dry_run, args.yes, allow_packages=allow_pkg)
            elif args.target == "surface":
                install_surface(paths, config, env, args.dry_run, args.yes)
            else:
                install_core(paths, config, env, args.dry_run, args.yes, allow_packages=allow_pkg)
                error = surface_support_error(env)
                if error:
                    warn(f"Skipping surface install: {error}")
                else:
                    install_surface(paths, config, env, args.dry_run, args.yes)
            return 0

        if args.command == "rollback":
            rollback(paths, dry_run=args.dry_run)
            return 0

        if args.command == "uninstall":
            uninstall(paths, dry_run=args.dry_run)
            return 0

        if args.command == "doctor":
            print(render_doctor(doctor_report(paths, config, env), args.json))
            return 0

        if args.command == "status":
            print(render_status(paths, config, env, args.json))
            return 0

        if args.command in {"shell", "enter"}:
            return _open_default_shell(env.resolved_mode)

        if args.command == "workspace":
            workspace_command = getattr(args, "workspace_command", None)
            if not workspace_command:
                return open_workspace(config)
            if workspace_command == "new":
                return new_session(config, paths, args.name, args.dry_run)
            if workspace_command == "list":
                sessions = list_sessions(config, paths)
                if not sessions:
                    note("No active or registered workspace sessions.")
                    return 0
                for s in sessions:
                    created = f"  (created {s['created_at']})" if s["created_at"] else ""
                    print(f"  {s['name']:<24} {s['status']}{created}")
                return 0
            if workspace_command == "kill":
                return kill_session(config, paths, getattr(args, "name", None), args.dry_run)
            if workspace_command == "attach":
                return attach_session(config, args.name)

        if args.command == "orbit":
            apply_orbit(paths.home, args.profile)
            return 0

        if args.command == "sync":
            sync_orbit(paths.home)
            return 0

        if args.command in {"ask", "nav", "ai"}:
            request = " ".join(args.request)
            result = ask(paths, config, request)
            print(render_result(result, args.json))
            return maybe_execute(result, True)

        if args.command == "fix":
            result = fix(paths, config)
            print(render_result(result, args.json))
            return maybe_execute(result, True)

        if args.command == "upgrade":
            if args.target == "surface":
                if args.startup_check:
                    plan = startup_upgrade_plan(paths, config, env)
                    if not plan["run"]:
                        return 0
                    if plan["should_upgrade"]:
                        if plan["message"]:
                            note(str(plan["message"]))
                        install_surface(paths, config, env, args.dry_run, True, force_upgrade=True)
                        return 0
                    if plan["message"]:
                        print(str(plan["message"]))
                    elif args.json:
                        print(render_upgrade_report(dict(plan["report"]), True))
                    return 0

                report = surface_upgrade_report(paths, config, env, allow_network=True)
                if args.check or args.json:
                    print(render_upgrade_report(report, args.json))
                    return 0
                if report["status"] in {"current", "unsupported-terminal", "unknown"}:
                    message = str(report.get("message", "No upgrade action needed."))
                    if report["status"] == "unsupported-terminal":
                        raise SystemExit(message)
                    note(message)
                    return 0
                install_surface(paths, config, env, args.dry_run, args.yes, force_upgrade=True)
                return 0

        if args.command == "config":
            if args.config_command == "show":
                print(show_config(paths, config), end="")
                return 0
            if args.config_command == "path":
                print(config_path(paths))
                return 0
            if args.config_command == "validate":
                validate_config(config)
                print("Config looks valid")
                return 0
            if not paths.config_file.exists():
                write_config(paths, config)
            returncode = _open_editor(str(paths.config_file))
            try:
                load_config(paths)
            except Exception as exc:
                warn(f"Config has an error after editing: {exc}")
            return returncode

        if args.command == "context":
            from .context import clear_context, set_context, show_context
            context_command = getattr(args, "context_command", None)
            if context_command == "set":
                ctx = set_context(paths, " ".join(args.task))
                from .logging_utils import ok as _ok
                _ok(f"Context set: {ctx.current_task}")
                if ctx.project_root:
                    note(f"Project root: {ctx.project_root}")
                return 0
            if context_command == "clear":
                clear_context(paths)
                from .logging_utils import ok as _ok
                _ok("Context cleared")
                return 0
            print(show_context(paths))
            return 0

        if args.command == "agent":
            from .agent import run_agent
            import dataclasses as _dc
            goal = " ".join(args.goal)
            max_steps = args.max_steps or int(config.agent.get("max_steps", 8))
            run = run_agent(paths, config, goal, dry_run=args.dry_run, max_steps=max_steps, yes=args.yes)
            if getattr(args, "json", False):
                import json as _json

                def _step_dict(s) -> dict:
                    return _dc.asdict(s)

                print(_json.dumps({
                    "goal": run.goal,
                    "started": run.started,
                    "status": run.status,
                    "abort_reason": run.abort_reason,
                    "steps": [_step_dict(s) for s in run.steps],
                }, indent=2))
            return 0 if run.status in {"completed", "dry-run"} else 1

        if args.command == "models":
            from .model_manager import (
                TASK_TYPES, list_loaded_models, list_local_models, model_for_task,
                pull_model, render_model_list, set_model_for_task,
            )
            models_command = getattr(args, "models_command", None)
            if models_command == "list" or not models_command:
                local = list_local_models(config)
                loaded = list_loaded_models(config)
                assignments = {t: model_for_task(config, t) for t in TASK_TYPES}
                print(render_model_list(local, loaded, assignments))
                return 0
            if models_command == "status":
                loaded = list_loaded_models(config)
                if not loaded:
                    note("No models currently loaded in Ollama VRAM.")
                    return 0
                for m in loaded:
                    print(f"  {m['name']:<35} {m.get('size', '?'):>6}  {m.get('processor', '?')}")
                return 0
            if models_command == "pull":
                return pull_model(config, args.name)
            if models_command == "set":
                set_model_for_task(paths, config, args.task, args.model)
                from .logging_utils import ok as _ok
                _ok(f"Model for '{args.task}' set to '{args.model}'")
                return 0

        if args.command == "plugins":
            from .plugins import discover_plugins, render_plugin_list, run_plugin
            if not config.plugins.get("enabled", True):
                note("Plugins are disabled. Set plugins.enabled = true in config.")
                return 0
            plugins_command = getattr(args, "plugins_command", None)
            plugins = discover_plugins(paths)
            if plugins_command == "list" or not plugins_command:
                print(render_plugin_list(plugins))
                return 0
            if plugins_command == "run":
                match = next((p for p in plugins if p.command == args.name), None)
                if not match:
                    raise SystemExit(f"No plugin named '{args.name}'. Try: zen plugins list")
                return run_plugin(match, list(args.plugin_args), config, paths)

        if args.command == "theme":
            from .theme import apply_theme, export_theme, list_themes, preview_theme
            theme_command = getattr(args, "theme_command", None)
            if theme_command == "list" or not theme_command:
                themes = list_themes(paths)
                active = config.surface.get("theme") or config.surface.get("orbit_profile", "")
                for t in themes:
                    marker = "*" if t.name == active else " "
                    src = f"[{t.source}]"
                    print(f"  {marker} {t.name:<20} {src:<9} {t.description}")
                return 0
            if theme_command == "apply":
                apply_theme(paths, config, args.name, dry_run=args.dry_run)
                return 0
            if theme_command == "preview":
                print(preview_theme(paths, args.name))
                return 0
            if theme_command == "export":
                content = export_theme(paths, config, args.name)
                if args.output:
                    from pathlib import Path as _Path
                    _Path(args.output).write_text(content, encoding="utf-8")
                    from .logging_utils import ok as _ok
                    _ok(f"Theme exported to {args.output}")
                else:
                    print(content)
                return 0

        if args.command == "version":
            print(__version__)
            return 0
    except (ValueError, FileNotFoundError, OSError, RuntimeError) as exc:
        fail(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
