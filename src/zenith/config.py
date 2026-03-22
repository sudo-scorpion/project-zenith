from __future__ import annotations

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
        "model": "llama3.2:3b",
        "auto_execute_safe": False,
        "log_generated_commands": True,
    },
    "surface": {
        "terminal": "ghostty",
        "orbit_profile": "celestial",
        "auto_sync": False,
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


def _format_toml(config: ResolvedConfig) -> str:
    def bool_str(value: bool) -> str:
        return "true" if value else "false"

    return f'''profile = "{config.profile}"
mode = "{config.mode}"
shell = "{config.shell}"

[features]
core = {bool_str(config.features['core'])}
surface = {bool_str(config.features['surface'])}
ai_nav = {bool_str(config.features['ai_nav'])}
ai_fix = {bool_str(config.features['ai_fix'])}
workspace = {bool_str(config.features['workspace'])}
orbit = {bool_str(config.features['orbit'])}
alias_overrides = {bool_str(config.features['alias_overrides'])}

[ai]
provider = "{config.ai['provider']}"
model = "{config.ai['model']}"
auto_execute_safe = {bool_str(config.ai['auto_execute_safe'])}
log_generated_commands = {bool_str(config.ai['log_generated_commands'])}

[surface]
terminal = "{config.surface['terminal']}"
orbit_profile = "{config.surface['orbit_profile']}"
auto_sync = {bool_str(config.surface['auto_sync'])}

[workspace]
default_session = "{config.workspace['default_session']}"
auto_resume = {bool_str(config.workspace['auto_resume'])}

[paths]
install_root = "{config.paths['install_root']}"
log_dir = "{config.paths['log_dir']}"
'''


def default_config(profile: str = "safe", mode: str = "auto", shell: str | None = None) -> ResolvedConfig:
    cfg = ResolvedConfig(
        profile=profile,
        mode=mode,
        shell=normalize_shell(shell or detect_default_shell() or DEFAULTS["shell"]),
        features=dict(DEFAULTS["features"]),
        ai=dict(DEFAULTS["ai"]),
        surface=dict(DEFAULTS["surface"]),
        workspace=dict(DEFAULTS["workspace"]),
        paths=dict(DEFAULTS["paths"]),
    )
    cfg.features["alias_overrides"] = profile == "personal"
    return cfg


def load_config(paths: Paths, cli_profile: str | None = None, cli_mode: str | None = None, cli_shell: str | None = None) -> ResolvedConfig:
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
        cfg.workspace.update(data.get("workspace", {}))
        cfg.paths.update(data.get("paths", {}))
    if cli_profile:
        cfg.profile = cli_profile
        cfg.features["alias_overrides"] = cli_profile == "personal"
    if cli_mode:
        cfg.mode = cli_mode
    if cli_shell:
        cfg.shell = normalize_shell(cli_shell)
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
    if config.ai.get("provider") != "ollama":
        raise ValueError("V1 currently supports ollama only")
    if config.surface.get("terminal") != "ghostty":
        raise ValueError("V1 currently supports ghostty only for the surface layer")
    if not config.paths.get("install_root") or not config.paths.get("log_dir"):
        raise ValueError("Config paths.install_root and paths.log_dir must be set")
