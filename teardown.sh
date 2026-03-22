#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-hybrid}"
IMAGE_NAME="${ZENITH_IMAGE_NAME:-zenith}"
CONTAINER_NAME="${ZENITH_CONTAINER_NAME:-zenith-shell}"
CONFIG_VOLUME="${ZENITH_CONFIG_VOLUME:-zenith-config}"
DATA_VOLUME="${ZENITH_DATA_VOLUME:-zenith-data}"
PYTHON_BIN="${ZENITH_PYTHON_BIN:-python3}"
PIP_PACKAGE="${ZENITH_PIP_PACKAGE:-project-zenith}"

usage() {
  cat <<'EOF'
Usage: ./teardown.sh [hybrid|host|container]

Most users should just run:
  ./teardown.sh

That removes the recommended hybrid setup.

Modes:
  hybrid    Remove host Zenith plus container artifacts
  host      Remove host Zenith only
  container Remove container artifacts only

Environment overrides:
  ZENITH_IMAGE_NAME=zenith
  ZENITH_CONTAINER_NAME=zenith-shell
  ZENITH_CONFIG_VOLUME=zenith-config
  ZENITH_DATA_VOLUME=zenith-data
  ZENITH_PYTHON_BIN=python3
  ZENITH_PIP_PACKAGE=project-zenith
EOF
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

cleanup_host() {
  if has_cmd "$PYTHON_BIN"; then
    if "$PYTHON_BIN" -c 'import zenith' >/dev/null 2>&1; then
      "$PYTHON_BIN" -m zenith.cli uninstall --yes || true
    fi
    "$PYTHON_BIN" -m pip uninstall -y "$PIP_PACKAGE" >/dev/null 2>&1 || true
  fi

  rm -f "$HOME/.local/bin/zen" "$HOME/.local/bin/zenith"
  rm -rf "$HOME/.config/zenith" "$HOME/.local/share/zenith"
}

cleanup_container() {
  if ! has_cmd podman; then
    printf 'Missing required command: podman
' >&2
    exit 1
  fi

  podman rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  podman volume rm -f "$CONFIG_VOLUME" "$DATA_VOLUME" >/dev/null 2>&1 || true
  podman image rm -f "$IMAGE_NAME" >/dev/null 2>&1 || true
}

case "$MODE" in
  hybrid)
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
    printf 'Unknown mode: %s

' "$MODE" >&2
    usage >&2
    exit 1
    ;;
esac
