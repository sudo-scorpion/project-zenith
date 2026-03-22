from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .models import Paths, ResolvedConfig
from .surface import VALID_ORBITS, apply_orbit

BUILTIN_ORBIT_DESCRIPTIONS = {
    "celestial": "Deep space blues with aurora shader",
    "matrix": "Green-on-black with matrix rain shader",
    "quantum": "Purple quantum field shader",
    "void": "Minimal dark void shader",
}

_KITTY_COLOR_KEYS = (
    "background", "foreground", "cursor", "selection_background", "selection_foreground",
    *(f"color{i}" for i in range(16)),
)


@dataclass
class ThemeInfo:
    name: str
    description: str
    source: str   # "builtin" or "user"
    path: Path | None = None


def list_themes(paths: Paths) -> list[ThemeInfo]:
    themes: list[ThemeInfo] = []
    for name in sorted(VALID_ORBITS):
        themes.append(ThemeInfo(
            name=name,
            description=BUILTIN_ORBIT_DESCRIPTIONS.get(name, "Built-in orbit theme"),
            source="builtin",
        ))
    if paths.themes_dir.exists():
        for toml_file in sorted(paths.themes_dir.glob("*.toml")):
            try:
                data = tomllib.loads(toml_file.read_text(encoding="utf-8"))
                themes.append(ThemeInfo(
                    name=str(data.get("name", toml_file.stem)),
                    description=str(data.get("description", "")),
                    source="user",
                    path=toml_file,
                ))
            except Exception:
                pass
    return themes


