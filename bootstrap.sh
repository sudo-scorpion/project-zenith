#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-hybrid}"
PROFILE="${ZENITH_PROFILE:-safe}"
IMAGE_NAME="${ZENITH_IMAGE_NAME:-zenith}"
CONTAINER_NAME="${ZENITH_CONTAINER_NAME:-zenith-shell}"
CONFIG_VOLUME="${ZENITH_CONFIG_VOLUME:-zenith-config}"
DATA_VOLUME="${ZENITH_DATA_VOLUME:-zenith-data}"
WORKSPACE_MOUNT="${ZENITH_WORKSPACE_MOUNT:-$ROOT_DIR}"
HOSTNAME_NAME="${ZENITH_HOSTNAME:-zenith}"

usage() {
  cat <<'HELP'
Usage: ./bootstrap.sh [hybrid|host|container]

Most users should just run:
  ./bootstrap.sh

That defaults to the recommended hybrid setup.

Modes:
  hybrid    Install full host Zenith and prepare a persistent core container
  host      Install full host Zenith (core + surface)
  container Build and prepare a persistent core container only

Environment overrides:
  ZENITH_PROFILE=safe|personal
  ZENITH_IMAGE_NAME=zenith
  ZENITH_CONTAINER_NAME=zenith-shell
  ZENITH_CONFIG_VOLUME=zenith-config
  ZENITH_DATA_VOLUME=zenith-data
  ZENITH_WORKSPACE_MOUNT=/path/to/workspace
HELP
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

install_host() {
  require_cmd python3
  cd "$ROOT_DIR"
  python3 -m pip install --no-cache-dir .
  python3 -m zenith.cli install all --mode host --profile "$PROFILE" --yes
}

stop_container_if_running() {
  podman stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
}

prepare_container() {
  require_cmd podman
  cd "$ROOT_DIR"

  podman build -t "$IMAGE_NAME" .
  podman volume inspect "$CONFIG_VOLUME" >/dev/null 2>&1 || podman volume create "$CONFIG_VOLUME" >/dev/null
  podman volume inspect "$DATA_VOLUME" >/dev/null 2>&1 || podman volume create "$DATA_VOLUME" >/dev/null
  podman rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

  podman create -it \
    --name "$CONTAINER_NAME" \
    --hostname "$HOSTNAME_NAME" \
    --entrypoint bash \
    --security-opt label=disable \
    -v "$CONFIG_VOLUME:/root/.config/zenith" \
    -v "$DATA_VOLUME:/root/.local/share/zenith" \
    -v "$WORKSPACE_MOUNT:/workspace" \
    -w /workspace \
    "$IMAGE_NAME" >/dev/null

  trap stop_container_if_running RETURN
  podman start "$CONTAINER_NAME" >/dev/null
  podman exec "$CONTAINER_NAME" bash -lc "cd /workspace && ZENITH_STRICT_BOOTSTRAP=1 zen install core --mode container --profile '$PROFILE' --yes"

  printf '\nContainer validation:\n'
  podman exec "$CONTAINER_NAME" zen doctor

  podman stop "$CONTAINER_NAME" >/dev/null
  trap - RETURN

  cat <<INFO
Container prepared.

Daily use:
  podman start -ai $CONTAINER_NAME

Extra shell into the running container:
  podman exec -it $CONTAINER_NAME bash
INFO
}

case "$MODE" in
  hybrid)
    install_host
    prepare_container
    ;;
  host)
    install_host
    ;;
  container)
    prepare_container
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
