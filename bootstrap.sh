#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="hybrid"
FRESH=0
PROFILE="${ZENITH_PROFILE:-safe}"
IMAGE_NAME="${ZENITH_IMAGE_NAME:-zenith}"
CONTAINER_NAME="${ZENITH_CONTAINER_NAME:-zenith-shell}"
CONFIG_VOLUME="${ZENITH_CONFIG_VOLUME:-zenith-config}"
DATA_VOLUME="${ZENITH_DATA_VOLUME:-zenith-data}"
WORKSPACE_MOUNT="${ZENITH_WORKSPACE_MOUNT:-$ROOT_DIR}"
HOSTNAME_NAME="${ZENITH_HOSTNAME:-zenith}"
TERMINAL="${ZENITH_TERMINAL:-kitty}"
CONTAINER_GPU="${ZENITH_CONTAINER_GPU:-auto}"
PODMAN_HOOKS_DIR="${ZENITH_PODMAN_HOOKS_DIR:-/usr/share/containers/oci/hooks.d}"
TERMINAL_REQUESTED=0
PODMAN_GPU_ARGS=()
GPU_STATUS_MSG=""

if [ -n "${ZENITH_TERMINAL:-}" ]; then
  TERMINAL_REQUESTED=1
fi

usage() {
  cat <<'HELP'
Usage: ./bootstrap.sh [hybrid|host|container|fresh] [--fresh] [--terminal NAME] [--gpu auto|nvidia|none]

Most users should just run:
  ./bootstrap.sh

That defaults to the recommended hybrid setup: lightweight host CLI plus a fully provisioned core container.

Modes:
  hybrid    Install a lightweight host CLI and prepare a persistent core container
  host      Install host Zenith in user space only on the host itself
  container Build and prepare a persistent core container only
  fresh     Remove the recommended hybrid setup first, then reinstall it

Options:
  --terminal NAME      Attempt a host user-space install for the chosen terminal and record it as the preferred surface terminal
  --gpu MODE           Container GPU mode: auto, nvidia, or none

Environment overrides:
  ZENITH_PROFILE=safe|personal
  ZENITH_IMAGE_NAME=zenith
  ZENITH_CONTAINER_NAME=zenith-shell
  ZENITH_CONFIG_VOLUME=zenith-config
  ZENITH_DATA_VOLUME=zenith-data
  ZENITH_WORKSPACE_MOUNT=/path/to/workspace
  ZENITH_TERMINAL=kitty
  ZENITH_CONTAINER_GPU=auto|nvidia|none
  ZENITH_PODMAN_HOOKS_DIR=/usr/share/containers/oci/hooks.d

Fresh reset examples:
  ./bootstrap.sh fresh
  ./bootstrap.sh --gpu nvidia
  ./bootstrap.sh host --fresh --terminal kitty
  ./bootstrap.sh container --fresh --gpu none
HELP
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s
' "$1" >&2
    exit 1
  fi
}

normalize_gpu_mode() {
  local raw
  raw="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$raw" in
    ''|auto)
      printf 'auto'
      ;;
    nvidia)
      printf 'nvidia'
      ;;
    none|off|cpu)
      printf 'none'
      ;;
    *)
      printf 'Unknown GPU mode: %s
' "$1" >&2
      exit 1
      ;;
  esac
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      hybrid|host|container)
        MODE="$1"
        ;;
      fresh)
        MODE="hybrid"
        FRESH=1
        ;;
      --fresh)
        FRESH=1
        ;;
      --terminal)
        if [ "$#" -lt 2 ]; then
          printf 'Missing value for --terminal

' >&2
          usage >&2
          exit 1
        fi
        TERMINAL="$2"
        TERMINAL_REQUESTED=1
        shift
        ;;
      --gpu)
        if [ "$#" -lt 2 ]; then
          printf 'Missing value for --gpu

' >&2
          usage >&2
          exit 1
        fi
        CONTAINER_GPU="$2"
        shift
        ;;
      -h|--help|help)
        usage
        exit 0
        ;;
      *)
        printf 'Unknown argument: %s

