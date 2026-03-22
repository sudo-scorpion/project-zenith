from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timedelta

from .binaries import resolve_binary, with_local_bin_path
from .config import normalize_terminal
from .install import _ghostty_version as detect_latest_ghostty_version
from .install import _kitty_version as detect_latest_kitty_version
from .manifest import load_manifest_history
from .models import EnvironmentInfo, Paths, ResolvedConfig

SURFACE_LABELS = {
    'ghostty': 'Ghostty',
    'kitty': 'Kitty',
}


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = re.findall(r'\d+', str(version))
    if len(parts) < 3:
        return ()
    return tuple(int(piece) for piece in parts[:3])


def _compare_versions(left: str, right: str) -> int:
    left_parts = _version_tuple(left)
    right_parts = _version_tuple(right)
    if not left_parts or not right_parts:
        return 0
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0


def _read_upgrade_state(paths: Paths) -> dict:
    if not paths.upgrade_state_file.exists():
        return {}
    try:
        return json.loads(paths.upgrade_state_file.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_upgrade_state(paths: Paths, payload: dict) -> None:
    paths.upgrade_state_file.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def _cached_surface_report(paths: Paths) -> dict:
    payload = _read_upgrade_state(paths)
    return dict(payload.get('surface', {}))


def _installed_version_from_manifest(paths: Paths, terminal: str) -> str:
    history = load_manifest_history(paths)
    for _, manifest in reversed(history):
        for package in reversed(list(manifest.get('packages', []))):
            if package.startswith(f'bootstrap:{terminal}:'):
                return package.rsplit(':', 1)[-1]
    return ''


def _installed_version_from_binary(terminal: str) -> str:
    binary = resolve_binary(terminal)
    if not binary:
        return ''
    commands = [[binary, '--version']]
    if terminal == 'ghostty':
        commands.append([binary, '+version'])
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=with_local_bin_path())
        text = (result.stdout or '') + '\n' + (result.stderr or '')
        match = re.search(r'(\d+\.\d+\.\d+)', text)
        if match:
            return match.group(1)
    return ''


def installed_surface_version(paths: Paths, terminal: str) -> str:
    version = _installed_version_from_manifest(paths, terminal)
    if version:
        return version
    return _installed_version_from_binary(terminal)


def recommended_surface_version(
    paths: Paths,
    config: ResolvedConfig,
    terminal: str,
    *,
    allow_network: bool = True,
) -> tuple[str, str]:
    if terminal == 'ghostty':
        pinned = os.environ.get('ZENITH_GHOSTTY_VERSION', '').strip() or str(config.updates.get('ghostty_version', '')).strip()
        detector = detect_latest_ghostty_version
    elif terminal == 'kitty':
        pinned = os.environ.get('ZENITH_KITTY_VERSION', '').strip() or str(config.updates.get('kitty_version', '')).strip()
        detector = detect_latest_kitty_version
    else:
        return '', 'unsupported'
    if pinned:
        return pinned, 'pinned'
    cached = _cached_surface_report(paths)
    cached_version = str(cached.get('recommended_version', '')).strip()
    if not allow_network:
        return cached_version, 'cached' if cached_version else 'unknown'
    detected = detector(paths, config) or ''
    if detected:
        return detected, 'detected'
    return cached_version, 'cached' if cached_version else 'unknown'


