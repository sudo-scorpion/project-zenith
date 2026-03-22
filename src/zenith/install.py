from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from .assets import iter_asset_files, materialized_asset_path, read_asset_text
from .backup import backup_file
from .config import write_config
from .logging_utils import info, ok, warn
from .manifest import begin_transaction, write_manifest
from .models import EnvironmentInfo, ManifestTransaction, Paths, ResolvedConfig
from .shells import shell_fragment_path, shell_fragment_source, shell_hook, shell_rc_path

CORE_PACKAGES = {
    "dnf": ["zellij", "yazi", "eza", "bat", "starship", "zoxide", "fzf", "ripgrep", "btop", "fastfetch", "ollama"],
    "pacman": ["zellij", "yazi", "eza", "bat", "starship", "zoxide", "fzf", "ripgrep", "btop", "fastfetch", "ollama"],
    "apt": ["zellij", "yazi", "eza", "bat", "starship", "zoxide", "fzf", "ripgrep", "btop", "fastfetch", "ollama"],
    "zypper": ["zellij", "yazi", "eza", "bat", "starship", "zoxide", "fzf", "ripgrep", "btop", "fastfetch", "ollama"],
    "apk": ["zellij", "yazi", "eza", "bat", "starship", "zoxide", "fzf", "ripgrep", "btop", "fastfetch", "ollama"],
    "brew": ["zellij", "yazi", "eza", "bat", "starship", "zoxide", "fzf", "ripgrep", "btop", "fastfetch", "ollama"],
}

SURFACE_PACKAGES = {
    "dnf": ["ghostty", "jetbrains-mono-fonts-all", "mesa-dri-drivers", "mesa-utils"],
    "pacman": ["ghostty", "ttf-jetbrains-mono-nerd", "mesa-utils"],
    "apt": ["ghostty", "fonts-jetbrains-mono", "mesa-utils"],
    "zypper": ["ghostty", "jetbrains-mono-fonts", "Mesa-dri", "Mesa-demo-x"],
    "apk": ["ghostty", "font-jetbrains-mono", "mesa-demos"],
    "brew": ["ghostty", "font-jetbrains-mono-nerd-font", "mesa"],
}


def surface_support_error(env: EnvironmentInfo) -> str | None:
    if env.resolved_mode != "host":
        return "surface install requires host mode"
    if not env.gui:
        return "surface install requires a GUI session"
    return None


def _run(command: list[str], dry_run: bool) -> bool:
    if dry_run:
        print("[dry-run]", " ".join(command))
        return True
    try:
        result = subprocess.run(command, check=False)
    except FileNotFoundError as exc:
        warn(f"Skipping command because a binary is missing: {exc}")
        return False
    if result.returncode == 0:
        return True
    warn(f"Command exited with status {result.returncode}: {' '.join(command)}")
    return False


def _package_commands(package_manager: str, packages: list[str]) -> list[list[str]]:
    if package_manager == "dnf":
        return [["sudo", "dnf", "install", "-y", package] for package in packages]
    if package_manager == "pacman":
        return [["sudo", "pacman", "-S", "--needed", "--noconfirm", package] for package in packages]
    if package_manager == "apt":
        return [["sudo", "apt-get", "update"]] + [["sudo", "apt-get", "install", "-y", package] for package in packages]
    if package_manager == "zypper":
        return [["sudo", "zypper", "--non-interactive", "install", package] for package in packages]
    if package_manager == "apk":
        return [["sudo", "apk", "add", package] for package in packages]
    if package_manager == "brew":
        return [["brew", "install", package] for package in packages]
    return []


def _record_modified(manifest: ManifestTransaction, target: Path) -> None:
    target_str = str(target)
    if target_str not in manifest.files_modified:
        manifest.files_modified.append(target_str)


def _copy_file(paths: Paths, src: Path, dst: Path, manifest: ManifestTransaction) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        backup_file(paths, manifest, dst)
        shutil.copy2(src, dst)
        _record_modified(manifest, dst)
        return
    shutil.copy2(src, dst)
    manifest.files_created.append(str(dst))