' "$1" >&2
        usage >&2
        exit 1
        ;;
    esac
    shift
  done
  CONTAINER_GPU="$(normalize_gpu_mode "$CONTAINER_GPU")"
}

gpu_plan_line() {
  case "$CONTAINER_GPU" in
    auto)
      printf -- '- try NVIDIA GPU passthrough automatically when the host runtime is available
'
      ;;
    nvidia)
      printf -- '- require NVIDIA GPU passthrough for the container
'
      ;;
    none)
      printf -- '- run the container without GPU passthrough
'
      ;;
  esac
}

print_plan() {
  printf '
Zenith deployment plan

'

  case "$MODE" in
    hybrid)
      cat <<INFO
Mode: hybrid
Fresh reset: $([ "$FRESH" -eq 1 ] && printf yes || printf no)
Preferred host surface terminal: $TERMINAL
Container GPU mode: $CONTAINER_GPU

Host:
- install the lightweight Zenith CLI only
- keep host changes local to your user account
- do not install heavy AI or core runtime packages on the host
- do not use sudo in this mode
INFO
      if [ "$TERMINAL_REQUESTED" -eq 1 ]; then
        printf -- '- attempt a user-space install of %s on the host
' "$TERMINAL"
      else
        printf -- '- do not attempt a host terminal install unless you pass --terminal
'
      fi
      cat <<INFO

Container:
- build a persistent Podman image and container
- install heavy core tools in the container
- install Ollama and pull the configured model in the container
- keep Zenith runtime state in Podman volumes
INFO
      gpu_plan_line
      cat <<INFO

Not included:
- host package-manager installs
- host GUI surface assets unless you explicitly request and successfully bootstrap a host terminal
- automatic host installation of the NVIDIA container toolkit

Visibility after setup:
- host probe: ./probe.sh
- container status: podman exec -it $CONTAINER_NAME zen status --json
- container doctor: podman exec -it $CONTAINER_NAME zen doctor
- container config: podman exec -it $CONTAINER_NAME zen config path
INFO
      ;;
    host)
      cat <<INFO
Mode: host
Fresh reset: $([ "$FRESH" -eq 1 ] && printf yes || printf no)
Preferred surface terminal: $TERMINAL

Host:
- install Zenith on the host in user space only
- keep host changes under your home directory
- do not use sudo or make host package-manager changes
- bootstrap only the tools Zenith can manage locally
- attempt a user-space install of the chosen terminal when Zenith knows how
- apply host-native surface assets for the chosen terminal when Zenith ships them

Container:
- not used in this mode

Visibility after setup:
- status: zen status --json
- doctor: zen doctor
- config: zen config path
- probe: ./probe.sh
INFO
      ;;
    container)
      cat <<INFO
Mode: container
Fresh reset: $([ "$FRESH" -eq 1 ] && printf yes || printf no)
Preferred host surface terminal: $TERMINAL
Container GPU mode: $CONTAINER_GPU

Host:
- no host Zenith install beyond this repo checkout
- no host package-manager changes
- no host terminal install attempt, even if --terminal is provided

Container:
- build a persistent Podman image and container
- install heavy core tools in the container
- install Ollama and pull the configured model in the container
- keep Zenith runtime state in Podman volumes
INFO
      gpu_plan_line
      cat <<INFO

Visibility after setup:
- container status: podman exec -it $CONTAINER_NAME zen status --json
- container doctor: podman exec -it $CONTAINER_NAME zen doctor
- container config: podman exec -it $CONTAINER_NAME zen config path
- host probe: ./probe.sh
INFO
      ;;
  esac

  printf '
'
}

install_host_minimal() {
  require_cmd python3
  cd "$ROOT_DIR"
  python3 -m pip install --no-cache-dir .
}

