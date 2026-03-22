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