def _copy_asset(paths: Paths, asset_parts: tuple[str, ...], dst: Path, manifest: ManifestTransaction) -> None:
    with materialized_asset_path(*asset_parts) as src:
        _copy_file(paths, src, dst, manifest)


def _write_text_file(paths: Paths, dst: Path, text: str, manifest: ManifestTransaction) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        backup_file(paths, manifest, dst)
        _record_modified(manifest, dst)
    else:
        manifest.files_created.append(str(dst))
    dst.write_text(text, encoding="utf-8")


def _write_config_file(paths: Paths, config: ResolvedConfig, manifest: ManifestTransaction) -> None:
    existing = paths.config_file.exists()
    if existing:
        backup_file(paths, manifest, paths.config_file)
    write_config(paths, config)
    if existing:
        _record_modified(manifest, paths.config_file)
    else:
        manifest.files_created.append(str(paths.config_file))


def _alias_override_snippet() -> str:
    return textwrap.dedent('''
if command -v eza >/dev/null 2>&1; then
  alias ls="eza --icons --git --group-directories-first"
  alias ll="eza -alF --icons --git --group-directories-first"
elif command -v exa >/dev/null 2>&1; then
  alias ls="exa --icons --git --group-directories-first"
  alias ll="exa -alF --icons --git --group-directories-first"
fi

if command -v bat >/dev/null 2>&1; then
  alias cat="bat --style=plain --paging=never"
elif command -v batcat >/dev/null 2>&1; then
  alias cat="batcat --style=plain --paging=never"
fi

if command -v z >/dev/null 2>&1; then
  alias cd="z"
fi
''').strip()


def _render_shell_fragment(config: ResolvedConfig) -> str:
    text = read_asset_text(*shell_fragment_source(config.shell))
    if config.features.get("alias_overrides"):
        text = text.rstrip() + "\n\n" + _alias_override_snippet() + "\n"
    return text


def _write_shell_fragment(paths: Paths, config: ResolvedConfig, manifest: ManifestTransaction) -> None:
    fragment_path = shell_fragment_path(paths, config.shell)
    _write_text_file(paths, fragment_path, _render_shell_fragment(config), manifest)

    rc_file = shell_rc_path(paths, config.shell)
    hook = shell_hook(config.shell)
    if rc_file.exists():
        current = rc_file.read_text(encoding="utf-8")
        if hook.strip() in current:
            return
        backup_file(paths, manifest, rc_file)
        _record_modified(manifest, rc_file)
        new_text = current
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        if new_text:
            new_text += "\n"
        rc_file.write_text(new_text + hook, encoding="utf-8")
        return

    rc_file.write_text(hook, encoding="utf-8")
    manifest.files_created.append(str(rc_file))


def _install_local_launchers(paths: Paths, manifest: ManifestTransaction) -> None:
    repo_bin = paths.root / "bin/zen"
    repo_src = paths.root / "src"
    python_bin = Path(sys.executable)
    shim = (
        "#!/usr/bin/env bash\n"
        f"if {shlex.quote(str(python_bin))} -c 'import zenith' >/dev/null 2>&1; then\n"
        f"  exec {shlex.quote(str(python_bin))} -m zenith.cli \"$@\"\n"
        "fi\n"
        f"if [ -f {shlex.quote(str(repo_bin))} ] && [ -d {shlex.quote(str(repo_src / 'zenith'))} ]; then\n"
        f"  export PYTHONPATH={shlex.quote(str(repo_src))}${{PYTHONPATH:+:$PYTHONPATH}}\n"
        f"  exec {shlex.quote(str(python_bin))} {shlex.quote(str(repo_bin))} \"$@\"\n"
        "fi\n"
        "echo 'Zenith is not installed for the current Python interpreter.' >&2\n"
        "exit 1\n"
    )
    for name in ("zen", "zenith"):
        launcher = paths.bin_home / name
        if launcher.exists():
            backup_file(paths, manifest, launcher)
            _record_modified(manifest, launcher)
        else:
            manifest.files_created.append(str(launcher))
        launcher.write_text(shim, encoding="utf-8")
        os.chmod(launcher, 0o755)


def _apply_config_paths(paths: Paths, config: ResolvedConfig) -> None:
    config.paths["install_root"] = str(paths.share_dir)
    config.paths["log_dir"] = str(paths.log_dir)


