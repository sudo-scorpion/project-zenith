# Deployment Guide

This page explains, in plain English, what Zenith does in each setup mode.

## Recommended mode

For most users, the recommended command is:

```bash
./bootstrap.sh
```

That means **hybrid mode**.

Hybrid mode is designed to keep the host light and keep the heavy runtime in Podman.

Host:
- installs the lightweight Zenith CLI
- keeps changes inside your user account
- does not install heavy AI or terminal packages on the host
- does not use `sudo`

Container:
- builds a persistent Podman image and container
- installs heavy runtime tools such as `ollama`, `zellij`, `yazi`, and `starship`
- pulls the configured Ollama model in the container
- keeps Zenith runtime state in Podman volumes

Not included:
- host GUI `surface`
- host package-manager installs

## Scenarios

### `./bootstrap.sh`

Use this when you want the normal recommended setup.

What happens:
- host gets a lightweight Zenith CLI
- Podman container gets the heavy runtime and AI tools
- default container GPU mode is `auto`, so Zenith tries NVIDIA passthrough when the host runtime is already available
- no host `sudo` package provisioning

### `./bootstrap.sh --gpu nvidia`

Use this when you want the normal recommended setup and you want Zenith to require NVIDIA GPU passthrough for the Podman container.

What happens:
- everything from the normal hybrid setup happens
- Zenith launches the container with `--gpus all`
- Zenith also adds Podman hooks from the configured hooks directory when that directory exists
- bootstrap fails early if you explicitly requested `nvidia` but the host does not expose `nvidia-smi`
- Zenith still does not install the host NVIDIA container toolkit for you

### `./bootstrap.sh --gpu none`

Use this when you want to force CPU-only container AI even on a GPU host.

What happens:
- everything from the normal hybrid setup happens
- Zenith launches the Podman container without GPU passthrough

### `./bootstrap.sh --terminal kitty`

Use this when you want the normal recommended setup and also want Zenith to try to install that host terminal for you in user space.

What happens:
- everything from the normal hybrid setup happens
- Zenith attempts a host user-space install for the requested terminal
- for Kitty on Linux, Zenith uses the official user-space installer
- for Ghostty on Linux, Zenith uses the official source-build path and bootstraps the required Zig version into user space when it can
- Zenith records that terminal name for later host-side `surface` work
- no host package-manager changes happen just because you set the terminal name

### `./bootstrap.sh fresh`

Use this when you want a true clean reinstall of the recommended setup.

What happens:
- runs `./teardown.sh clean` for the hybrid setup
- reinstalls the same hybrid layout from scratch

### `./bootstrap.sh container`

Use this when you only want the container side.

What happens:
- no host Zenith install beyond this repo checkout
- Podman container gets the heavy runtime and AI tools

### `./bootstrap.sh host`

Use this only when you want Zenith to live directly on the host.

What happens:
- installs Zenith on the host itself
- stays in your user space only
- does not use `sudo`
- does not make host package-manager changes
- bootstraps only the host tools Zenith can manage locally
- attempts a user-space install of the chosen terminal when Zenith knows how
- records and applies host-native surface assets for the chosen terminal when Zenith ships them

### `./teardown.sh clean`

Use this when you want Zenith removed.

What happens:
- removes Zenith-owned host config, state, and shims
- removes Zenith Podman container, image, and volumes
- removes fallback binaries Zenith bootstrapped

## What goes where

### Host in hybrid mode

These are the kinds of things that belong on the host in the recommended setup:
- the `zen` launcher
- lightweight Python package install for Zenith itself
- user-owned host config and state helpers
- repo checkout

### Container in hybrid mode

These are the kinds of things that belong in the container in the recommended setup:
- `ollama`
- Ollama models
- `zellij`
- `yazi`
- `starship`
- other heavy shell and AI runtime tools
- workspace and AI execution runtime

### Host-only by design

These belong on the host and are not part of the normal container path:
- `surface`
- terminal config
- shaders
- GUI/session integration

## User-space host truth

Zenith now follows a simple rule on the host:

- no `sudo`
- no host package-manager changes
- no pretending a host binary was installed when Zenith only wrote config

That means host-side `surface` setup is about user-space config, terminal bootstraps, and assets. If your chosen terminal binary is missing and Zenith does not ship a local bootstrap for it, Zenith fails clearly and tells you that directly.

## GPU note

If AI feels slow, the first question is where Ollama is running.

- In hybrid mode, Ollama normally runs in the container.
- If that container does not have GPU passthrough, Ollama will run on CPU.
- `zen doctor` and `zen status --json` can now show whether Ollama is using GPU or CPU.

If you want GPU-backed AI, you need one of these:
- Podman container with real GPU passthrough via `./bootstrap.sh --gpu nvidia` or `ZENITH_CONTAINER_GPU=nvidia`
- or a host Ollama endpoint with Zenith pointed at it explicitly
