from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from .assets import iter_asset_files, materialized_asset_path, read_asset_text
from .backup import backup_file
from .binaries import binary_available, resolve_binary, with_local_bin_path
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

BOOTSTRAP_PACKAGES = {
    'cargo': {
        'dnf': ['cargo', 'gcc', 'make', 'pkgconf-pkg-config'],
        'pacman': ['cargo', 'base-devel', 'pkgconf'],
        'apt': ['cargo', 'build-essential', 'pkg-config'],
        'zypper': ['cargo', 'gcc', 'make', 'pkg-config'],
        'apk': ['cargo', 'build-base', 'pkgconf'],
        'brew': ['rust'],
    },
    'curl': {
        'dnf': ['curl', 'tar'],
        'pacman': ['curl', 'tar'],
        'apt': ['curl', 'tar'],
        'zypper': ['curl', 'tar'],
        'apk': ['curl', 'tar'],
        'brew': ['curl'],
    },
}

CARGO_CRATES = {
    'zellij': ['zellij'],
    'starship': ['starship'],
    'yazi': ['yazi-fm', 'yazi-cli'],
}

TOOL_BINARIES = {
    'zellij': ('zellij',),
    'yazi': ('yazi',),
    'starship': ('starship',),
    'ollama': ('ollama',),
}

OLLAMA_ARCHIVE_NAMES = {
    'x86_64': 'amd64',
    'amd64': 'amd64',
    'aarch64': 'arm64',
    'arm64': 'arm64',
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
        result = subprocess.run(command, check=False, env=with_local_bin_path())
    except FileNotFoundError as exc:
        warn(f"Skipping command because a binary is missing: {exc}")
        return False
    if result.returncode == 0:
        return True
    warn(f"Command exited with status {result.returncode}: {' '.join(command)}")
    return False


def _run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, env=with_local_bin_path())


def _is_root() -> bool:
    return hasattr(os, 'geteuid') and os.geteuid() == 0


def _privilege_prefix(package_manager: str) -> list[str]:
    if package_manager == 'brew' or _is_root():
        return []
    return ['sudo']


def _package_commands(package_manager: str, packages: list[str]) -> list[list[str]]:
    prefix = _privilege_prefix(package_manager)
    if package_manager == "dnf":
        return [prefix + ["dnf", "install", "-y", package] for package in packages]
    if package_manager == "pacman":
        return [prefix + ["pacman", "-S", "--needed", "--noconfirm", package] for package in packages]
    if package_manager == "apt":
        return [prefix + ["apt-get", "update"]] + [prefix + ["apt-get", "install", "-y", package] for package in packages]
    if package_manager == "zypper":
        return [prefix + ["zypper", "--non-interactive", "install", package] for package in packages]
    if package_manager == "apk":
        return [prefix + ["apk", "add", package] for package in packages]
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
    _record_packages(manifest, packages)
    failures = 0
    for command in _package_commands(env.package_manager, packages):
        if not _run(command, dry_run=dry_run):
            failures += 1
    if failures and not dry_run:
        warn(f"Package installation completed with {failures} warning(s); Zenith continued with local setup.")


def _record_packages(manifest: ManifestTransaction, packages: list[str]) -> None:
    for package in packages:
        if package not in manifest.packages:
            manifest.packages.append(package)


def _install_specific_packages(env: EnvironmentInfo, packages: list[str], manifest: ManifestTransaction, dry_run: bool) -> bool:
    commands = _package_commands(env.package_manager, packages)
    if not commands:
        return False
    failures = 0
    for command in commands:
        if not _run(command, dry_run=dry_run):
            failures += 1
    if failures:
        return False
    _record_packages(manifest, packages)
    return True


def _ensure_helper_packages(env: EnvironmentInfo, helper: str, manifest: ManifestTransaction, dry_run: bool) -> bool:
    if helper == 'cargo' and binary_available('cargo'):
        return True
    if helper == 'curl' and binary_available('curl'):
        return True
    packages = BOOTSTRAP_PACKAGES.get(helper, {}).get(env.package_manager)
    if not packages:
        warn(f'No fallback helper package mapping for {helper} on {env.package_manager}')
        return False
    return _install_specific_packages(env, packages, manifest, dry_run)


def _install_with_cargo(paths: Paths, env: EnvironmentInfo, tool: str, manifest: ManifestTransaction, dry_run: bool) -> bool:
    crates = CARGO_CRATES[tool]
    binaries = TOOL_BINARIES[tool]
    if binary_available(*binaries):
        return True
    if not _ensure_helper_packages(env, 'cargo', manifest, dry_run):
        warn(f'Unable to install cargo toolchain for {tool}')
        return False
    cargo = resolve_binary('cargo') or 'cargo'
    command = [cargo, 'install', '--locked', '--root', str(paths.home / '.local')] + crates
    if not _run(command, dry_run=dry_run):
        return False
    if not dry_run and not binary_available(*binaries):
        warn(f'{tool} fallback install completed but the expected binary was not found')
        return False
    _record_packages(manifest, [f'cargo:{tool}'])
    return True