def _install_core_assets(paths: Paths, manifest: ManifestTransaction) -> None:
    _copy_asset(paths, ("configs", "starship", "starship.toml"), paths.home / ".config/starship.toml", manifest)
    _copy_asset(paths, ("configs", "zellij", "layout.kdl"), paths.home / ".config/zellij/layouts/zenith.kdl", manifest)
    _copy_asset(paths, ("configs", "zellij", "config.kdl"), paths.home / ".config/zellij/config.kdl", manifest)
    _copy_asset(paths, ("prompts", "nav.prompt"), paths.prompt_dir / "nav.prompt", manifest)
    _copy_asset(paths, ("prompts", "fix.prompt"), paths.prompt_dir / "fix.prompt", manifest)


def _install_surface_assets(paths: Paths, manifest: ManifestTransaction) -> None:
    ghostty_dir = paths.home / ".config/ghostty"
    shaders_dir = ghostty_dir / "shaders"
    ghostty_dir.mkdir(parents=True, exist_ok=True)
    shaders_dir.mkdir(parents=True, exist_ok=True)
    _copy_asset(paths, ("configs", "ghostty", "config"), ghostty_dir / "config", manifest)
    for shader_name, shader_path in iter_asset_files("configs", "ghostty", "shaders"):
        _copy_file(paths, shader_path, shaders_dir / shader_name, manifest)


def _confirm(message: str, assume_yes: bool, dry_run: bool) -> None:
    if assume_yes or dry_run:
        return
    answer = input(f"{message} [y/N] " ).strip().lower()
    if answer != "y":
        raise SystemExit("Install canceled")


def _install_packages(env: EnvironmentInfo, package_map: dict[str, list[str]], manifest: ManifestTransaction, dry_run: bool) -> None:
    packages = package_map.get(env.package_manager)
    if not packages:
        warn(f"Skipping package install for unsupported package manager: {env.package_manager}")
        return
    manifest.packages.extend(packages)
    failures = 0
    for command in _package_commands(env.package_manager, packages):
        if not _run(command, dry_run=dry_run):
            failures += 1
    if failures and not dry_run:
        warn(f"Package installation completed with {failures} warning(s); Zenith continued with local setup.")


def install_core(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, dry_run: bool, assume_yes: bool) -> None:
    manifest = begin_transaction(config.profile, env.resolved_mode, ["core"])
    config.features["core"] = True
    _apply_config_paths(paths, config)
    info(f"Preparing core install for profile={config.profile} mode={env.resolved_mode}")
    print("Plan:")
    print(f"  profile: {config.profile}")
    print(f"  mode: {env.resolved_mode}")
    print(f"  shell: {config.shell}")
    print(f"  package manager: {env.package_manager}")
    print(f"  config: {paths.config_file}")
    print(f"  shell fragment: {shell_fragment_path(paths, config.shell)}")
    _confirm("Apply Zenith core changes?", assume_yes, dry_run)

    _install_packages(env, CORE_PACKAGES, manifest, dry_run=dry_run)

    if dry_run:
        ok("Core dry-run complete")
        return

    _write_config_file(paths, config, manifest)
    _install_local_launchers(paths, manifest)
    _write_shell_fragment(paths, config, manifest)
    _install_core_assets(paths, manifest)
    write_manifest(paths, manifest)
    ok("Core installed")


def install_surface(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, dry_run: bool, assume_yes: bool) -> None:
    error = surface_support_error(env)
    if error:
        raise SystemExit(error)

    manifest = begin_transaction(config.profile, env.resolved_mode, ["surface"])
    config.features["surface"] = True
    config.features["orbit"] = True
    _apply_config_paths(paths, config)
    info(f"Preparing surface install for profile={config.profile} mode={env.resolved_mode}")
    _confirm("Apply Zenith surface changes?", assume_yes, dry_run)

    _install_packages(env, SURFACE_PACKAGES, manifest, dry_run=dry_run)

    if dry_run:
        ok("Surface dry-run complete")
        return

    _write_config_file(paths, config, manifest)
    _install_surface_assets(paths, manifest)
    write_manifest(paths, manifest)
    ok("Surface installed")
