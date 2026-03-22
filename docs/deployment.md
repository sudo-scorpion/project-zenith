# Deployment Guide

This page explains, in plain English, what Zenith does in each setup mode.

## Recommended mode

For most users, the recommended command is:

```bash
./bootstrap.sh host --terminal kitty
```

That means **host mode**. Everything goes directly onto your machine in user space — no containers needed for daily work.

Host mode:
- installs all shell and terminal tools on your machine via `sudo dnf` (or your distro's package manager)
- installs Kitty terminal in user space
- deploys starship prompt, zsh config, fzf, autosuggestions, syntax highlighting
- makes `ai` and `fix` shortcuts available in every shell session
- keeps everything under your home directory and user-owned paths

No container is needed in host mode. Zellij, Ollama, and all tools run directly on your machine. The container is only relevant in hybrid mode.

## Scenarios

### `./bootstrap.sh host --terminal kitty` (recommended)

Use this for your daily machine setup.

What happens:
- installs Zenith CLI on the host
- installs all core tools (`zsh`, `zellij`, `yazi`, `eza`, `bat`, `starship`, `zoxide`, `fzf`, `ripgrep`, `btop`, `fastfetch`) via the system package manager with `sudo`
- installs Kitty terminal in user space
- deploys zsh fragment, starship config, kitty config, zsh plugins
- sets up `ai` and `fix` shell shortcuts

### `./bootstrap.sh host --fresh --terminal kitty`

Clean reinstall of the host setup. Removes existing Zenith artifacts first, then reinstalls everything from scratch.

### `./bootstrap.sh` (hybrid mode)

Use this when you want Ollama running in an isolated Podman container with GPU passthrough and a lightweight host.

Host gets:
- the lightweight `zen` CLI and launcher only

Container gets:
- `ollama`, heavy runtime tools, AI models
- `zen workspace` sessions via Zellij

### `./bootstrap.sh --gpu nvidia`

Hybrid mode with required NVIDIA GPU passthrough for the Podman container.

What happens:
- everything from the hybrid setup happens
- Zenith launches the container with `--device nvidia.com/gpu=all`
- bootstrap fails early if `nvidia-smi` is not available on the host
- Ollama GPU libraries (`~/.local/lib/ollama`) are deployed so GPU backends load correctly

### `./bootstrap.sh --gpu none`

Force CPU-only container AI even on a GPU host.

### `./bootstrap.sh --terminal kitty` (hybrid + surface)

Hybrid mode plus a host Kitty install.

What happens:
- everything from the hybrid setup happens
- Zenith installs Kitty in user space and deploys terminal config

### `./bootstrap.sh fresh`

Clean reinstall of the hybrid setup.

### `./bootstrap.sh container`

Container side only, no host Zenith install.

### `./teardown.sh`

Removes the full hybrid setup.

### `./teardown.sh host`

Removes host Zenith only. Cleans up:
- Zenith config and state directories
- shell fragment source hooks from `.zshrc` and `.bashrc`
- system packages installed by Zenith (via `sudo dnf remove`)
- user-space binaries (`~/.local/bin/zen`, `~/.local/bin/kitty`, etc.)
- zsh plugins (`~/.local/share/zsh-plugins/`)
- caches (`~/.cache/starship`, `~/.cache/zoxide`, `~/.local/share/zoxide`)
- zsh completion dumps (`~/.zcompdump*`)

## What goes where

### Host (daily driver)

- all shell tools: `eza`, `bat`, `fzf`, `ripgrep`, `zoxide`, `btop`, `starship`, `zsh`
- terminal: Kitty (`~/.local/kitty.app`)
- shell config: `~/.config/zenith/zenith.zshrc`, zsh plugins
- prompt: `~/.config/starship.toml`
- `ai` and `fix` shortcuts in every shell session
- the `zen` CLI launcher

### Container (AI compute only)

- `ollama` and the AI model (`qwen2.5-coder:7b`)
- GPU passthrough via CDI
- `zen workspace` focused sessions (Zellij)
- Ollama GPU libraries at `~/.local/lib/ollama`

### Host-only by design

- Kitty terminal config and surface assets
- Ghostty shaders
- GUI/session integration

## GPU note

If AI feels slow:

- run `zen doctor` or `zen status --json` to confirm whether Ollama is using GPU or CPU
- in hybrid mode, Ollama runs in the container — use `./bootstrap.sh --gpu nvidia` to enable passthrough
- GPU libraries must be present at `~/.local/lib/ollama/` for Ollama to find its CUDA backend; these are deployed automatically by `zen install core` when bootstrapping Ollama from a release archive
- `num_gpu = 99` in config ensures all available GPU layers are used
