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
from .workspace import open_workspace


def add_common_flags(parser: argparse.ArgumentParser, *, json_flag: bool = False, execute_flag: bool = False) -> None:
    parser.add_argument("--profile", choices=["personal", "safe"])
    parser.add_argument("--mode", choices=["auto", "host", "container"])
    parser.add_argument("--shell", choices=list(SUPPORTED_SHELLS))
    parser.add_argument("--terminal")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    if json_flag:
        parser.add_argument("--json", action="store_true")
    if execute_flag:
        parser.add_argument("--execute", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zen")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install")
    install.add_argument("target", choices=["core", "surface", "all"])
    add_common_flags(install)

    uninstall_cmd = sub.add_parser("uninstall")
    add_common_flags(uninstall_cmd)

    rollback_cmd = sub.add_parser("rollback")
    add_common_flags(rollback_cmd)

    doctor = sub.add_parser("doctor")
    add_common_flags(doctor, json_flag=True)

    status = sub.add_parser("status")
    add_common_flags(status, json_flag=True)

    workspace = sub.add_parser("workspace")
    add_common_flags(workspace)

    orbit = sub.add_parser("orbit")
    orbit.add_argument("profile", choices=["celestial", "matrix", "quantum", "void"])
    add_common_flags(orbit)

    sync_cmd = sub.add_parser("sync")
    add_common_flags(sync_cmd)

    ask_parser = sub.add_parser("ask", aliases=["nav"])
    ask_parser.add_argument("request", nargs="+")
    add_common_flags(ask_parser, json_flag=True, execute_flag=True)

    fix_parser = sub.add_parser("fix")
    add_common_flags(fix_parser, json_flag=True, execute_flag=True)

    config_parser = sub.add_parser("config")
    config_parser.add_argument("config_command", choices=["show", "path", "validate", "edit"])
    add_common_flags(config_parser)

    upgrade = sub.add_parser("upgrade")
    upgrade.add_argument("target", choices=["surface"])
    add_common_flags(upgrade, json_flag=True)
    upgrade.add_argument("--check", action="store_true")
    upgrade.add_argument("--startup-check", action="store_true", help=argparse.SUPPRESS)

    version = sub.add_parser("version")
    add_common_flags(version)
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

    try:
        if args.command == "install":
            if args.target == "core":
                install_core(paths, config, env, args.dry_run, args.yes)
            elif args.target == "surface":
                install_surface(paths, config, env, args.dry_run, args.yes)
            else:
                install_core(paths, config, env, args.dry_run, args.yes)
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

        if args.command == "workspace":
            return open_workspace(config)

        if args.command == "orbit":
            apply_orbit(paths.home, args.profile)
            return 0

        if args.command == "sync":
            sync_orbit(paths.home)
            return 0

        if args.command in {"ask", "nav"}:
            request = " ".join(args.request)
            result = ask(paths, config, request)
            print(render_result(result, args.json))
            return maybe_execute(result, args.execute)

        if args.command == "fix":
            result = fix(paths, config)
            print(render_result(result, args.json))
            return maybe_execute(result, args.execute)

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
            return _open_editor(str(paths.config_file))

        if args.command == "version":
            print(__version__)
            return 0
    except Exception as exc:  # noqa: BLE001
        fail(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
