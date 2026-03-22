#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${ZENITH_IMAGE_NAME:-zenith}"
CONTAINER_NAME="${ZENITH_CONTAINER_NAME:-zenith-shell}"
CONFIG_VOLUME="${ZENITH_CONFIG_VOLUME:-zenith-config}"
DATA_VOLUME="${ZENITH_DATA_VOLUME:-zenith-data}"
PYTHON_BIN="${ZENITH_PYTHON_BIN:-python3}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zenith"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/zenith"
MANIFEST_DIR="$DATA_DIR/manifests"

show_path() {
  if [ -e "$1" ] || [ -L "$1" ]; then
    printf 'FOUND  %s\n' "$1"
  else
    printf 'CLEAR  %s\n' "$1"
  fi
}

printf 'Zenith artifact probe\n\n'

printf '[Core state]\n'
show_path "$CONFIG_DIR"
show_path "$DATA_DIR"
show_path "$HOME/.local/bin/zen"
show_path "$HOME/.local/bin/zenith"
show_path "$HOME/.local/bin/ollama"
show_path "$HOME/.local/bin/zellij"
show_path "$HOME/.local/bin/yazi"
show_path "$HOME/.local/bin/ya"
show_path "$HOME/.local/bin/starship"
show_path "$HOME/.ollama"

printf '\n[Managed config/assets]\n'
show_path "$HOME/.config/starship.toml"
show_path "$HOME/.config/zellij/config.kdl"
show_path "$HOME/.config/zellij/layouts/zenith.kdl"
show_path "$HOME/.config/ghostty/config"
show_path "$HOME/.config/ghostty/shaders/celestial.glsl"
show_path "$HOME/.config/ghostty/shaders/matrix.glsl"
show_path "$HOME/.config/ghostty/shaders/quantum.glsl"
show_path "$HOME/.config/ghostty/shaders/void.glsl"

printf '\n[Python package]\n'
if command -v "$PYTHON_BIN" >/dev/null 2>&1 && "$PYTHON_BIN" -m pip show project-zenith >/dev/null 2>&1; then
  printf 'FOUND  project-zenith pip package\n'
else
  printf 'CLEAR  project-zenith pip package\n'
fi

printf '\n[Manifest-recorded packages]\n'
if [ -d "$MANIFEST_DIR" ] && command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  "$PYTHON_BIN" - <<'PY2' "$MANIFEST_DIR"
import json
import sys
from pathlib import Path
manifest_dir = Path(sys.argv[1])
seen = []
for path in sorted(manifest_dir.glob('*.json')):
    if path.name == 'latest.json':
        continue
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        continue
    for package in payload.get('packages', []):
        if package not in seen:
            seen.append(package)
if not seen:
    print('CLEAR  no manifest-recorded packages')
else:
    for package in seen:
        print(f'FOUND  {package}')
PY2
else
  printf 'CLEAR  no manifest history available\n'
fi

printf '\n[Podman artifacts]\n'
if command -v podman >/dev/null 2>&1; then
  if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -Fx "$CONTAINER_NAME" >/dev/null 2>&1; then
    printf 'FOUND  container %s\n' "$CONTAINER_NAME"
  else
    printf 'CLEAR  container %s\n' "$CONTAINER_NAME"
  fi
  if podman images --format '{{.Repository}}' 2>/dev/null | grep -Fx "$IMAGE_NAME" >/dev/null 2>&1; then
    printf 'FOUND  image %s\n' "$IMAGE_NAME"
  else
    printf 'CLEAR  image %s\n' "$IMAGE_NAME"
  fi
  for volume in "$CONFIG_VOLUME" "$DATA_VOLUME"; do
    if podman volume ls --format '{{.Name}}' 2>/dev/null | grep -Fx "$volume" >/dev/null 2>&1; then
      printf 'FOUND  volume %s\n' "$volume"
    else
      printf 'CLEAR  volume %s\n' "$volume"
    fi
  done
else
  printf 'CLEAR  podman not installed\n'
fi
