from __future__ import annotations

import json
from pathlib import Path

from .models import Paths, ResolvedConfig
from .shells import SUPPORTED_SHELLS, detect_default_shell, normalize_shell

DEFAULTS = {
    "profile": "safe",
    "mode": "auto",
    "shell": "bash",
    "features": {
        "core": False,
        "surface": False,
        "ai_nav": True,
        "ai_fix": True,
        "workspace": True,
        "orbit": False,
        "alias_overrides": False,
    },
    "ai": {
        "provider": "ollama",
        "host": "http://127.0.0.1:11434",
        "model": "qwen3.5:4b",
        "ask_model": "",
        "fix_model": "",
        "keep_alive": "15m",
        "timeout_seconds": 90,
        "temperature": 0.0,
        "num_ctx": 4096,
        "num_predict": 160,
        "top_k": 40,
        "top_p": 0.9,
        "repeat_penalty": 1.05,
        "structured_output": True,
        "auto_execute_safe": False,
        "log_generated_commands": True,
    },
    "surface": {
        "terminal": "kitty",
        "orbit_profile": "celestial",
        "auto_sync": False,
    },
    "updates": {
        "check_on_startup": False,
        "recommend_on_startup": True,
        "auto_upgrade_on_startup": False,
        "startup_interval_hours": 24,
        "kitty_version": "",
        "ghostty_version": "",
    },
    "workspace": {
        "default_session": "zenith",
        "auto_resume": True,
    },
    "paths": {
        "install_root": "~/.local/share/zenith",
        "log_dir": "~/.config/zenith/logs",
    },
}

FEATURE_KEYS = ("core", "surface", "ai_nav", "ai_fix", "workspace", "orbit", "alias_overrides")
AI_KEYS = (
    "provider",
    "host",
    "model",
    "ask_model",
    "fix_model",
    "keep_alive",
    "timeout_seconds",
    "temperature",
    "num_ctx",
    "num_predict",
    "top_k",
    "top_p",
    "repeat_penalty",
    "structured_output",
    "auto_execute_safe",
    "log_generated_commands",
)
SURFACE_KEYS = ("terminal", "orbit_profile", "auto_sync")
UPDATE_KEYS = (
    "check_on_startup",
    "recommend_on_startup",
    "auto_upgrade_on_startup",
    "startup_interval_hours",
    "kitty_version",
    "ghostty_version",
)
WORKSPACE_KEYS = ("default_session", "auto_resume")
PATH_KEYS = ("install_root", "log_dir")

SECTION_COMMENTS = {
    "features": [
        "Turn Zenith feature groups on or off.",
    ],
    "ai": [
        "AI runtime and generation settings.",
        "Use ask_model for fast command suggestions and fix_model for stronger repair flows.",
    ],
    "surface": [
        "Host-side terminal surface settings.",
        "Zenith manages supported terminals in user space only.",
    ],
    "updates": [
        "Surface install and upgrade policy.",
        "check_on_startup: periodically check whether Zenith recommends a surface install or upgrade.",
        "recommend_on_startup: print a recommendation during shell startup when Zenith sees one.",
        "auto_upgrade_on_startup: apply the supported surface upgrade automatically during shell startup.",
        "startup_interval_hours: minimum time between startup checks.",
        "kitty_version: optional explicit Kitty version pin for deterministic installs/upgrades.",
        "ghostty_version: optional explicit Ghostty version pin for deterministic installs/upgrades.",
    ],
    "workspace": [
        "Workspace session defaults.",
    ],
    "paths": [
        "Zenith-owned paths in your user space.",
    ],
}


