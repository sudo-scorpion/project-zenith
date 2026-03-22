from __future__ import annotations

from datetime import datetime
from pathlib import Path

VALID_ORBITS = {"celestial", "matrix", "quantum", "void"}


def apply_orbit(home: Path, profile: str) -> None:
    if profile not in VALID_ORBITS:
        raise SystemExit("Usage: zen orbit <celestial|matrix|quantum|void>")
    shader = home / ".config/ghostty/shaders" / f"{profile}.glsl"
    if not shader.exists():
        raise SystemExit(f"Orbit profile not installed: {profile}")
    config_path = home / ".config/ghostty/config"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        # Surgically replace only theme and custom-shader lines so user
        # customisations (fonts, keybindings, etc.) are preserved.
        lines = config_path.read_text(encoding="utf-8").splitlines()
        new_lines: list[str] = []
        found_theme = False
        found_shader = False
        for line in lines:
            key = line.split("=", 1)[0].strip()
            if key == "theme":
                new_lines.append(f'theme = "{profile}"')
                found_theme = True
            elif key == "custom-shader":
                new_lines.append(f'custom-shader = "{shader}"')
                found_shader = True
            else:
                new_lines.append(line)
        if not found_theme:
            new_lines.append(f'theme = "{profile}"')
        if not found_shader:
            new_lines.append(f'custom-shader = "{shader}"')
        config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        config_path.write_text(
            "\n".join(
                [
                    'font-family = "JetBrains Mono"',
                    'font-size = 13',
                    f'theme = "{profile}"',
                    f'custom-shader = "{shader}"',
                    'background-opacity = 0.92',
                    "",
                ]
            ),
            encoding="utf-8",
        )


def sync_orbit(home: Path) -> None:
    hour = datetime.now().hour
    if 6 <= hour < 16:
        profile = "celestial"
    elif 16 <= hour < 20:
        profile = "quantum"
    elif 20 <= hour < 23:
        profile = "matrix"
    else:
        profile = "void"
    apply_orbit(home, profile)
