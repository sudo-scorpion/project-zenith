#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-hybrid}"
IMAGE_NAME="${ZENITH_IMAGE_NAME:-zenith}"
CONTAINER_NAME="${ZENITH_CONTAINER_NAME:-zenith-shell}"
CONFIG_VOLUME="${ZENITH_CONFIG_VOLUME:-zenith-config}"
DATA_VOLUME="${ZENITH_DATA_VOLUME:-zenith-data}"
PYTHON_BIN="${ZENITH_PYTHON_BIN:-python3}"
PIP_PACKAGE="${ZENITH_PIP_PACKAGE:-project-zenith}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zenith"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/zenith"
MANIFEST_DIR="$DATA_DIR/manifests"

usage() {
  cat <<'EOF'
Usage: ./teardown.sh [hybrid|host|container|clean]

Most users should just run:
  ./teardown.sh

That removes the recommended hybrid setup.

Modes:
  hybrid    Remove host Zenith plus container artifacts
  host      Remove host Zenith only
  container Remove container artifacts only
  clean     Alias for the default full cleanup

This script aggressively removes Zenith-owned artifacts, including:
- Zenith config/state/data directories
- local Zenith shims and fallback binaries
- Ollama model/cache state that Zenith may have bootstrapped
- the persistent Zenith Podman container, volumes, and image
- manifest-recorded package installs when their package manager is available
EOF
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

log() {
  printf '%s\n' "$1"
}

remove_path() {
  if [ -e "$1" ] || [ -L "$1" ]; then
    rm -rf "$1"
    log "Removed $1"
  fi
}

manifest_packages() {
  if [ ! -d "$MANIFEST_DIR" ] || ! has_cmd "$PYTHON_BIN"; then
    return 0
  fi
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
for package in seen:
    print(package)
PY2
}

_sudo() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

remove_system_package() {
  package="$1"
  if has_cmd dnf; then
    _sudo dnf remove -y "$package" >/dev/null 2>&1 || true
    return
  fi
  if has_cmd pacman; then
    _sudo pacman -Rns --noconfirm "$package" >/dev/null 2>&1 || true
    return
  fi
  if has_cmd apt-get; then
    _sudo apt-get remove -y "$package" >/dev/null 2>&1 || true
    _sudo apt-get autoremove -y >/dev/null 2>&1 || true
    return
  fi
  if has_cmd zypper; then
    _sudo zypper --non-interactive remove "$package" >/dev/null 2>&1 || true
    return
  fi
  if has_cmd apk; then
    _sudo apk del "$package" >/dev/null 2>&1 || true
    return
  fi
  if has_cmd brew; then
    brew uninstall "$package" >/dev/null 2>&1 || true
    return
  fi
}

remove_manifest_packages() {
  manifest_packages | while IFS= read -r package; do
    [ -n "$package" ] || continue
    case "$package" in
      cargo:zellij)
        if has_cmd cargo; then
          cargo uninstall --root "$HOME/.local" zellij >/dev/null 2>&1 || true
        fi
        remove_path "$HOME/.local/bin/zellij"
        ;;
      cargo:starship)
        if has_cmd cargo; then
          cargo uninstall --root "$HOME/.local" starship >/dev/null 2>&1 || true
        fi
        remove_path "$HOME/.local/bin/starship"
        ;;
      cargo:yazi)
        if has_cmd cargo; then
          cargo uninstall --root "$HOME/.local" yazi-fm >/dev/null 2>&1 || true
          cargo uninstall --root "$HOME/.local" yazi-cli >/dev/null 2>&1 || true
        fi
        remove_path "$HOME/.local/bin/yazi"
        remove_path "$HOME/.local/bin/ya"
        ;;
      bootstrap:ollama)
        remove_path "$HOME/.local/bin/ollama"
        ;;
      bootstrap:kitty:*)
        remove_path "$HOME/.local/bin/kitty"
        remove_path "$HOME/.local/bin/kitten"
        remove_path "$HOME/.local/kitty.app"
        ;;
      ollama-model:*)
        model="${package#ollama-model:}"
        if has_cmd ollama; then
          ollama rm "$model" >/dev/null 2>&1 || true
        fi
        ;;
      *)
        remove_system_package "$package"
        ;;
    esac
  done
}

