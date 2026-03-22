from __future__ import annotations

import os
import platform
import re
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
from .config import normalize_terminal, write_config
from .logging_utils import info, note, ok, warn
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
    'archive': {
        'dnf': ['curl', 'tar', 'unzip', 'zstd'],
        'pacman': ['curl', 'tar', 'unzip', 'zstd'],
        'apt': ['curl', 'tar', 'unzip', 'zstd'],
        'zypper': ['curl', 'tar', 'unzip', 'zstd'],
        'apk': ['curl', 'tar', 'unzip', 'zstd'],
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

DOWNLOADABLE_TOOLS = {
    'zellij': {
        'x86_64': {
            'url': 'https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz',
            'archive_type': 'tar.gz',
            'binaries': ('zellij',),
        },
        'amd64': {
            'url': 'https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz',
            'archive_type': 'tar.gz',
            'binaries': ('zellij',),
        },
        'aarch64': {
            'url': 'https://github.com/zellij-org/zellij/releases/latest/download/zellij-aarch64-unknown-linux-musl.tar.gz',
            'archive_type': 'tar.gz',
            'binaries': ('zellij',),
        },
        'arm64': {
            'url': 'https://github.com/zellij-org/zellij/releases/latest/download/zellij-aarch64-unknown-linux-musl.tar.gz',
            'archive_type': 'tar.gz',
            'binaries': ('zellij',),
        },
    },
    'yazi': {
        'x86_64': {
            'url': 'https://github.com/sxyazi/yazi/releases/latest/download/yazi-x86_64-unknown-linux-musl.zip',
            'archive_type': 'zip',
            'binaries': ('yazi', 'ya'),
        },
        'amd64': {
            'url': 'https://github.com/sxyazi/yazi/releases/latest/download/yazi-x86_64-unknown-linux-musl.zip',
            'archive_type': 'zip',
            'binaries': ('yazi', 'ya'),
        },
        'aarch64': {
            'url': 'https://github.com/sxyazi/yazi/releases/latest/download/yazi-aarch64-unknown-linux-musl.zip',
            'archive_type': 'zip',
            'binaries': ('yazi', 'ya'),
        },
        'arm64': {
            'url': 'https://github.com/sxyazi/yazi/releases/latest/download/yazi-aarch64-unknown-linux-musl.zip',
            'archive_type': 'zip',
            'binaries': ('yazi', 'ya'),
        },
    },
    'ollama': {
        'x86_64': {
            'url': 'https://ollama.com/download/ollama-linux-amd64.tar.zst',
            'archive_type': 'tar.zst',
            'binaries': ('ollama',),
        },
        'amd64': {
            'url': 'https://ollama.com/download/ollama-linux-amd64.tar.zst',
            'archive_type': 'tar.zst',
            'binaries': ('ollama',),
        },
        'aarch64': {
            'url': 'https://ollama.com/download/ollama-linux-arm64.tar.zst',
            'archive_type': 'tar.zst',
            'binaries': ('ollama',),
        },
        'arm64': {
            'url': 'https://ollama.com/download/ollama-linux-arm64.tar.zst',
            'archive_type': 'tar.zst',
            'binaries': ('ollama',),
        },
    },
}

STRICT_CORE_TOOLS = ('zellij', 'yazi', 'starship', 'ollama')
BUILTIN_SURFACE_TERMINALS = {'ghostty', 'kitty'}
GHOSTTY_DOWNLOAD_PAGE = 'https://ghostty.org/download'
GHOSTTY_RELEASES_LATEST = 'https://github.com/ghostty-org/ghostty/releases/latest'
GHOSTTY_KNOWN_VERSION = '1.3.1'
GHOSTTY_TARBALL_URL = 'https://release.files.ghostty.org/{version}/ghostty-{version}.tar.gz'
KITTY_INSTALLER_URL = 'https://sw.kovidgoyal.net/kitty/installer.sh'
KITTY_RELEASES_LATEST = 'https://github.com/kovidgoyal/kitty/releases/latest'
KITTY_KNOWN_VERSION = '0.46.0'
ZIG_DOWNLOAD_URL = 'https://ziglang.org/download/{version}/zig-{arch}-{platform}-{version}.tar.xz'
ZIG_ARCH_MAP = {
    'x86_64': 'x86_64',
    'amd64': 'x86_64',
    'aarch64': 'aarch64',
    'arm64': 'aarch64',
    'armv7l': 'arm',
    'arm': 'arm',
}
GHOSTTY_PACKAGE_HINTS = {
    'dnf': {
        'gtk4': 'gtk4-devel',
        'libadwaita-1': 'libadwaita-devel',
        'gtk4-layer-shell-0': 'gtk4-layer-shell-devel',
        'gettext': 'gettext',
        'pkg-config': 'pkgconf-pkg-config',
    },
    'apt': {
        'gtk4': 'libgtk-4-dev',
        'libadwaita-1': 'libadwaita-1-dev',
        'gtk4-layer-shell-0': 'libgtk4-layer-shell-dev',
        'gettext': 'gettext',
        'pkg-config': 'pkg-config',
    },
    'pacman': {
        'gtk4': 'gtk4',
        'libadwaita-1': 'libadwaita',
        'gtk4-layer-shell-0': 'gtk4-layer-shell',
        'gettext': 'gettext',
        'pkg-config': 'pkgconf',
    },
    'zypper': {
        'gtk4': 'gtk4-devel',
        'libadwaita-1': 'libadwaita-devel',
        'gtk4-layer-shell-0': 'gtk4-layer-shell-devel',
        'gettext': 'gettext',
        'pkg-config': 'pkgconf',
    },
    'apk': {
        'gtk4': 'gtk4.0-dev',
        'libadwaita-1': 'libadwaita-dev',
        'gtk4-layer-shell-0': 'gtk4-layer-shell-dev',
        'gettext': 'gettext',
        'pkg-config': 'pkgconf',
    },
}


def surface_support_error(env: EnvironmentInfo) -> str | None:
    if env.resolved_mode != "host":
        return "surface install requires host mode"
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


def _run_capture_silent(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False, env=with_local_bin_path())
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(command, 127, '', str(exc))


def _summarize_process_error(result: subprocess.CompletedProcess[str]) -> str:
    parts = [part.strip() for part in (result.stderr, result.stdout) if part and part.strip()]
    if not parts:
        return f'exit status {result.returncode}'
    first_line = parts[0].splitlines()[0].strip()
    return first_line if first_line else f'exit status {result.returncode}'


def _package_name_from_command(command: list[str]) -> str:
    if not command:
        return 'package'
    if command[0] == 'brew' and len(command) >= 3:
        return command[-1]
    if 'install' in command or 'add' in command:
        return command[-1]
    return command[-1]


def _is_root() -> bool:
    return hasattr(os, 'geteuid') and os.geteuid() == 0


def _privilege_prefix(package_manager: str) -> list[str]:
    return []


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


def _install_ghostty_surface_assets(paths: Paths, manifest: ManifestTransaction) -> None:
    ghostty_dir = paths.home / ".config/ghostty"
    shaders_dir = ghostty_dir / "shaders"
    ghostty_dir.mkdir(parents=True, exist_ok=True)
    shaders_dir.mkdir(parents=True, exist_ok=True)
    _copy_asset(paths, ("configs", "ghostty", "config"), ghostty_dir / "config", manifest)
    for shader_name, shader_path in iter_asset_files("configs", "ghostty", "shaders"):
        _copy_file(paths, shader_path, shaders_dir / shader_name, manifest)


def _install_kitty_surface_assets(paths: Paths, manifest: ManifestTransaction) -> None:
    kitty_dir = paths.home / ".config/kitty"
    kitty_dir.mkdir(parents=True, exist_ok=True)
    _copy_asset(paths, ("configs", "kitty", "kitty.conf"), kitty_dir / "kitty.conf", manifest)


def _install_surface_assets(paths: Paths, manifest: ManifestTransaction, terminal: str) -> None:
    if terminal == 'ghostty':
        _install_ghostty_surface_assets(paths, manifest)
        return
    if terminal == 'kitty':
        _install_kitty_surface_assets(paths, manifest)
        return


def _terminal_bootstrap_supported(terminal: str) -> bool:
    return terminal in {'ghostty', 'kitty'}


def _zig_download_metadata(version: str) -> dict[str, str] | None:
    if not sys.platform.startswith('linux'):
        return None
    arch = ZIG_ARCH_MAP.get(platform.machine().lower())
    if not arch:
        return None
    return {
        'url': ZIG_DOWNLOAD_URL.format(version=version, arch=arch, platform='linux'),
        'archive_name': f'zig-{arch}-linux-{version}.tar.xz',
    }


def _kitty_version(paths: Paths, config: ResolvedConfig | None = None) -> str | None:
    override = os.environ.get('ZENITH_KITTY_VERSION', '').strip()
    if not override and config is not None:
        override = str(config.updates.get('kitty_version', '')).strip()
    if override:
        return override
    curl = resolve_binary('curl') or 'curl'
    latest = _run_capture_silent([
        curl,
        '-A', 'Zenith/0.1 (+https://sw.kovidgoyal.net/kitty)',
        '--retry', '3',
        '--connect-timeout', '15',
        '-fsSILo', '/dev/null',
        '-w', '%{url_effective}',
        KITTY_RELEASES_LATEST,
    ])
    if latest.returncode == 0:
        final_url = (latest.stdout or '').strip()
        match = re.search(r'/releases/(?:tag/)?v?([0-9]+\.[0-9]+\.[0-9]+)', final_url)
        if match:
            return match.group(1)
    return KITTY_KNOWN_VERSION


def _install_kitty_user_space(paths: Paths, config: ResolvedConfig, manifest: ManifestTransaction, dry_run: bool, force_upgrade: bool = False) -> bool:
    if binary_available('kitty') and not force_upgrade:
        note('Kitty is already available in PATH')
        return True
    if binary_available('kitty') and force_upgrade:
        note('Zenith will refresh the Kitty install in user space')
    if not sys.platform.startswith('linux'):
        warn('Zenith currently only supports automatic Kitty bootstrap on Linux')
        return False

    version = _kitty_version(paths, config)
    if not version:
        warn('Unable to determine the current Kitty release version automatically from the official release feed')
        return False
    if version == KITTY_KNOWN_VERSION:
        note(f'Using bundled supported Kitty release {version} because live release discovery is unavailable')
    else:
        note(f'Using Kitty {version} for the user-space surface install')

    curl = resolve_binary('curl') or 'curl'
    sh_bin = resolve_binary('sh') or '/bin/sh'
    installer_script = paths.cache_dir / 'kitty-installer.sh'
    app_dir = paths.home / '.local/kitty.app'
    kitty_binary = app_dir / 'bin/kitty'
    kitten_binary = app_dir / 'bin/kitten'
    kitty_launcher = paths.bin_home / 'kitty'
    kitten_launcher = paths.bin_home / 'kitten'

    if dry_run:
        print('[dry-run]', ' '.join([curl, '-fsSL', KITTY_INSTALLER_URL, '-o', str(installer_script)]))
        print('[dry-run]', ' '.join([sh_bin, str(installer_script), 'launch=n', f'installer=version-{version}']))
        print('[dry-run]', f'install Kitty launchers into {paths.bin_home}')
        return True

    result = _run_capture_silent([curl, '-fsSL', KITTY_INSTALLER_URL, '-o', str(installer_script)])
    if result.returncode != 0:
        warn(f'Unable to download the official Kitty installer: {_summarize_process_error(result)}')
        return False

    install = _run_capture_silent([sh_bin, str(installer_script), 'launch=n', f'installer=version-{version}'])
    if install.returncode != 0:
        warn(f'Kitty installer failed: {_summarize_process_error(install)}')
        return False

    if not kitty_binary.exists() or not kitten_binary.exists():
        warn(f'Kitty installer completed but expected binaries were not found under {app_dir}')
        return False

    for launcher, target in ((kitty_launcher, kitty_binary), (kitten_launcher, kitten_binary)):
        script = '#!/usr/bin/env bash\nexec ' + shlex.quote(str(target)) + ' "$@"\n'
        if launcher.exists() or launcher.is_symlink():
            backup_file(paths, manifest, launcher)
            _record_modified(manifest, launcher)
        else:
            manifest.files_created.append(str(launcher))
        launcher.write_text(script, encoding='utf-8')
        os.chmod(launcher, 0o755)

    note(f'Installed Kitty into {app_dir}')
    _record_packages(manifest, [f'bootstrap:kitty:{version}'])
    return True


def _ghostty_package_hint(env: EnvironmentInfo, key: str) -> str | None:
    hints = GHOSTTY_PACKAGE_HINTS.get(env.package_manager, {})
    return hints.get(key)


def _ghostty_missing_packages_message(env: EnvironmentInfo, missing_libs: list[str], missing_tools: list[str]) -> str | None:
    package_names: list[str] = []
    for item in missing_libs:
        hint = _ghostty_package_hint(env, item)
        if hint and hint not in package_names:
            package_names.append(hint)
    if 'gettext' in missing_tools:
        hint = _ghostty_package_hint(env, 'gettext')
        if hint and hint not in package_names:
            package_names.append(hint)
    if 'pkg-config or pkgconf' in missing_tools:
        hint = _ghostty_package_hint(env, 'pkg-config')
        if hint and hint not in package_names:
            package_names.append(hint)
    if not package_names:
        return None
    if env.package_manager == 'unknown':
        return 'Host package hints are unavailable because Zenith could not identify the host package manager from this environment.'
    return f'Host packages still needed for Ghostty on {env.package_manager}: ' + ', '.join(package_names)


def _install_zig_user_space(paths: Paths, version: str, manifest: ManifestTransaction, dry_run: bool) -> bool:
    existing = resolve_binary('zig')
    if existing:
        current = _run_capture_silent([existing, 'version'])
        if current.returncode == 0 and current.stdout.strip() == version:
            note(f'Zig {version} is already available in PATH')
            return True

    metadata = _zig_download_metadata(version)
    if not metadata:
        warn(f'Zenith does not have a Zig bootstrap for architecture {platform.machine()} on this platform')
        return False

    if not resolve_binary('curl') or not resolve_binary('tar'):
        warn('Zenith needs curl and tar on the host to bootstrap Zig in user space')
        return False

    url = metadata['url']
    archive = paths.cache_dir / metadata['archive_name']
    stage_dir = paths.cache_dir / f'zig-stage-{version}'
    install_root = paths.home / '.local/opt/zig'
    curl = resolve_binary('curl') or 'curl'
    tar = resolve_binary('tar') or 'tar'

    if dry_run:
        print('[dry-run]', ' '.join([curl, '-fsSL', url, '-o', str(archive)]))
        print('[dry-run]', ' '.join([tar, '-xf', str(archive), '-C', str(stage_dir)]))
        print('[dry-run]', f'install Zig {version} under {install_root}')
        return True

    result = _run_capture_silent([curl, '-fsSL', url, '-o', str(archive)])
    if result.returncode != 0:
        warn(f'Unable to download Zig {version}: {_summarize_process_error(result)}')
        return False

    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    extract = _run_capture_silent([tar, '-xf', str(archive), '-C', str(stage_dir)])
    if extract.returncode != 0:
        warn(f'Unable to extract Zig {version}: {_summarize_process_error(extract)}')
        return False

    source_dirs = [candidate for candidate in stage_dir.iterdir() if candidate.is_dir()]
    if not source_dirs:
        warn(f'Unable to locate the extracted Zig {version} directory')
        return False

    install_root.mkdir(parents=True, exist_ok=True)
    destination = install_root / source_dirs[0].name
    if destination.exists():
        shutil.rmtree(destination, ignore_errors=True)
    shutil.move(str(source_dirs[0]), str(destination))

    zig_binary = destination / 'zig'
    if not zig_binary.exists():
        warn(f'Zig {version} download did not contain the expected zig binary')
        return False
    os.chmod(zig_binary, 0o755)

    launcher = paths.bin_home / 'zig'
    script = '#!/usr/bin/env bash\nexec ' + shlex.quote(str(zig_binary)) + ' "$@"\n'
    if launcher.exists():
        backup_file(paths, manifest, launcher)
        _record_modified(manifest, launcher)
    else:
        manifest.files_created.append(str(launcher))
    launcher.write_text(script, encoding='utf-8')
    os.chmod(launcher, 0o755)

    note(f'Bootstrapped Zig {version} into {paths.home / ".local"}')
    _record_packages(manifest, [f'bootstrap:zig:{version}'])
    return True


def _ghostty_expected_zig_version(version: str) -> str | None:
    if version.startswith('1.3.'):
        return '0.15.2'
    if version.startswith('1.2.'):
        return '0.14.1'
    if version.startswith('1.1.') or version.startswith('1.0.'):
        return '0.13.0'
    return None


def _ghostty_pkg_config() -> str | None:
    return resolve_binary('pkg-config', 'pkgconf')


def _pkg_config_has(package: str, pkg_config: str) -> bool:
    result = _run_capture_silent([pkg_config, '--exists', package])
    return result.returncode == 0


def _ghostty_version(paths: Paths, config: ResolvedConfig | None = None) -> str | None:
    override = os.environ.get('ZENITH_GHOSTTY_VERSION', '').strip()
    if not override and config is not None:
        override = str(config.updates.get('ghostty_version', '')).strip()
    if override:
        return override
    curl = resolve_binary('curl') or 'curl'

    fetch = _run_capture_silent([
        curl,
        '-A', 'Zenith/0.1 (+https://ghostty.org)',
        '--retry', '3',
        '--connect-timeout', '15',
        '-fsSL',
        GHOSTTY_DOWNLOAD_PAGE,
    ])
    if fetch.returncode == 0:
        content = (fetch.stdout or '') + '\n' + (fetch.stderr or '')
        for pattern in (
            r'Version\s+([0-9]+\.[0-9]+\.[0-9]+)',
            r'ghostty-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz',
            r'/([0-9]+\.[0-9]+\.[0-9]+)/ghostty-[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz',
        ):
            match = re.search(pattern, content)
            if match:
                return match.group(1)

    latest = _run_capture_silent([
        curl,
        '-A', 'Zenith/0.1 (+https://ghostty.org)',
        '--retry', '3',
        '--connect-timeout', '15',
        '-fsSILo', '/dev/null',
        '-w', '%{url_effective}',
        GHOSTTY_RELEASES_LATEST,
    ])
    if latest.returncode == 0:
        final_url = (latest.stdout or '').strip()
        match = re.search(r'/releases/(?:tag/)?v?([0-9]+\.[0-9]+\.[0-9]+)', final_url)
        if match:
            return match.group(1)

    return GHOSTTY_KNOWN_VERSION


def _ghostty_prerequisites(paths: Paths, *, check_zig: bool = True) -> tuple[bool, list[str], list[str]]:
    missing_tools: list[str] = []
    missing_libs: list[str] = []

    if check_zig:
        zig = resolve_binary('zig')
        if not zig:
            missing_tools.append('zig')
    pkg_config = _ghostty_pkg_config()
    if not pkg_config:
        missing_tools.append('pkg-config or pkgconf')
    gettext = resolve_binary('gettext', 'msgfmt')
    if not gettext:
        missing_tools.append('gettext')
    curl = resolve_binary('curl')
    if not curl:
        missing_tools.append('curl')
    tar = resolve_binary('tar')
    if not tar:
        missing_tools.append('tar')

    if pkg_config:
        if not _pkg_config_has('gtk4', pkg_config):
            missing_libs.append('gtk4')
        if not _pkg_config_has('libadwaita-1', pkg_config):
            missing_libs.append('libadwaita-1')

    return (not missing_tools and not missing_libs, missing_tools, missing_libs)


def _ghostty_build_flags(pkg_config: str | None) -> list[str]:
    flags = ['-Doptimize=ReleaseFast']
    if pkg_config and not _pkg_config_has('gtk4-layer-shell-0', pkg_config):
        flags.append('-fno-sys=gtk4-layer-shell')
    return flags


def _install_ghostty_user_space(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, manifest: ManifestTransaction, dry_run: bool, force_upgrade: bool = False) -> bool:
    if binary_available('ghostty') and not force_upgrade:
        note('Ghostty is already available in PATH')
        return True
    if binary_available('ghostty') and force_upgrade:
        note('Zenith will refresh the Ghostty install in user space')
    if not sys.platform.startswith('linux'):
        warn('Zenith currently only supports automatic Ghostty bootstrap on Linux')
        return False

    version = _ghostty_version(paths, config)
    if not version:
        warn('Unable to determine the current Ghostty release version automatically from ghostty.org/download or GitHub releases')
        note('Zenith only needs ZENITH_GHOSTTY_VERSION=x.y.z as a last-resort override when both automatic release lookups are unavailable')
        return False

    if version == GHOSTTY_KNOWN_VERSION:
        note(f'Using bundled supported Ghostty release {version} because live release discovery is unavailable')
    else:
        note(f'Using Ghostty {version} for the user-space surface install')
    expected_zig = _ghostty_expected_zig_version(version)
    if expected_zig:
        if not _install_zig_user_space(paths, expected_zig, manifest, dry_run):
            warn(f'Ghostty {version} needs Zig {expected_zig}, and Zenith could not make that Zig version available in user space')
            return False

    ok_prereqs, missing_tools, missing_libs = _ghostty_prerequisites(paths, check_zig=not (expected_zig and dry_run))
    if not ok_prereqs:
        if missing_tools:
            warn('Ghostty user-space install is blocked by missing tools: ' + ', '.join(missing_tools))
        if missing_libs:
            warn('Ghostty user-space install is blocked by missing host development libraries: ' + ', '.join(missing_libs))
        package_hint = _ghostty_missing_packages_message(env, missing_libs, missing_tools)
        if package_hint:
            note(package_hint)
        note('Official Ghostty docs require Zig plus GTK4, libadwaita, pkg-config/pkgconf, and gettext for Linux source builds; Zenith can disable gtk4-layer-shell when that package is unavailable')
        return False

    zig = resolve_binary('zig') or 'zig'
    zig_version = _run_capture_silent([zig, 'version'])
    detected_zig = zig_version.stdout.strip() if zig_version.returncode == 0 else ''
    if expected_zig and detected_zig and detected_zig != expected_zig:
        warn(f'Ghostty {version} expects Zig {expected_zig}, but found Zig {detected_zig}')
        return False

    url = GHOSTTY_TARBALL_URL.format(version=version)
    archive = paths.cache_dir / f'ghostty-{version}.tar.gz'
    source_root = paths.cache_dir / f'ghostty-{version}'
    prefix = paths.home / '.local'
    curl = resolve_binary('curl') or 'curl'
    tar = resolve_binary('tar') or 'tar'
    pkg_config = _ghostty_pkg_config()
    build_flags = _ghostty_build_flags(pkg_config)

    if dry_run:
        print('[dry-run]', ' '.join([curl, '-fsSL', url, '-o', str(archive)]))
        print('[dry-run]', ' '.join([tar, '-xf', str(archive), '-C', str(paths.cache_dir)]))
        print('[dry-run]', ' '.join([zig, 'build', '-p', str(prefix)] + build_flags))
        return True

    result = _run_capture_silent([curl, '-fsSL', url, '-o', str(archive)])
    if result.returncode != 0:
        warn(f'Unable to download Ghostty source tarball: {_summarize_process_error(result)}')
        return False

    if source_root.exists():
        shutil.rmtree(source_root, ignore_errors=True)
    source_root.mkdir(parents=True, exist_ok=True)
    extract = _run_capture_silent([tar, '-xf', str(archive), '-C', str(source_root)])
    if extract.returncode != 0:
        warn(f'Unable to extract Ghostty source tarball: {_summarize_process_error(extract)}')
        return False

    source_dirs = [candidate for candidate in source_root.iterdir() if candidate.is_dir()]
    build_dir = source_dirs[0] if source_dirs else source_root
    build = subprocess.run(
        [zig, 'build', '-p', str(prefix)] + build_flags,
        cwd=build_dir,
        capture_output=True,
        text=True,
        check=False,
        env=with_local_bin_path(),
    )
    if build.returncode != 0:
        warn(f'Ghostty build failed: {_summarize_process_error(build)}')
        return False

    if not binary_available('ghostty'):
        warn('Ghostty build completed but the ghostty binary was not found in PATH')
        return False

    note(f'Bootstrapped Ghostty into {paths.home / ".local"}')
    _record_packages(manifest, [f'bootstrap:ghostty:{version}'])
    return True


def _ensure_surface_terminal(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, terminal: str, manifest: ManifestTransaction, dry_run: bool, force_upgrade: bool = False) -> bool:
    if binary_available(terminal) and not force_upgrade:
        note(f'{terminal} is already available in PATH')
        return True
    if terminal == 'ghostty':
        return _install_ghostty_user_space(paths, config, env, manifest, dry_run, force_upgrade=force_upgrade)
    if terminal == 'kitty':
        return _install_kitty_user_space(paths, config, manifest, dry_run, force_upgrade=force_upgrade)
    warn(f'Zenith does not yet know how to install {terminal} in user space')
    note(f'Install {terminal} yourself first, then rerun Zenith with --terminal {terminal}')
    return False


def _confirm(message: str, assume_yes: bool, dry_run: bool) -> None:
    if assume_yes or dry_run:
        return
    answer = input(f"{message} [y/N] " ).strip().lower()
    if answer != "y":
        raise SystemExit("Install canceled")


def _install_packages(env: EnvironmentInfo, package_map: dict[str, list[str]], manifest: ManifestTransaction, dry_run: bool) -> None:
    if env.resolved_mode == 'host':
        note('Skipping host package-manager installs; Zenith is staying in user space on the host')
        return
    packages = package_map.get(env.package_manager)
    if not packages:
        warn(f"Skipping package install for unsupported package manager: {env.package_manager}")
        return
    _record_packages(manifest, packages)
    failures = 0
    for command in _package_commands(env.package_manager, packages):
        package = _package_name_from_command(command)
        if dry_run:
            print('[dry-run]', ' '.join(command))
            continue
        result = _run_capture_silent(command)
        if result.returncode == 0:
            note(f"Installed {package} via {env.package_manager}")
            continue
        failures += 1
        note(f"{package} is not available via {env.package_manager}; Zenith will use a fallback when possible")
    if failures and not dry_run:
        note(f"Native package install missed {failures} tool(s); continuing with Zenith-managed setup")


def _record_packages(manifest: ManifestTransaction, packages: list[str]) -> None:
    for package in packages:
        if package not in manifest.packages:
            manifest.packages.append(package)


def _install_specific_packages(env: EnvironmentInfo, packages: list[str], manifest: ManifestTransaction, dry_run: bool) -> bool:
    commands = _package_commands(env.package_manager, packages)
    if not commands:
        return False
    failures: list[str] = []
    for command in commands:
        package = _package_name_from_command(command)
        if dry_run:
            print('[dry-run]', ' '.join(command))
            continue
        result = _run_capture_silent(command)
        if result.returncode == 0:
            note(f"Installed helper package {package} via {env.package_manager}")
            continue
        failures.append(f"{package} ({_summarize_process_error(result)})")
    if failures:
        warn(f"Unable to install helper packages via {env.package_manager}: {', '.join(failures)}")
        return False
    _record_packages(manifest, packages)
    return True


def _ensure_helper_packages(env: EnvironmentInfo, helper: str, manifest: ManifestTransaction, dry_run: bool) -> bool:
    if helper == 'cargo' and binary_available('cargo'):
        return True
    if helper == 'archive' and binary_available('curl') and binary_available('tar') and binary_available('unzip') and binary_available('zstd'):
        return True
    if env.resolved_mode == 'host':
        note(f'Zenith will not install host helper packages for {helper}; provide them yourself if you want that host-side bootstrap path')
        return False
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
    note(f"Bootstrapping {tool} with cargo")
    if not _ensure_helper_packages(env, 'cargo', manifest, dry_run):
        warn(f'Unable to install cargo toolchain for {tool}')
        return False
    cargo = resolve_binary('cargo') or 'cargo'
    command = [cargo, 'install', '--locked', '--root', str(paths.home / '.local')] + crates
    if dry_run:
        print('[dry-run]', ' '.join(command))
        return True
    result = _run_capture_silent(command)
    if result.returncode != 0:
        warn(f"Unable to bootstrap {tool} with cargo: {_summarize_process_error(result)}")
        return False
    if not binary_available(*binaries):
        warn(f'{tool} fallback install completed but the expected binary was not found')
        return False
    note(f"Bootstrapped {tool} into {paths.bin_home}")
    _record_packages(manifest, [f'cargo:{tool}'])
    return True


def _downloadable_tool_metadata(tool: str) -> dict[str, str | tuple[str, ...]] | None:
    if not sys.platform.startswith('linux'):
        return None
    return DOWNLOADABLE_TOOLS.get(tool, {}).get(platform.machine().lower())


def _extract_archive(archive: Path, archive_type: str, stage_dir: Path, dry_run: bool) -> bool:
    if archive_type in {'tar.gz', 'tgz'}:
        command = ['tar', '-xzf', str(archive), '-C', str(stage_dir)]
    elif archive_type == 'tar.zst':
        command = ['tar', '--zstd', '-xf', str(archive), '-C', str(stage_dir)]
    elif archive_type == 'zip':
        command = ['unzip', '-oq', str(archive), '-d', str(stage_dir)]
    else:
        warn(f'Unknown archive type: {archive_type}')
        return False
    return _run(command, dry_run=dry_run)


def _install_from_release_archive(paths: Paths, env: EnvironmentInfo, tool: str, manifest: ManifestTransaction, dry_run: bool) -> bool:
    if binary_available(*TOOL_BINARIES[tool]):
        return True
    metadata = _downloadable_tool_metadata(tool)
    if not metadata:
        warn(f'No release bootstrap defined for {tool} on architecture {platform.machine()}')
        return False
    note(f"Bootstrapping {tool} from a prebuilt release")
    if not _ensure_helper_packages(env, 'archive', manifest, dry_run):
        warn(f'Unable to install archive helpers needed for {tool}')
        return False

    url = str(metadata['url'])
    archive_type = str(metadata['archive_type'])
    binaries = tuple(str(entry) for entry in metadata['binaries'])
    archive_name = url.rsplit('/', 1)[-1]
    archive = paths.cache_dir / archive_name
    stage_dir = paths.cache_dir / f'{tool}-stage'
    curl = resolve_binary('curl') or 'curl'

    if dry_run:
        print('[dry-run]', ' '.join([curl, '-fsSL', url, '-o', str(archive)]))
        if not _extract_archive(archive, archive_type, stage_dir, dry_run=True):
            return False
        for binary_name in binaries:
            print('[dry-run]', f'copy extracted {binary_name} to {paths.bin_home / binary_name}')
        return True

    result = _run_capture_silent([curl, '-fsSL', url, '-o', str(archive)])
    if result.returncode != 0:
        warn(f"Unable to download {tool}: {_summarize_process_error(result)}")
        return False

    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    if not _extract_archive(archive, archive_type, stage_dir, dry_run=False):
        warn(f"Unable to unpack the {tool} archive")
        return False

    for binary_name in binaries:
        matches = [candidate for candidate in stage_dir.rglob(binary_name) if candidate.is_file()]
        if not matches:
            warn(f'Unable to find {binary_name} in the downloaded {tool} archive')
            return False
        destination = paths.bin_home / binary_name
        _copy_file(paths, matches[0], destination, manifest)
        os.chmod(destination, 0o755)

    note(f"Bootstrapped {tool} into {paths.bin_home}")
    _record_packages(manifest, [f'bootstrap:{tool}'])
    return True


def _install_ollama_fallback(paths: Paths, env: EnvironmentInfo, manifest: ManifestTransaction, dry_run: bool) -> bool:
    if binary_available('ollama'):
        return True
    return _install_from_release_archive(paths, env, 'ollama', manifest, dry_run)


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


def _strict_install_enabled() -> bool:
    return os.environ.get('ZENITH_STRICT_BOOTSTRAP', '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _validate_strict_core(config: ResolvedConfig, env: EnvironmentInfo) -> None:
    if not _strict_install_enabled():
        return

    failures: list[str] = []
    for tool in STRICT_CORE_TOOLS:
        if binary_available(*TOOL_BINARIES[tool]):
            continue
        failures.append(f'missing required tool: {tool}')

    if binary_available('ollama') and _should_bootstrap_model(config, env):
        model = str(config.ai.get('model', 'llama3.2:3b'))
        ollama = resolve_binary('ollama')
        if not ollama or not _has_ollama_model(ollama, model):
            failures.append(f'missing required ollama model: {model}')

    if failures:
        summary = '\n'.join(f'  - {entry}' for entry in failures)
        raise SystemExit(f'Strict Zenith core bootstrap failed:\n{summary}')


def _install_core_fallbacks(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, manifest: ManifestTransaction, dry_run: bool) -> None:
    if not binary_available(*TOOL_BINARIES['zellij']):
        _install_from_release_archive(paths, env, 'zellij', manifest, dry_run)
    if not binary_available(*TOOL_BINARIES['yazi']):
        _install_from_release_archive(paths, env, 'yazi', manifest, dry_run)
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
    _validate_strict_core(config, env)

    if dry_run:
        ok("Core dry-run complete")
        return

    _write_config_file(paths, config, manifest)
    _install_local_launchers(paths, manifest)
    _write_shell_fragment(paths, config, manifest)
    _install_core_assets(paths, manifest)
    write_manifest(paths, manifest)
    ok("Core installed")


def install_surface(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, dry_run: bool, assume_yes: bool, force_upgrade: bool = False) -> None:
    error = surface_support_error(env)
    if error:
        raise SystemExit(error)

    terminal = normalize_terminal(config.surface.get('terminal'))
    manifest = begin_transaction(config.profile, env.resolved_mode, ["surface"])
    config.features["surface"] = True
    config.features["orbit"] = terminal == 'ghostty'
    _apply_config_paths(paths, config)
    info(f"Preparing surface install for profile={config.profile} mode={env.resolved_mode} terminal={terminal}")
    note('Surface installs are user-space only; Zenith will not use sudo or the host package manager here')
    _confirm("Apply Zenith surface changes?", assume_yes, dry_run)

    if not _ensure_surface_terminal(paths, config, env, terminal, manifest, dry_run, force_upgrade=force_upgrade):
        if _terminal_bootstrap_supported(terminal):
            raise SystemExit(f'{terminal} could not be installed in user space. Zenith reported the missing prerequisite or build failure above.')
        raise SystemExit(f'Zenith cannot install {terminal} in user space yet. Install it yourself first, then rerun this command.')

    if dry_run:
        if terminal in BUILTIN_SURFACE_TERMINALS:
            note(f"Zenith will install {terminal} surface assets under your home directory")
        else:
            note(f"Zenith will record terminal={terminal} but has no built-in surface assets for it yet")
        if not env.gui:
            note('No GUI session was detected, so Zenith would skip terminal config assets even though the terminal binary bootstrap was requested')
        ok("Surface dry-run complete")
        return

    _write_config_file(paths, config, manifest)
    if not env.gui:
        note('No GUI session was detected. Zenith installed or verified the terminal binary, but skipped GUI-facing surface assets.')
        write_manifest(paths, manifest)
        ok("Surface preference recorded")
        return

    if terminal in BUILTIN_SURFACE_TERMINALS:
        _install_surface_assets(paths, manifest, terminal)
        write_manifest(paths, manifest)
        ok("Surface installed")
        return

    note(f"Zenith recorded terminal={terminal}, but no terminal-specific surface assets were installed")
    write_manifest(paths, manifest)
    ok("Surface preference recorded")