def surface_upgrade_report(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo, *, allow_network: bool = True) -> dict[str, str | bool]:
    terminal = normalize_terminal(config.surface.get('terminal'))
    label = SURFACE_LABELS.get(terminal, terminal.capitalize())
    if terminal not in SURFACE_LABELS:
        return {
            'component': 'surface',
            'terminal': terminal,
            'installed_version': '',
            'recommended_version': '',
            'recommended_source': 'unsupported',
            'status': 'unsupported-terminal',
            'message': f'Zenith does not manage upgrades for terminal={terminal} yet.',
            'container': env.container,
        }

    installed_version = installed_surface_version(paths, terminal)
    recommended_version, recommended_source = recommended_surface_version(paths, config, terminal, allow_network=allow_network)

    if not recommended_version:
        message = f'{label} is not installed and Zenith does not know a recommended version yet.'
        if installed_version:
            message = f'{label} {installed_version} is installed, but Zenith does not know a newer recommended version right now.'
        return {
            'component': 'surface',
            'terminal': terminal,
            'installed_version': installed_version,
            'recommended_version': '',
            'recommended_source': recommended_source,
            'status': 'unknown',
            'message': message,
            'container': env.container,
        }

    if not installed_version:
        return {
            'component': 'surface',
            'terminal': terminal,
            'installed_version': '',
            'recommended_version': recommended_version,
            'recommended_source': recommended_source,
            'status': 'install-available',
            'message': f'{label} {recommended_version} is recommended but not installed by Zenith yet.',
            'container': env.container,
        }

    comparison = _compare_versions(installed_version, recommended_version)
    if comparison < 0:
        return {
            'component': 'surface',
            'terminal': terminal,
            'installed_version': installed_version,
            'recommended_version': recommended_version,
            'recommended_source': recommended_source,
            'status': 'upgrade-available',
            'message': f'{label} upgrade available: installed {installed_version}, recommended {recommended_version}.',
            'container': env.container,
        }

    return {
        'component': 'surface',
        'terminal': terminal,
        'installed_version': installed_version,
        'recommended_version': recommended_version,
        'recommended_source': recommended_source,
        'status': 'current',
        'message': f'{label} {installed_version} is current for Zenith.',
        'container': env.container,
    }


def record_surface_upgrade_report(paths: Paths, report: dict[str, str | bool]) -> None:
    payload = _read_upgrade_state(paths)
    payload['surface'] = {
        'checked_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        **report,
    }
    _write_upgrade_state(paths, payload)


def startup_check_due(paths: Paths, config: ResolvedConfig) -> bool:
    interval = int(config.updates.get('startup_interval_hours', 24))
    if interval <= 0:
        return True
    cached = _cached_surface_report(paths)
    checked_at = str(cached.get('checked_at', '')).strip()
    if not checked_at:
        return True
    try:
        last = datetime.fromisoformat(checked_at)
    except ValueError:
        return True
    deadline = last + timedelta(hours=interval)
    return datetime.now().astimezone() >= deadline


def startup_upgrade_plan(paths: Paths, config: ResolvedConfig, env: EnvironmentInfo) -> dict[str, str | bool | dict]:
    check_on_startup = bool(config.updates.get('check_on_startup'))
    recommend_on_startup = bool(config.updates.get('recommend_on_startup', True))
    auto_upgrade_on_startup = bool(config.updates.get('auto_upgrade_on_startup'))

    if not check_on_startup and not auto_upgrade_on_startup:
        return {'run': False, 'message': '', 'should_upgrade': False, 'report': {}}
    if not startup_check_due(paths, config):
        return {'run': False, 'message': '', 'should_upgrade': False, 'report': {}}

    report = surface_upgrade_report(paths, config, env, allow_network=True)
    record_surface_upgrade_report(paths, report)

    should_upgrade = auto_upgrade_on_startup and report.get('status') in {'install-available', 'upgrade-available'}
    message = ''
    if should_upgrade:
        message = str(report.get('message', 'Zenith will upgrade the configured surface terminal on startup.'))
    elif recommend_on_startup and report.get('status') in {'install-available', 'upgrade-available'}:
        message = str(report.get('message', 'Zenith recommends a surface upgrade.')) + ' Run `zen upgrade surface`.'

    return {'run': True, 'message': message, 'should_upgrade': should_upgrade, 'report': report}


def render_upgrade_report(report: dict[str, str | bool], as_json: bool) -> str:
    if as_json:
        return json.dumps(report, indent=2)
    lines = [
        f"component: {report.get('component', 'surface')}",
        f"terminal: {report.get('terminal', '')}",
        f"installed: {report.get('installed_version', '') or 'none'}",
        f"recommended: {report.get('recommended_version', '') or 'unknown'}",
        f"source: {report.get('recommended_source', '')}",
        f"status: {report.get('status', '')}",
        f"message: {report.get('message', '')}",
    ]
    return '\n'.join(lines)