def _toml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def _render_section(name: str, values: dict[str, object], keys: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for comment in SECTION_COMMENTS.get(name, ()):
        lines.append(f"# {comment}")
    lines.append(f"[{name}]")
    for key in keys:
        lines.append(f"{key} = {_toml_scalar(values[key])}")
    return lines


def _format_toml(config: ResolvedConfig) -> str:
    lines = [
        "# Zenith configuration",
        "# Edit this file with: zen config edit",
        "# Inspect current state with: zen status --json, zen doctor, zen upgrade surface --check",
        "",
        "# Core identity",
        f"profile = {_toml_scalar(config.profile)}",
        f"mode = {_toml_scalar(config.mode)}",
        f"shell = {_toml_scalar(config.shell)}",
        "",
    ]
    lines.extend(_render_section("features", config.features, FEATURE_KEYS))
    lines.append("")
    lines.extend(_render_section("ai", config.ai, AI_KEYS))
    lines.append("")
    lines.extend(_render_section("surface", config.surface, SURFACE_KEYS))
    lines.append("")
    lines.extend(_render_section("updates", config.updates, UPDATE_KEYS))
    lines.append("")
    lines.extend(_render_section("workspace", config.workspace, WORKSPACE_KEYS))
    lines.append("")
    lines.extend(_render_section("paths", config.paths, PATH_KEYS))
    return "\n".join(lines) + "\n"


def default_config(profile: str = "safe", mode: str = "auto", shell: str | None = None) -> ResolvedConfig:
    cfg = ResolvedConfig(
        profile=profile,
        mode=mode,
        shell=normalize_shell(shell or detect_default_shell() or DEFAULTS["shell"]),
        features=dict(DEFAULTS["features"]),
        ai=dict(DEFAULTS["ai"]),
        surface=dict(DEFAULTS["surface"]),
        updates=dict(DEFAULTS["updates"]),
        workspace=dict(DEFAULTS["workspace"]),
        paths=dict(DEFAULTS["paths"]),
    )
    cfg.features["alias_overrides"] = profile == "personal"
    return cfg


def normalize_terminal(terminal: str | None) -> str:
    value = str(terminal or DEFAULTS["surface"]["terminal"]).strip().lower()
    if not value:
        raise ValueError("Config surface.terminal must be set")
    return value


def load_config(
    paths: Paths,
    cli_profile: str | None = None,
    cli_mode: str | None = None,
    cli_shell: str | None = None,
    cli_terminal: str | None = None,
) -> ResolvedConfig:
    cfg = default_config()
    if paths.config_file.exists():
        import tomllib

        data = tomllib.loads(paths.config_file.read_text(encoding="utf-8"))
        cfg.profile = data.get("profile", cfg.profile)
        cfg.mode = data.get("mode", cfg.mode)
        cfg.shell = data.get("shell", cfg.shell)
        cfg.features.update(data.get("features", {}))
        cfg.ai.update(data.get("ai", {}))
        cfg.surface.update(data.get("surface", {}))
        cfg.updates.update(data.get("updates", {}))
        cfg.workspace.update(data.get("workspace", {}))
        cfg.paths.update(data.get("paths", {}))
    if cli_profile:
        cfg.profile = cli_profile
        cfg.features["alias_overrides"] = cli_profile == "personal"
    if cli_mode:
        cfg.mode = cli_mode
    if cli_shell:
        cfg.shell = normalize_shell(cli_shell)
    if cli_terminal:
        cfg.surface["terminal"] = normalize_terminal(cli_terminal)
    validate_config(cfg)
    return cfg


def write_config(paths: Paths, config: ResolvedConfig) -> None:
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.config_file.write_text(_format_toml(config), encoding="utf-8")


def show_config(paths: Paths, config: ResolvedConfig) -> str:
    if not paths.config_file.exists():
        write_config(paths, config)
    return paths.config_file.read_text(encoding="utf-8")


def config_path(paths: Paths) -> Path:
    return paths.config_file


def validate_config(config: ResolvedConfig) -> None:
    if config.profile not in {"personal", "safe"}:
        raise ValueError(f"Unsupported profile: {config.profile}")
    if config.mode not in {"auto", "host", "container"}:
        raise ValueError(f"Unsupported mode: {config.mode}")
    if normalize_shell(config.shell) not in SUPPORTED_SHELLS:
        supported = ", ".join(SUPPORTED_SHELLS)
        raise ValueError(f"Unsupported shell: {config.shell}. Supported shells: {supported}")
    config.shell = normalize_shell(config.shell)
    if config.ai.get("provider") == "ollama":
        pass
    else:
        raise ValueError("V1 currently supports ollama only")
    if not str(config.ai.get("host", "")).strip():
        raise ValueError("Config ai.host must be set")
    if not str(config.ai.get("model", "")).strip():
        raise ValueError("Config ai.model must be set")
    if "nav_model" in config.ai and not str(config.ai.get("ask_model", "")).strip():
        config.ai["ask_model"] = config.ai.get("nav_model", "")
    for key in ("ask_model", "fix_model"):
        if key in config.ai and config.ai[key] is not None:
            config.ai[key] = str(config.ai[key]).strip()
    for key in ("timeout_seconds", "num_ctx", "num_predict", "top_k"):
        value = int(config.ai.get(key, DEFAULTS["ai"][key]))
        if value <= 0:
            raise ValueError(f"Config ai.{key} must be greater than zero")
        config.ai[key] = value
    for key in ("temperature", "top_p", "repeat_penalty"):
        value = float(config.ai.get(key, DEFAULTS["ai"][key]))
        if value < 0:
            raise ValueError(f"Config ai.{key} must not be negative")
        config.ai[key] = value
    config.surface["terminal"] = normalize_terminal(config.surface.get("terminal"))
    config.updates["kitty_version"] = str(config.updates.get("kitty_version", "")).strip()
    config.updates["ghostty_version"] = str(config.updates.get("ghostty_version", "")).strip()
    for key in ("check_on_startup", "recommend_on_startup", "auto_upgrade_on_startup"):
        config.updates[key] = bool(config.updates.get(key, DEFAULTS["updates"][key]))
    interval = int(config.updates.get("startup_interval_hours", DEFAULTS["updates"]["startup_interval_hours"]))
    if interval < 0:
        raise ValueError("Config updates.startup_interval_hours must not be negative")
    config.updates["startup_interval_hours"] = interval
    if not config.paths.get("install_root") or not config.paths.get("log_dir"):
        raise ValueError("Config paths.install_root and paths.log_dir must be set")