install_requested_terminal() {
  if [ "$TERMINAL_REQUESTED" -eq 0 ]; then
    return
  fi
  if python3 -m zenith.cli install surface --mode host --profile "$PROFILE" --terminal "$TERMINAL" --yes; then
    return
  fi
  if [ "$MODE" = "hybrid" ]; then
    printf '
[warn] Host terminal bootstrap for %s did not complete. Zenith will continue with the hybrid core setup.
' "$TERMINAL" >&2
    printf '[note] Run zen upgrade surface --check or zen install surface --mode host --terminal %s --yes later after the host prerequisites are available.

' "$TERMINAL" >&2
    return 0
  fi
  return 1
}

install_host_full() {
  install_host_minimal
  python3 -m zenith.cli install all --mode host --profile "$PROFILE" --terminal "$TERMINAL" --yes
}

stop_container_if_running() {
  podman stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
}

run_fresh_reset() {
  "$ROOT_DIR/teardown.sh" "$MODE"
}

configure_container_gpu() {
  PODMAN_GPU_ARGS=()
  GPU_STATUS_MSG='GPU passthrough disabled; the container will run AI on CPU unless you point Zenith at another Ollama endpoint.'

  case "$CONTAINER_GPU" in
    none)
      return 0
      ;;
    auto)
      if ! command -v nvidia-smi >/dev/null 2>&1; then
        GPU_STATUS_MSG='No NVIDIA runtime was detected on the host; Zenith will continue without container GPU passthrough.'
        return 0
      fi
      ;;
    nvidia)
      if ! command -v nvidia-smi >/dev/null 2>&1; then
        printf '[warn] Container GPU mode was set to nvidia, but nvidia-smi is not available on the host.
' >&2
        return 1
      fi
      ;;
  esac

  PODMAN_GPU_ARGS+=(--gpus all)
  if [ -d "$PODMAN_HOOKS_DIR" ]; then
    PODMAN_GPU_ARGS+=(--hooks-dir "$PODMAN_HOOKS_DIR")
    GPU_STATUS_MSG="NVIDIA GPU passthrough requested for the container via --gpus all and hooks from $PODMAN_HOOKS_DIR."
  else
    GPU_STATUS_MSG='NVIDIA GPU passthrough requested for the container via --gpus all. The Podman hooks directory was not found, so host NVIDIA container support may still be incomplete.'
  fi
  return 0
}

prepare_container() {
  local create_args=()

  require_cmd podman
  cd "$ROOT_DIR"

  configure_container_gpu
  printf '[note] %s
' "$GPU_STATUS_MSG"

  podman build -t "$IMAGE_NAME" .
  podman volume inspect "$CONFIG_VOLUME" >/dev/null 2>&1 || podman volume create "$CONFIG_VOLUME" >/dev/null
  podman volume inspect "$DATA_VOLUME" >/dev/null 2>&1 || podman volume create "$DATA_VOLUME" >/dev/null
  podman rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

  create_args=(create -it
    --name "$CONTAINER_NAME"
    --hostname "$HOSTNAME_NAME"
    --entrypoint bash
    --security-opt label=disable
  )
  if [ "${#PODMAN_GPU_ARGS[@]}" -gt 0 ]; then
    create_args+=("${PODMAN_GPU_ARGS[@]}")
  fi
  create_args+=(
    -v "$CONFIG_VOLUME:/root/.config/zenith"
    -v "$DATA_VOLUME:/root/.local/share/zenith"
    -v "$WORKSPACE_MOUNT:/workspace"
    -w /workspace
    "$IMAGE_NAME"
  )

  podman "${create_args[@]}" >/dev/null

  trap stop_container_if_running RETURN
  podman start "$CONTAINER_NAME" >/dev/null
  podman exec "$CONTAINER_NAME" bash -lc "cd /workspace && ZENITH_STRICT_BOOTSTRAP=1 zen install core --mode container --profile '$PROFILE' --yes"

  printf '
Container validation:
'
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

parse_args "$@"
print_plan

if [ "$FRESH" -eq 1 ]; then
  run_fresh_reset
fi

case "$MODE" in
  hybrid)
    install_host_minimal
    install_requested_terminal
    prepare_container
    ;;
  host)
    install_host_full
    ;;
  container)
    prepare_container
    ;;
esac