def _ollama_download_url() -> str | None:
    arch = OLLAMA_ARCHIVE_NAMES.get(platform.machine().lower())
    if not arch:
        return None
    return f'https://ollama.com/download/ollama-linux-{arch}.tgz'


def _install_ollama_fallback(paths: Paths, env: EnvironmentInfo, manifest: ManifestTransaction, dry_run: bool) -> bool:
    if binary_available('ollama'):
        return True
    url = _ollama_download_url()
    if not url:
        warn(f'No ollama download defined for architecture {platform.machine()}')
        return False
    if not _ensure_helper_packages(env, 'curl', manifest, dry_run):
        warn('Unable to install curl/tar needed for ollama bootstrap')
        return False
    archive = paths.cache_dir / f'ollama-{platform.machine().lower()}.tgz'
    stage_dir = paths.cache_dir / 'ollama-stage'
    curl = resolve_binary('curl') or 'curl'
    if not _run([curl, '-fsSL', url, '-o', str(archive)], dry_run=dry_run):
        return False
    if dry_run:
        print('[dry-run]', 'tar', '-xzf', str(archive), '-C', str(stage_dir))
        print('[dry-run]', f'copy extracted ollama binary to {paths.bin_home / "ollama"}')
        return True
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    if not _run(['tar', '-xzf', str(archive), '-C', str(stage_dir)], dry_run=False):
        return False
    matches = [candidate for candidate in stage_dir.rglob('ollama') if candidate.is_file()]
    if not matches:
        warn('Unable to find an ollama binary in the downloaded archive')
        return False
    destination = paths.bin_home / 'ollama'
    _copy_file(paths, matches[0], destination, manifest)
    os.chmod(destination, 0o755)
    _record_packages(manifest, ['bootstrap:ollama'])
    return True


def _ollama_ready(ollama: str) -> bool:
    result = _run_capture([ollama, 'list'])
    return result.returncode == 0


def _record_service(manifest: ManifestTransaction, service: str) -> None:
    if service not in manifest.services:
        manifest.services.append(service)


def _start_ollama_service(paths: Paths, manifest: ManifestTransaction, dry_run: bool) -> bool:
    ollama = resolve_binary('ollama')
    if not ollama:
        return False
    if _ollama_ready(ollama):
        return True
    log_file = paths.log_dir / 'ollama.log'
    if dry_run:
        print('[dry-run]', f'{ollama} serve >> {log_file} 2>&1 &')
        return True
    with log_file.open('ab') as handle:
        process = subprocess.Popen([ollama, 'serve'], stdout=handle, stderr=handle, env=with_local_bin_path(), start_new_session=True)
    deadline = time.time() + 20
    while time.time() < deadline:
        if _ollama_ready(ollama):
            _record_service(manifest, 'ollama serve')
            return True
        if process.poll() is not None:
            break
        time.sleep(1)
    warn('ollama serve did not become ready')
    return False


def _has_ollama_model(ollama: str, model: str) -> bool:
    result = _run_capture([ollama, 'list'])
    return result.returncode == 0 and model in result.stdout


def _should_bootstrap_model(config: ResolvedConfig, env: EnvironmentInfo) -> bool:
    if 'bootstrap_model' in config.ai:
        return bool(config.ai.get('bootstrap_model'))
    return env.resolved_mode == 'container'


def _ensure_ollama_model(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, manifest: ManifestTransaction, dry_run: bool) -> bool:
    if not _should_bootstrap_model(config, env):
        return True
    ollama = resolve_binary('ollama')
    if not ollama:
        return False
    model = str(config.ai.get('model', 'llama3.2:3b'))
    if not _start_ollama_service(paths, manifest, dry_run):
        return False
    if dry_run:
        print('[dry-run]', ollama, 'pull', model)
        return True
    if _has_ollama_model(ollama, model):
        return True
    if not _run([ollama, 'pull', model], dry_run=False):
        return False
    _record_packages(manifest, [f'ollama-model:{model}'])
    return True


def _install_core_fallbacks(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, manifest: ManifestTransaction, dry_run: bool) -> None:
    if not binary_available(*TOOL_BINARIES['zellij']):
        _install_with_cargo(paths, env, 'zellij', manifest, dry_run)
    if not binary_available(*TOOL_BINARIES['yazi']):
        _install_with_cargo(paths, env, 'yazi', manifest, dry_run)
    if not binary_available(*TOOL_BINARIES['starship']):
        _install_with_cargo(paths, env, 'starship', manifest, dry_run)
    if not binary_available(*TOOL_BINARIES['ollama']):
        _install_ollama_fallback(paths, env, manifest, dry_run)
    if binary_available(*TOOL_BINARIES['ollama']):
        _ensure_ollama_model(paths, config, env, manifest, dry_run)

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
    _install_core_fallbacks(paths, config, env, manifest, dry_run=dry_run)

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