strip_zenith_from_rc() {
  local rc_file="$1"
  [ -f "$rc_file" ] || return 0
  # Remove the "# Project Zenith" block: the marker line + the 3 lines after it
  if grep -q '# Project Zenith' "$rc_file" 2>/dev/null; then
    sed -i '/# Project Zenith/{N;N;N;d}' "$rc_file"
    log "Stripped Zenith hook from $rc_file"
  fi
}

cleanup_host() {
  if has_cmd "$PYTHON_BIN"; then
    if "$PYTHON_BIN" -c 'import zenith' >/dev/null 2>&1; then
      "$PYTHON_BIN" -m zenith.cli uninstall --yes || true
    fi
    "$PYTHON_BIN" -m pip uninstall -y "$PIP_PACKAGE" >/dev/null 2>&1 || true
  fi

  # Belt-and-suspenders: strip Zenith hook from shell RCs even if manifest rollback missed it
  strip_zenith_from_rc "$HOME/.bashrc"
  strip_zenith_from_rc "$HOME/.zshrc"
  strip_zenith_from_rc "$HOME/.bash_profile"
  strip_zenith_from_rc "$HOME/.zprofile"

  remove_manifest_packages

  remove_path "$HOME/.local/bin/zen"
  remove_path "$HOME/.local/bin/zenith"
  remove_path "$HOME/.local/bin/ollama"
  remove_path "$HOME/.local/lib/ollama"
  remove_path "$HOME/.local/bin/kitty"
  remove_path "$HOME/.local/bin/kitten"
  remove_path "$HOME/.local/bin/zellij"
  remove_path "$HOME/.local/bin/yazi"
  remove_path "$HOME/.local/bin/ya"
  remove_path "$HOME/.local/bin/starship"
  remove_path "$HOME/.local/kitty.app"
  remove_path "$HOME/.ollama"

  remove_path "$HOME/.config/starship.toml"
  remove_path "$HOME/.config/kitty/kitty.conf"
  remove_path "$HOME/.config/zellij/layouts/zenith.kdl"
  remove_path "$HOME/.config/zellij/config.kdl"
  remove_path "$HOME/.config/ghostty/shaders/celestial.glsl"
  remove_path "$HOME/.config/ghostty/shaders/matrix.glsl"
  remove_path "$HOME/.config/ghostty/shaders/quantum.glsl"
  remove_path "$HOME/.config/ghostty/shaders/void.glsl"
  remove_path "$HOME/.config/ghostty/config"

  # zsh plugins cloned by zen install core
  remove_path "$HOME/.local/share/zsh-plugins"

  # caches written by tools Zenith installs
  remove_path "$HOME/.cache/starship"
  remove_path "$HOME/.cache/zoxide"
  remove_path "$HOME/.local/share/zoxide"

  # zsh completion dump written on first zsh start after install
  for f in "$HOME"/.zcompdump*; do
    [ -e "$f" ] && remove_path "$f"
  done

  remove_path "$CONFIG_DIR"
  remove_path "$DATA_DIR"
}

cleanup_container() {
  if ! has_cmd podman; then
    log 'Skipping container cleanup because podman is not installed.'
    return 0
  fi

  podman rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  podman volume rm -f "$CONFIG_VOLUME" "$DATA_VOLUME" >/dev/null 2>&1 || true
  podman image rm -f "$IMAGE_NAME" >/dev/null 2>&1 || true
  log "Removed Podman artifacts for $CONTAINER_NAME / $IMAGE_NAME"
}

case "$MODE" in
  hybrid|clean)
    cleanup_host
    cleanup_container
    ;;
  host)
    cleanup_host
    ;;
  container)
    cleanup_container
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    printf 'Unknown mode: %s\n\n' "$MODE" >&2
    usage >&2
    exit 1
    ;;
esac