def _load_user_theme(theme_path: Path) -> dict:
    try:
        return tomllib.loads(theme_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Cannot load theme from {theme_path}: {exc}") from exc


def _find_theme(paths: Paths, name: str) -> ThemeInfo | None:
    for theme in list_themes(paths):
        if theme.name == name:
            return theme
    return None


def _apply_kitty_colors(home: Path, colors: dict[str, str], dry_run: bool) -> None:
    kitty_conf = home / ".config/kitty/kitty.conf"
    if not kitty_conf.exists():
        if dry_run:
            return
        kitty_conf.parent.mkdir(parents=True, exist_ok=True)
        kitty_conf.write_text("", encoding="utf-8")

    lines = kitty_conf.read_text(encoding="utf-8").splitlines()
    updated: dict[str, bool] = {k: False for k in colors}
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        key = stripped.split()[0] if stripped.split() else ""
        if key in colors:
            new_lines.append(f"{key} {colors[key]}")
            updated[key] = True
        else:
            new_lines.append(line)

    for key, value in colors.items():
        if not updated[key]:
            new_lines.append(f"{key} {value}")

    if not dry_run:
        kitty_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _apply_ghostty_colors(home: Path, colors: dict[str, str], shader: str | None, dry_run: bool) -> None:
    ghostty_conf = home / ".config/ghostty/config"
    if not ghostty_conf.exists():
        if dry_run:
            return
        ghostty_conf.parent.mkdir(parents=True, exist_ok=True)
        ghostty_conf.write_text("", encoding="utf-8")

    lines = ghostty_conf.read_text(encoding="utf-8").splitlines()
    updated: dict[str, bool] = {k: False for k in colors}
    shader_updated = False
    new_lines: list[str] = []

    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in colors:
            new_lines.append(f"{key} = {colors[key]}")
            updated[key] = True
        elif key == "custom-shader" and shader is not None:
            new_lines.append(f'custom-shader = "{shader}"')
            shader_updated = True
        else:
            new_lines.append(line)

    for key, value in colors.items():
        if not updated[key]:
            new_lines.append(f"{key} = {value}")
    if shader and not shader_updated:
        new_lines.append(f'custom-shader = "{shader}"')

    if not dry_run:
        ghostty_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def apply_theme(paths: Paths, config: ResolvedConfig, name: str, dry_run: bool = False) -> None:
    from .logging_utils import info, ok
    theme = _find_theme(paths, name)
    if theme is None:
        raise SystemExit(f"Theme '{name}' not found. Use: zen theme list")

    if theme.source == "builtin":
        if dry_run:
            info(f"[dry-run] would apply orbit theme '{name}'")
            return
        apply_orbit(paths.home, name)
        config.surface["orbit_profile"] = name
        config.surface["theme"] = ""
        from .config import write_config
        write_config(paths, config)
        return

    if theme.path is None:
        raise SystemExit(f"Theme '{name}' has no file path — cannot apply user theme.")
    data = _load_user_theme(theme.path)
    kitty_colors: dict[str, str] = {
        k: str(v) for k, v in data.get("kitty_colors", {}).items()
        if k in _KITTY_COLOR_KEYS
    }
    ghostty_colors: dict[str, str] = {
        k: str(v) for k, v in data.get("ghostty_colors", {}).items()
    }
    shader = str(data.get("shader", {}).get("path", "")).strip() or None

    terminal = str(config.surface.get("terminal", "kitty"))
    if kitty_colors and terminal == "kitty":
        info(f"Applying Kitty colors for theme '{name}'")
        _apply_kitty_colors(paths.home, kitty_colors, dry_run)

    if ghostty_colors and terminal == "ghostty":
        info(f"Applying Ghostty colors for theme '{name}'")
        _apply_ghostty_colors(paths.home, ghostty_colors, shader, dry_run)

    if not dry_run:
        config.surface["theme"] = name
        from .config import write_config
        write_config(paths, config)
        ok(f"Theme '{name}' applied")


def preview_theme(paths: Paths, name: str) -> str:
    theme = _find_theme(paths, name)
    if theme is None:
        raise SystemExit(f"Theme '{name}' not found. Use: zen theme list")

    lines = [f"Theme:   {theme.name}", f"Source:  {theme.source}"]
    if theme.description:
        lines.append(f"Info:    {theme.description}")

    if theme.source == "user" and theme.path:
        try:
            data = _load_user_theme(theme.path)
            kitty_n = len(data.get("kitty_colors", {}))
            ghostty_n = len(data.get("ghostty_colors", {}))
            has_shader = bool(str(data.get("shader", {}).get("path", "")).strip())
            lines.append(f"Kitty:   {kitty_n} color keys")
            lines.append(f"Ghostty: {ghostty_n} color keys")
            if has_shader:
                lines.append(f"Shader:  {data['shader']['path']}")
        except SystemExit:
            lines.append("(theme file could not be parsed)")

    return "\n".join(lines)


def export_theme(paths: Paths, config: ResolvedConfig, name: str) -> str:
    terminal = str(config.surface.get("terminal", "kitty"))
    lines = [
        f'name = "{name}"',
        'description = ""',
        'author = ""',
        "",
    ]

    if terminal == "kitty":
        kitty_conf = paths.home / ".config/kitty/kitty.conf"
        kitty_colors: dict[str, str] = {}
        if kitty_conf.exists():
            for line in kitty_conf.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] in _KITTY_COLOR_KEYS:
                    kitty_colors[parts[0]] = parts[1]
        lines.append("[kitty_colors]")
        for key in _KITTY_COLOR_KEYS:
            if key in kitty_colors:
                lines.append(f'{key} = "{kitty_colors[key]}"')
            else:
                lines.append(f'# {key} = ""')
        lines.append("")

    if terminal == "ghostty":
        ghostty_conf = paths.home / ".config/ghostty/config"
        ghostty_colors: dict[str, str] = {}
        if ghostty_conf.exists():
            for line in ghostty_conf.read_text(encoding="utf-8").splitlines():
                key_part, _, val_part = line.partition("=")
                key = key_part.strip()
                val = val_part.strip().strip('"')
                if key and val and not key.startswith("#"):
                    ghostty_colors[key] = val
        lines.append("[ghostty_colors]")
        for key, val in ghostty_colors.items():
            if key not in ("theme", "custom-shader"):
                lines.append(f'{key} = "{val}"')
        lines.append("")
        lines.append("[shader]")
        shader_val = ghostty_colors.get("custom-shader", "")
        lines.append(f'path = "{shader_val}"')

    return "\n".join(lines) + "\n"
